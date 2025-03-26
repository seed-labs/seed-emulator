from __future__ import annotations
import requests
import logging
import os
import re
from urllib.parse import urlparse
from enum import Enum
from typing import Dict, Tuple, Union, Any, Set

from sys import version
from seedemu.core import (Emulator, Interface, Layer, Network, Registry,
                          Router, ScionAutonomousSystem, ScionRouterMixin,
                          ScopedRegistry, Graphable, Node,
                            Option, AutoRegister, OptionMode)
from seedemu.core.ScionAutonomousSystem import IA
from seedemu.layers import ScionBase, ScionIsd
import shutil
import tempfile
from seedemu.utilities.BuildtimeDocker import BuildtimeDockerFile, BuildtimeDockerImage, sh
from enum import Enum
from dataclasses import dataclass

class LinkType(Enum):
    """!
    @brief Type of a SCION link between two ASes.
    """

    ## Core link between core ASes.
    Core = "Core"

    ## Customer-Provider transit link.
    Transit = "Transit"

    ## Non-core AS peering link.
    Peer = "Peer"

    def __str__(self):
        return f"{self.name}"

    def to_topo_format(self) -> str:
        """Return type name as expected in .topo files."""
        if self.value == "Core":
            return "CORE"
        elif self.value == "Transit":
            return "CHILD"
        elif self.value == "Peer":
            return "PEER"
        assert False, "invalid scion link type"

    def to_json(self, core_as: bool, is_parent: bool) -> str:
        """
        a core AS has to have 'CHILD' as its 'link_to' attribute value,
        for all interfaces!!
        The child AS on the other end of the link will have 'PARENT'
        """
        if self.value == "Core":
            return "CORE"
        elif self.value == "Peer":
            return "PEER"
        elif self.value == "Transit":
            if is_parent:
                return "CHILD"
            else:
                assert not core_as, 'Logic error:  Core ASes must only provide transit to customers, not receive it!'
                return "PARENT"

class ScionConfigMode(Enum):
    """how shall the /etc/scion config dir contents be handled:"""

    # statically include config in docker image (ship together)
    # this is fine, if no reconfiguration is required or the images
    # must be self contained i.e. for docker swarm deployment
    BAKED_IN = 0
    # mount shared folder from host into /etc/scion path of node
    # this saves considerable image build time and eases reconfiguration
    SHARED_FOLDER = 1
    # create named volumes for each container
    NAMED_VOLUME = 2
    # TODO all hosts of an AS could in theory share the same volume/bind-mount..
    # PER_AS_SHARING # this would only be possible for keys/crypto but not config files

# NOTE this option is used by ScionRouting and ScionIsd layers
# and can be specified in ScionRouting constructor
class SCION_ETC_CONFIG_VOL(Option, AutoRegister):
        """ this option controls the policy
        where to put all the SCION related files on the host.
        """
        value_type = ScionConfigMode
        @classmethod
        def supportedModes(cls) -> OptionMode:
            return OptionMode.BUILD_TIME
        @classmethod
        def default(cls):
            return ScionConfigMode.BAKED_IN


def handleScionConfFile( node, filename: str, filecontent: str, subdir: str = None):
    """ wrapper around 'Node::setFile' for /etc/scion config files
    @param subdir sub path relative to /etc/scion
    """
    if (opt := node.getOption('scion_etc_config_vol')) != None:
                suffix = f'/{subdir}' if subdir != None else ''
                match opt.value:
                    case ScionConfigMode.SHARED_FOLDER:
                        current_dir = os.getcwd()
                        path = os.path.join(current_dir,
                                             f'.shared/{node.getAsn()}/{node.getName()}/etcscion{suffix}')
                        os.makedirs(path, exist_ok=True)
                        with open(os.path.join(path, filename), "w") as file:
                            file.write(filecontent)
                    case _:
                    #case ScionConfigMode.BAKED_IN:
                        node.setFile(f"/etc/scion{suffix}/{filename}", filecontent)
                    #case ScionConfigMode.NAMED_VOLUME: will be populated on fst mount
    else:
        assert False, 'implementation error - lacking global default for option'


@dataclass
class CheckoutSpecification():#SetupSpecification
    """
    Identifies a specific SCION release version or RepoCheckout
    """
    mode: str # 'release' or 'build'
    release_location: str
    version: str
    git_repo_url: str
    checkout: str

    # TODO do some more logic >> version and release_location must not be specified independently
    def __init__(self,
                  mode: str = None,
                  release_location: str = None,
                  version: str = None,
                  git_repo_url: str = None,
                  checkout: str = None
                  ):
        if not mode:        self.mode = "release"
        else: self.mode = mode
        if not release_location:
            self.release_location = "https://github.com/scionproto/scion/releases/download/v0.12.0/scion_0.12.0_amd64_linux.tar.gz"
        else: self.release_location = release_location
        if not version:
            self.version = "v0.12.0"
        else: self.version = version
        # "mode": "build",
        if not git_repo_url:
            self.git_repo_url = "https://github.com/scionproto/scion.git"
        else: self.git_repo_url = git_repo_url
        if not checkout:
            self.checkout = "v0.12.0" # could be tag, branch or commit (ex "efbbd5835f33ab52389976d4b69d68fa7c087230")
        else: self.checkout = checkout


# InstallationPlan, InstallPolicy
class SetupSpecification(Enum):
    """! @brief describes how exactly the SCION distributables
      shall be installed i.e. either from ubuntu-packages or local checkout and build
    """

    PACKAGES = "UbuntuPackage"
    LOCAL_BUILD = "Compile from sources" #CheckoutSpecification

    def __call__(self, *args, **kwargs) -> SetupSpecification:#Union[str, CheckoutSpecification]:
        """
        Overloads `()` to return the appropriate object based on the enum variant.
        """
        if self == SetupSpecification.PACKAGES:
            return self # "Ubuntu ETHZ .deb package installation"
        elif self == SetupSpecification.LOCAL_BUILD:
            if type(args[0]) == CheckoutSpecification:
                self.checkout_spec = args[0]
            else:
                self.checkout_spec = CheckoutSpecification(*args, **kwargs)
            return self
        else:
            raise TypeError(f"Invalid SetupSpecification variant: {self}")

    def describe(method):
        match method:
            case SetupSpecification.PACKAGES:
                return "Installed via Ubuntu ETHZ .deb package"
            case SetupSpecification.LOCAL_BUILD:
                return "Local build from source"

# TODO: add the notion of provided capabilities to SetupSpecification
# some features(options) of the ScionRouting layer
#  might require a special checkout on the node (>> conditional options )
# Currently we are unable to detect inadequate checkouts/setups
# for a given set of options on a node at build time(the emulation will just not work).
class ScionBuilder():
    """!
    @brief A strategy object who knows how to install
    the SCION distributables on a Node as instructed by a specification.

    This neatly separates installation and configuration of the SCION stack.
    The former is the ScionBuilder's job, whereas the latter is up to the ScionRouting layer,
    which delegates installatation to the builder.
    The builder is stateless and all configuration state resides on nodes in form of options.
    Checks the mode property and either downloads the binaries and builds it from source
    Also supports local absolute directory file path to use instead in release mode
    """


    def __init__(self):
        pass

    def installSCION(self, node: Node):
        """!@brief install required SCION distributables
            (network stack) on the given node
        Installs the right SCION stack distributables on the given node based on its role.
        But doesn't configure them ( /etc/scion config dir is untouched by it)
        The install is performed as instructed by the nodes SetupSpec option.
        """
        spec = node.getOption('setup_spec')
        assert spec != None, 'implementation error - all nodes are supposed to have a SetupSpecification set by ScionRoutingLayer'

        match s:=spec.value:
            case SetupSpecification.LOCAL_BUILD:
                self.__installFromBuild(node, s.checkout_spec)
                self._addSCIONLabPackages(node)
                node.addBuildCommand("apt-get update && apt download scion-apps-bwtester"
                                     " && dpkg --ignore-depends=scion-daemon,scion-dispatcher -i scion-apps-bwtester_3.4.2_amd64.deb")


            case SetupSpecification.PACKAGES:
                self._installFromDebPackage(node)

    def nameOfCmd(self, cmd, node: Node) -> str:
        spec = node.getOption('setup_spec')
        assert spec != None, 'implementation error - all nodes are supposed to have a SetupSpecification set by ScionRoutingLayer'
        assert cmd in ['router', 'control', 'dispatcher', 'daemon'], f'unknown SCION distributable {cmd}'
        match spec.value:
            case SetupSpecification.PACKAGES:
                return {'router': 'scion-border-router',
                        'control': 'scion-control-service',
                        'dispatcher': 'scion-dispatcher',
                        'daemon': 'sciond' }[cmd]
            case SetupSpecification.LOCAL_BUILD:
                return cmd

    def _addSCIONLabPackages(self, node: Node):
        node.addBuildCommand(
            'echo "deb [trusted=yes] https://packages.netsec.inf.ethz.ch/debian all main"'
            " > /etc/apt/sources.list.d/scionlab.list"
        )

    def _installFromDebPackage(self, node: Node): # TODO: don't install  all distributables on all nodes i.e. no BR for hosts etc.
        """Install SCION packages on the node."""
        self._addSCIONLabPackages(node)
        node.addBuildCommand(
            "apt-get update && apt-get install -y"
            " scion-border-router scion-control-service scion-daemon scion-dispatcher scion-tools"
            " scion-apps-bwtester"
        )
        node.addSoftware("apt-transport-https")
        node.addSoftware("ca-certificates") # by whom are these required exactly ?! only the deb-packages ?!
        self.installHelpers(node)

    def __installFromBuild(self, node: Node, s: CheckoutSpecification):
        """
        validates the specification and if its sensible
        does checkout, build and mount into node as volume
        """
        self.__validateBuildConfiguration(s)
        build_dir = self.__generateBuild(s)
        path_to_binaries = "/bin/scion/" # path in container TODO move to CheckoutSpec ?!
        node.addSharedFolder(path_to_binaries, build_dir)
        node.addDockerCommand(f'ENV PATH={path_to_binaries}:$PATH ')
        self.installHelpers(node)

    def installHelpers(self, node: Node):
        #node.addSoftware("apt-transport-https")
        #node.addSoftware("ca-certificates") # by whom are these required exactly ?! only the deb-packages ?!

        if node.getOption("rotate_logs").value == "true":
            node.addSoftware("apache2-utils")  # for rotatelogs
        # TODO actually i had to check if there's any option on this node
        # which has OptionMode.RUN_TIME set
        if node.getOption("use_envsubst").value == "true":  # for envsubst
            node.addSoftware("gettext")



    def __validateBuildConfiguration(self, config: CheckoutSpecification):
        """
        validate build configuration dict by checking all the required keys and url validity
        """
        if not config.mode:
            raise KeyError("No SCION build configuration provided.")
        if config.mode not in ["release", "build"]:
            raise ValueError("Only two SCION build modes accepted. 'release'|'build'")
        if config.mode == "release":
            if not config.release_location:
                raise KeyError("releaseLocation must be set for the mode 'release'")
            self.__validateReleaseLocation(config.release_location)
            if not config.version:
                raise KeyError("version must be set for the mode 'release'")
        if config.mode == "build":
            if not config.git_repo_url:
                raise KeyError("gitRepoUrl must be set for the mode 'build'")
            if not config.checkout:
                raise KeyError("'checkout' must be set for the mode 'build'")
            self.__validateGitURL(config.git_repo_url)

    def __validateReleaseLocation(self, path: str):
        """
        check if the local path exists or the url is valid and reachable
        """
        if (path) and self.__is_local_path(path):
            if not os.path.exists(path):
                raise ValueError("SCION local binary location is not valid.")
            if not os.path.isabs(path):
                raise ValueError("Absolute path required for the folder containing binaries")
        elif self.__is_http_url(path):
            try:
                response = requests.head(path, allow_redirects=True, timeout=5)
                if not response.status_code < 400:
                    raise Exception(f"SCION release url is valid but not reachable")
            except requests.RequestException as e:
                logging.error(e)
                raise Exception(f"SCION release url is valid but not reachable")
        else:
            raise ValueError("Release location is Neither a valid HTTP URL nor a local path")

    def __is_http_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return result.scheme in ("http", "https") and bool(result.netloc)
        except ValueError:
            return False

    def __is_local_path(self, path: str) -> bool:
        # A local path shouldn't be a URL but should exist in the filesystem
        return not self.__is_http_url(path)

    def __validateGitURL(self, url: str) :
        # Ensure the URL ends with .git for Git repositories
        if not url.endswith(".git"):
            raise ValueError("URL does not look like a Git repository (missing .git)")
        # Check the Git info/refs endpoint
        git_service_url = f"{url}/info/refs?service=git-upload-pack"
        try:
            response = requests.get(git_service_url, timeout=10)
            if not (response.status_code == 200 and "git-upload-pack" in response.text):
                raise ValueError("SCION build repository not found (404)")
        except requests.RequestException as e:
                logging.error(e)
                raise ValueError(f"Invalid SCION build repository")

    def __classifyGitCheckout(self, checkout: str) -> str:
        # Check if it's a commit (40 characters, hexadecimal)
        if re.match(r'^[0-9a-fA-F]{40}$', checkout):
            return "commit"
        # Check if it's a tag (can be any string, usually without slashes and more descriptive)
        if re.match(r'^[\w.-]+$', checkout):
            return "tag"
        # Check if it's a branch (can include slashes, dashes, or numbers)
        if re.match(r'^[\w/.-]+$', checkout):
            return "branch"

        return "unknown"

    def __generateGitCloneString(self, repo_url: str, checkout: str) -> str:
        """
        Generates a Git clone string for the specified reference (branch, tag, or commit).
        """
        checkout_type = self.__classifyGitCheckout(checkout)
        if checkout_type == "branch":
            return f"git clone -b {checkout} {repo_url} scion"
        elif checkout_type == "tag":
            return f"git clone --branch {checkout} {repo_url} scion"
        elif checkout_type == "commit":
            # Clone first, then checkout the commit
            return f"git clone {repo_url} scion && cd scion && git checkout {checkout}"
        else:
            raise ValueError("Invalid reference type. Must be 'branch', 'tag', or 'commit'.")

    def __generateBuild(self, spec: CheckoutSpecification) -> str :
        """
        method to build all SCION binaries and output to .scion_build_output based on the configuration mode
        """
        if spec.mode == "release":
            if not self.__is_local_path(spec.release_location):
                if not os.path.isdir(f".scion_build_output/scion_binaries_{spec.version}"):
                    SCION_RELEASE_TEMPLATE = f"""FROM alpine
                    RUN apk add --no-cache wget tar
                    WORKDIR /app
                    RUN wget -qO- {spec.release_location} | tar xvz -C /app
                    """
                    dockerfile = BuildtimeDockerFile(SCION_RELEASE_TEMPLATE)
                    container = BuildtimeDockerImage(f"scion-release-fetch-container_{spec.version}").build(dockerfile).container()
                    current_dir = os.getcwd()
                    output_dir = os.path.join(current_dir, f".scion_build_output/scion_binaries_{spec.version}")
                    container.entrypoint("sh").mountVolume(output_dir, "/build").run(
                       "-c \"cp -r /app/* /build\""
                    )
                    return output_dir

                else:
                    output_dir = os.path.join(os.getcwd(), f".scion_build_output/scion_binaries_{spec.version}")
                    return output_dir
            else:
                return spec.release_location
        else:
            if not os.path.isdir(f".scion_build_output/scion_binaries_{spec.checkout}"):
                SCION_BUILD_TEMPLATE = f"""FROM golang:1.22-alpine
                RUN apk add --no-cache git
                RUN {self.__generateGitCloneString(spec.git_repo_url, spec.checkout)}
                RUN cd scion && go mod tidy && CGO_ENABLED=0 go build -o bin ./router/... ./control/... ./dispatcher/... ./daemon/... ./scion/... ./scion-pki/... ./gateway/...
                """
                dockerfile = BuildtimeDockerFile(SCION_BUILD_TEMPLATE)
                container = BuildtimeDockerImage(f"scion-build-container-{spec.checkout}").build(dockerfile).container()
                current_dir = os.getcwd()
                output_dir = os.path.join(current_dir, f".scion_build_output/scion_binaries_{spec.checkout}")
                container.entrypoint("sh").mountVolume(output_dir, "/build").run(
                   "-c \"cp -r scion/bin/* /build\""
                )
                return output_dir

            else:
                output_dir = os.path.join(os.getcwd(), f".scion_build_output/scion_binaries_{spec.checkout}")
                return output_dir


class Scion(Layer, Graphable):
    """!
    @brief This layer manages SCION inter-AS links.

    This layer requires specifying link end points as ISD-ASN pairs as ASNs
    alone do not uniquely identify a SCION AS (see ScionISD layer).
    """

    __links: Dict[Tuple[IA, IA, str, str, LinkType], int]
    __ix_links: Dict[Tuple[int, IA, IA, str, str, LinkType], Dict[str,Any] ]
    __if_ids_by_as = {} # Dict[IA, Set[int]]

    def __init__(self):
        """!
        @brief SCION layer constructor.
        """
        super().__init__()
        self.__links = {}
        self.__ix_links = {}
        self.addDependency('ScionIsd', False, False)

    def getName(self) -> str:
        return "Scion"

    @staticmethod
    def _setIfId(ia: IA, ifid: int):
        """!@brief allocate the given IFID for the given AS.
            Returns wheter or not this assignment was unique
            or the ID already occupied by another Interface.
        """
        ifs = Scion.getIfIds(ia)
        v = ifid in ifs
        ifs.add(ifid)
        Scion.__if_ids_by_as[ia] = ifs
        return v

    @staticmethod
    def getIfIds(ia: IA) -> Set[int]:
        ifs = set()
        keys = Scion.__if_ids_by_as.keys()
        if ia in keys:
            ifs = Scion.__if_ids_by_as[ia]
        return ifs

    @staticmethod
    def peekNextIfId(ia: IA) -> int:
        """! @brief get the next free IFID, but don't allocate it yet.
        @note subsequent calls return the same, if not interleaved with getNextIfId() or _setIfId()
        """
        ifs = Scion.getIfIds(ia)
        if not ifs:
            return 0

        last = Scion._fst_free_id(ifs)
        return last+1

    @staticmethod
    def _fst_free_id(ifs: Set[int]) -> int:
        """ find the first(lowest) available free IFID number"""
        last = -1
        for i in ifs:
            if i-last > 1:
                return last+1
            else:
                last=i
        return last

    @staticmethod
    def getNextIfId(ia: IA) -> int:
        """ allocate the next free IFID
            if call returned X, a subsequent call will return X+1 (or higher)
        """
        ifs = Scion.getIfIds(ia)
        if not ifs:
            ifs.add(1)
            ifs.add(0)
            Scion.__if_ids_by_as[ia] = ifs

            return 1

        last = Scion._fst_free_id(ifs)

        ifs.add(last+1)
        Scion.__if_ids_by_as[ia] = ifs
        return last+1

    def addXcLink(self, a: Union[IA, Tuple[int, int]], b: Union[IA, Tuple[int, int]],
                  linkType: LinkType, count: int=1, a_router: str="", b_router: str="",) -> 'Scion':
        """!
        @brief Create a direct cross-connect link between to ASes.

        @param a First AS (ISD and ASN).
        @param b Second AS (ISD and ASN).
        @param linkType Link type from a to b.
        @param count Number of parallel links.
        @param a_router router of AS a default is ""
        @param b_router router of AS b default is ""

        @throws AssertionError if link already exists or is link to self.

        @returns self
        """
        a, b = IA(*a), IA(*b)
        assert a.asn != b.asn, "Cannot link as{} to itself.".format(a)
        assert (a, b, a_router, b_router, linkType) not in self.__links, (
            "Link between as{} and as{} of type {} exists already.".format(a, b, linkType))

        self.__links[(a, b, a_router, b_router, linkType)] = count

        return self

# additional arguments in 'kwargs':
# i.e. a_IF_ID and b_IF_ID if known (i.e. by a DataProvider)
    def addIxLink(self, ix: int, a: Union[IA, Tuple[int, int]], b: Union[IA, Tuple[int, int]],
                  linkType: LinkType, count: int=1, a_router: str="", b_router: str="", **kwargs) -> 'Scion':
        """!
        @brief Create a private link between two ASes at an IX.

        @param ix IXP id.
        @param a First AS (ISD and ASN).
        @param b Second AS (ISD and ASN).
        @param linkType Link type from a to b. In case of Transit: A is parent
        @param count Number of parallel links.
        @param a_router router of AS a default is ""
        @param b_router router of AS b default is ""

        @throws AssertionError if link already exists or is link to self.

        @returns self
        """
        a, b = IA(*a), IA(*b)
        assert a.asn != b.asn, "Cannot link as{} to itself.".format(a)
        assert (a, b, a_router, b_router, linkType) not in self.__links, (
            "Link between as{} and as{} of type {} at ix{} exists already.".format(a, b, linkType, ix))

        key = (ix, a, b, a_router, b_router, linkType)

        ids = []
        if 'if_ids' in kwargs:
            ids = kwargs['if_ids']
            assert not Scion._setIfId(a, ids[0]), f'Interface ID {ids[0]} not unique for IA {a}'
            assert not Scion._setIfId(b, ids[1]), f'Interface ID {ids[1]} not unique for IA {b}'
        else: # auto assign next free IFIDs
            ids = (Scion.getNextIfId(a), Scion.getNextIfId(b))

        if key in self.__ix_links.keys():
            self.__ix_links[key]['count'] += count
        else:
            self.__ix_links[key] = {'count': count , 'if_ids': set()}

        self.__ix_links[key]['if_ids'].add(ids)

        return self

    def configure(self, emulator: Emulator) -> None:
        reg = emulator.getRegistry()
        base_layer: ScionBase = reg.get('seedemu', 'layer', 'Base')
        assert issubclass(base_layer.__class__, ScionBase)

        self._configure_links(reg, base_layer)

    def render(self, emulator: Emulator) -> None:
        pass

    def _doCreateGraphs(self, emulator: Emulator) -> None:
        # core AS: double circle
        # non-core AS: circle
        # core link: bold line
        # transit link: normal line
        # peering link: dashed line

        self._log('Creating SCION graphs...')
        graph = self._addGraph('Scion Connections', False)

        reg = emulator.getRegistry()
        scionIsd_layer: ScionIsd = reg.get('seedemu', 'layer', 'ScionIsd')

        for (a, b, a_router, b_router, rel), count in self.__links.items():
            a_shape = 'doublecircle' if scionIsd_layer.isCoreAs(a.isd, a.asn) else 'circle'
            b_shape = 'doublecircle' if scionIsd_layer.isCoreAs(b.isd, b.asn) else 'circle'

            if not graph.hasVertex('AS{}'.format(a.asn), 'ISD{}'.format(a.isd)):
                graph.addVertex('AS{}'.format(a.asn), 'ISD{}'.format(a.isd), a_shape)
            if not graph.hasVertex('AS{}'.format(b.asn), 'ISD{}'.format(b.isd)):
                graph.addVertex('AS{}'.format(b.asn), 'ISD{}'.format(b.isd), b_shape)

            if rel == LinkType.Core:
                for _ in range(count):
                    graph.addEdge('AS{}'.format(a.asn), 'AS{}'.format(b.asn),
                                'ISD{}'.format(a.isd), 'ISD{}'.format(b.isd),
                                style= 'bold')
            if rel == LinkType.Transit:
                for _ in range(count):
                    graph.addEdge('AS{}'.format(a.asn), 'AS{}'.format(b.asn),
                                'ISD{}'.format(a.isd), 'ISD{}'.format(b.isd),
                                alabel='P', blabel='C')
            if rel == LinkType.Peer:
                for _ in range(count):
                    graph.addEdge('AS{}'.format(a.asn), 'AS{}'.format(b.asn),
                                'ISD{}'.format(a.isd), 'ISD{}'.format(b.isd),
                                style= 'dashed')

        for (ix, a, b, a_router, b_router, rel), d in self.__ix_links.items():
            count = d['count']
            ifids = d['if_ids']
            assert count == len(ifids)
            a_shape = 'doublecircle' if scionIsd_layer.isCoreAs(a.isd, a.asn) else 'circle'
            b_shape = 'doublecircle' if scionIsd_layer.isCoreAs(b.isd, b.asn) else 'circle'

            if not graph.hasVertex('AS{}'.format(a.asn), 'ISD{}'.format(a.isd)):
                graph.addVertex('AS{}'.format(a.asn), 'ISD{}'.format(a.isd), a_shape)
            if not graph.hasVertex('AS{}'.format(b.asn), 'ISD{}'.format(b.isd)):
                graph.addVertex('AS{}'.format(b.asn), 'ISD{}'.format(b.isd), b_shape)

            if rel == LinkType.Core:
                for ids in ifids:
                    graph.addEdge('AS{}'.format(a.asn), 'AS{}'.format(b.asn),
                                'ISD{}'.format(a.isd), 'ISD{}'.format(b.isd),
                                label='IX{}'.format(ix), style= 'bold',
                                alabel=f'#{ids[0]}',blabel=f'#{ids[1]}')
            elif rel == LinkType.Transit:
                for ids in ifids:
                    graph.addEdge('AS{}'.format(a.asn), 'AS{}'.format(b.asn),
                                'ISD{}'.format(a.isd), 'ISD{}'.format(b.isd),
                                label='IX{}'.format(ix),
                                alabel=f'P #{ids[0]}', blabel=f'C #{ids[1]}')
            elif rel == LinkType.Peer:
                for ids in ifids:
                    graph.addEdge('AS{}'.format(a.asn), 'AS{}'.format(b.asn),
                                'ISD{}'.format(a.isd), 'ISD{}'.format(b.isd),
                                'IX{}'.format(ix), style= 'dashed',
                                alabel=f'#{ids[0]}',blabel=f'#{ids[1]}')
            else:
                assert False, f'Invalid LinkType: {rel}'

    def print(self, indent: int = 0) -> str:
        out = ' ' * indent
        out += 'ScionLayer:\n'

        indent += 4
        for (ix, a, b, a_router, b_router, rel), d in self.__ix_links.items():
            count = d['count']
            out += ' ' * indent
            if a_router == "":
                out += f'IX{ix}: AS{a} -({rel})-> '
            else:
                out += f'IX{ix}: AS{a}_{a_router} -({rel})-> '
            if b_router == "":
                out += f'AS{b}'
            else:
                out += f'AS{b}_{b_router}'
            if count > 1:
                out += f' ({count} times)'
            out += '\n'

        for (a, b, a_router, b_router, rel), count in self.__links.items():
            out += ' ' * indent
            if a_router == "":
                out += f'XC: AS{a} -({rel})-> '
            else:
                out += f'XC: AS{a}_{a_router} -({rel})-> '
            if b_router == "":
                out += f'AS{b}'
            else:
                out += f'AS{b}_{b_router}'
            if count > 1:
                out += f' ({count} times)'
            out += '\n'

        return out

    def _configure_links(self, reg: Registry, base_layer: ScionBase) -> None:
        """Configure SCION links with IFIDs, IPs, ports, etc."""
        # cross-connect links
        for (a, b, a_router, b_router, rel), count in self.__links.items():
            a_reg = ScopedRegistry(str(a.asn), reg)
            b_reg = ScopedRegistry(str(b.asn), reg)
            a_as = base_layer.getAutonomousSystem(a.asn)
            b_as = base_layer.getAutonomousSystem(b.asn)

            if a_router == "" or b_router == "": # if routers are not explicitly specified try to get them
                try:
                    a_router, b_router = self.__get_xc_routers(a.asn, a_reg, b.asn, b_reg)
                except AssertionError:
                    assert False, f"cannot find XC to configure link as{a} --> as{b}"
            else: # if routers are explicitly specified, try to get them
                try:
                    a_router = a_reg.get('rnode', a_router)
                except AssertionError:
                    assert False, f"cannot find router {a_router} in as{a}"
                try:
                    b_router = b_reg.get('rnode', b_router)
                except AssertionError:
                    assert False, f"cannot find router {b_router} in as{b}"

            a_ifaddr, a_net, _ = a_router.getCrossConnect(b.asn, b_router.getName())
            b_ifaddr, b_net, _ = b_router.getCrossConnect(a.asn, a_router.getName())
            assert a_net == b_net
            net = reg.get('xc', 'net', a_net)
            a_addr = str(a_ifaddr.ip)
            b_addr = str(b_ifaddr.ip)

            for _ in range(count):
                self._log(f"add scion XC link: {a_addr} as{a} -({rel})-> {b_addr} as{b}")
                self.__create_link(a_router, b_router, a, b, a_as, b_as,
                                a_addr, b_addr, net, rel)

        # IX links
        for (ix, a, b, a_router, b_router, rel), d in self.__ix_links.items():
            count = d['count']
            ix_reg = ScopedRegistry('ix', reg)
            a_reg = ScopedRegistry(str(a.asn), reg)
            b_reg = ScopedRegistry(str(b.asn), reg)
            a_as = base_layer.getAutonomousSystem(a.asn)
            b_as = base_layer.getAutonomousSystem(b.asn)

            ix_net = ix_reg.get('net', f'ix{ix}')
            if a_router == "" or b_router == "": # if routers are not explicitly specified get all routers in AS
                a_routers = a_reg.getByType('rnode')
                b_routers = b_reg.getByType('rnode')
            else: # else get the specified routers
                a_routers = [a_reg.get('rnode', a_router)]
                b_routers = [b_reg.get('rnode', b_router)]

            # get the routers connected to the IX
            try:
                a_ixrouter, a_ixif = self.__get_ix_port(a_routers, ix_net)
            except AssertionError:
                assert False, f"cannot resolve scion peering: as{a} not in ix{ix}"
            try:
                b_ixrouter, b_ixif = self.__get_ix_port(b_routers, ix_net)
            except AssertionError:
                assert False, f"cannot resolve scion peering: as{a} not in ix{ix}"
            if 'if_ids' in d:
                self._log(f"add scion IX link: {a_ixif.getAddress()} AS{a} -({rel})->"
                        f"{b_ixif.getAddress()} AS{b}")
                for ids in d['if_ids']:
                    self.__create_link(a_ixrouter, b_ixrouter, a, b, a_as, b_as,
                                str(a_ixif.getAddress()), str(b_ixif.getAddress()),
                                ix_net, rel, if_ids = ids)
            else:
                for _ in range(count):
                    self._log(f"add scion IX link: {a_ixif.getAddress()} AS{a} -({rel})->"
                        f"{b_ixif.getAddress()} AS{b}")

                    self.__create_link(a_ixrouter, b_ixrouter, a, b, a_as, b_as,
                                str(a_ixif.getAddress()), str(b_ixif.getAddress()),
                                ix_net, rel)

    @staticmethod
    def __get_xc_routers(a: int, a_reg: ScopedRegistry, b: int, b_reg: ScopedRegistry) -> Tuple[Router, Router]:
        """Find routers responsible for a cross-connect link between a and b."""
        for router in a_reg.getByType('brdnode'):
            for peer, asn in router.getCrossConnects().keys():
                if asn == b and b_reg.has('brdnode', peer):
                    return (router, b_reg.get('brdnode', peer))
        assert False

    @staticmethod
    def __get_ix_port(routers: ScopedRegistry, ix_net: Network) -> Tuple[Router, Interface]:
        """Find a router in 'routers' that is connected to 'ix_net' and the
        interface making the connection.
        """
        for router in routers:
            for iface in router.getInterfaces():
                if iface.getNet() == ix_net:
                    return (router, iface)
        else:
            assert False

    def __create_link(self,
                     a_router: ScionRouterMixin, b_router: ScionRouterMixin,
                     a_ia: IA, b_ia: IA,
                     a_as: ScionAutonomousSystem, b_as: ScionAutonomousSystem,
                     a_addr: str, b_addr: str,
                     net: Network,
                     rel: LinkType,
                     if_ids=None ):
        """Create a link between SCION BRs a and b.
        In case of LinkType Transit: A is parent of B
        """

        a_ifid = -1
        b_ifid = -1

        if if_ids:
            a_ifid = if_ids[0]
            b_ifid = if_ids[1]
        else:
            a_ifid = Scion.getNextIfId(a_ia)
            b_ifid = Scion.getNextIfId(b_ia)

        a_port = a_router.getNextPort()
        b_port = b_router.getNextPort()

        a_core = 'core' in a_as.getAsAttributes(a_ia.isd)
        b_core = 'core' in b_as.getAsAttributes(b_ia.isd)

        if a_core and b_core:
            assert rel == LinkType.Core, f'Between Core ASes there can only be Core Links! {a_ia} -- {b_ia}'

        a_iface = {
            "underlay": {
                "local": f"{a_addr}:{a_port}",
                "remote": f"{b_addr}:{b_port}",
            },
            "isd_as": str(b_ia),
            "link_to": rel.to_json(a_core, True),
            "mtu": net.getMtu(),
        }
        # TODO: additional settings according to config of 'as_a'

        b_iface = {
            "underlay": {
                "local": f"{b_addr}:{b_port}",
                "remote": f"{a_addr}:{a_port}",
            },
            "isd_as": str(a_ia),
            "link_to": rel.to_json(b_core, False),
            "mtu": net.getMtu(),
        }
        # TODO: additional settings according to config of 'as_b'

        # XXX(benthor): Remote interface id could probably be added
        # regardless of LinkType but might then undermine SCION's
        # discovery mechanism of remote interface ids. This way is
        # more conservative: Only add 'remote_interface_id' field to
        # dicts if LinkType is Peer.
        #
        # WARNING: As of February 2023, this feature is not yet
        # supported in upstream SCION.
        if rel == LinkType.Peer:
            self._log("WARNING: As of February 2023 SCION peering links are not supported in upstream SCION")
            a_iface["remote_interface_id"] = int(b_ifid)
            b_iface["remote_interface_id"] = int(a_ifid)

        # Create interfaces in BRs
        a_router.addScionInterface(int(a_ifid), a_iface)
        b_router.addScionInterface(int(b_ifid), b_iface)
