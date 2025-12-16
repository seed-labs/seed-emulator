from __future__ import annotations

import logging
import os
import re
import requests
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Set, Tuple, Union
from urllib.parse import urlparse

from seedemu.core import (
    AutoRegister,
    Emulator,
    Graphable,
    Interface,
    Layer,
    Network,
    Node,
    Option,
    OptionMode,
    Registry,
    Router,
    ScionAutonomousSystem,
    ScopedRegistry,
)
from seedemu.core.ScionAutonomousSystem import IA
from seedemu.layers import ScionBase, ScionIsd
from seedemu.utilities.BuildtimeDocker import BuildtimeDockerFile, BuildtimeDockerImage, sh


class LinkType(Enum):
    """!
    @brief Type of a SCION link between two ASes.
    """

    Core = "Core"        # Core link between core ASes
    Transit = "Transit"  # Customer-Provider transit link
    Peer = "Peer"        # Non-core AS peering link

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
                assert (
                    not core_as
                ), "Logic error: Core ASes must only provide transit to customers, not receive it!"
                return "PARENT"


class ScionConfigMode(Enum):
    """how shall the /etc/scion config dir contents be handled:"""

    BAKED_IN = 0
    SHARED_FOLDER = 1
    NAMED_VOLUME = 2



class SCION_ETC_CONFIG_VOL(Option, AutoRegister):
    """ this option controls the policy where to put all the SCION related files on the host. """
    value_type = ScionConfigMode

    @classmethod
    def supportedModes(cls) -> OptionMode:
        return OptionMode.BUILD_TIME

    @classmethod
    def default(cls):
        return ScionConfigMode.BAKED_IN


def handleScionConfFile(node, filename: str, filecontent: str, subdir: str = None):
    """ wrapper around 'Node::setFile' for /etc/scion config files
    @param subdir sub path relative to /etc/scion
    """
    if (opt := node.getOption("scion_etc_config_vol")) is not None:
        suffix = f"/{subdir}" if subdir is not None else ""
        match opt.value:
            case ScionConfigMode.SHARED_FOLDER:
                current_dir = os.getcwd()
                path = os.path.join(
                    current_dir, f".shared/{node.getAsn()}/{node.getName()}/etcscion{suffix}"
                )
                os.makedirs(path, exist_ok=True)
                with open(os.path.join(path, filename), "w", encoding="utf-8") as f:
                    f.write(filecontent)
            case _:
                node.setFile(f"/etc/scion{suffix}/{filename}", filecontent)
    else:
        assert False, "implementation error - lacking global default for option"


@dataclass
class CheckoutSpecification:
    """
    Identifies a specific SCION release version or RepoCheckout
    """

    mode: str
    release_location: str
    version: str
    git_repo_url: str
    checkout: str

    def __init__(
        self,
        mode: str = None,
        release_location: str = None,
        version: str = None,
        git_repo_url: str = None,
        checkout: str = None,
    ):
        self.mode = mode if mode else "release"
        self.release_location = (
            release_location
            if release_location
            else "https://github.com/scionproto/scion/releases/download/v0.12.0/scion_0.12.0_amd64_linux.tar.gz"
        )
        self.version = version if version else "v0.12.0"
        self.git_repo_url = git_repo_url if git_repo_url else "https://github.com/scionproto/scion.git"
        self.checkout = checkout if checkout else "v0.12.0"


class SetupSpecification(Enum):
    """describes how exactly the SCION distributables shall be installed"""

    PACKAGES = "UbuntuPackage"
    LOCAL_BUILD = "Compile from sources"

    def __call__(self, *args, **kwargs) -> "SetupSpecification":
        """
        Overloads `()` to return the appropriate object based on the enum variant.
        """
        if self == SetupSpecification.PACKAGES:
            return self
        elif self == SetupSpecification.LOCAL_BUILD:
            if len(args) > 0 and isinstance(args[0], CheckoutSpecification):
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


class ScionBuilder:
    """
    Strategy object that installs SCION distributables on a node based on node setup_spec.
    """

    def __init__(self):
        pass

    def installSCION(self, node: Node):
        spec = node.getOption("setup_spec", prefix="scion")
        assert (
            spec is not None
        ), "implementation error - all nodes are supposed to have a SetupSpecification set by ScionRoutingLayer"

        match s := spec.value:
            case SetupSpecification.LOCAL_BUILD:
                self.__installFromBuild(node, s.checkout_spec)
                self._addSCIONLabPackages(node)
                node.addBuildCommand(
                    "apt-get update && apt download scion-apps-bwtester"
                    " && dpkg --ignore-depends=scion-daemon,scion-dispatcher -i scion-apps-bwtester_3.4.2_amd64.deb"
                )
            case SetupSpecification.PACKAGES:
                self._installFromDebPackage(node)

    def nameOfCmd(self, cmd, node: Node) -> str:
        spec = node.getOption("setup_spec", prefix="scion")
        assert spec is not None, "setup_spec missing"
        assert cmd in ["router", "control", "dispatcher", "daemon"], f"unknown SCION distributable {cmd}"

        match spec.value:
            case SetupSpecification.PACKAGES:
                return {
                    "router": "scion-border-router",
                    "control": "scion-control-service",
                    "dispatcher": "scion-dispatcher",
                    "daemon": "sciond",
                }[cmd]
            case SetupSpecification.LOCAL_BUILD:
                return cmd

    def _addSCIONLabPackages(self, node: Node):
        node.addBuildCommand(
            'echo "deb [trusted=yes] https://packages.netsec.inf.ethz.ch/debian all main"'
            " > /etc/apt/sources.list.d/scionlab.list"
        )

    def _installFromDebPackage(self, node: Node):
        self._addSCIONLabPackages(node)
        node.addBuildCommand(
            "apt-get update && apt-get install -y"
            " scion-border-router scion-control-service scion-daemon scion-dispatcher scion-tools"
            " scion-apps-bwtester"
        )
        node.addSoftware("apt-transport-https")
        node.addSoftware("ca-certificates")
        self.installHelpers(node)

    def __installFromBuild(self, node: Node, s: CheckoutSpecification):
        self.__validateBuildConfiguration(s)
        build_dir = self.__generateBuild(s)
        path_to_binaries = "/bin/scion/"
        node.addSharedFolder(path_to_binaries, build_dir)
        node.addDockerCommand(f"ENV PATH={path_to_binaries}:$PATH ")
        self.installHelpers(node)

    def installHelpers(self, node: Node):
        if node.getOption("rotate_logs", prefix="scion").value == "true":
            node.addSoftware("apache2-utils")
        if node.getOption("use_envsubst", prefix="scion").value == "true":
            node.addSoftware("gettext")

    # ---------------- FIXED INDENTATION STARTS HERE ----------------

    def __validateBuildConfiguration(self, config: CheckoutSpecification):
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
        Check if local path exists OR URL is valid and reachable.

        IMPORTANT:
        - If the SCION release is already cached in .scion_build_output/, do NOT fail just
          because GitHub (or the internet) is temporarily unreachable.
        """

        # Local path: must exist + must be absolute
        if path and self.__is_local_path(path):
            if not os.path.exists(path):
                raise ValueError("SCION local binary location is not valid.")
            if not os.path.isabs(path):
                raise ValueError("Absolute path required for the folder containing binaries")
            return

        # URL: try reachability check, but do NOT hard-fail if cache exists
        if self.__is_http_url(path):
            cached_ok = False

            try:
                m = re.search(r"/download/(v[^/]+)/", path)
                if m:
                    v = m.group(1)  # e.g. "v0.12.0"
                    cached_dir = os.path.join(os.getcwd(), f".scion_build_output/scion_binaries_{v}")
                    if os.path.isdir(cached_dir):
                        cached_ok = True
            except Exception:
                cached_ok = False

            try:
                response = requests.head(path, allow_redirects=True, timeout=30)
                if response.status_code >= 400:
                    if cached_ok:
                        logging.warning(
                            "SCION release URL not reachable, but cached binaries exist; continuing."
                        )
                        return
                    raise Exception("SCION release url is valid but not reachable")
                return
            except requests.RequestException as e:
                logging.error(e)
                if cached_ok:
                    logging.warning(
                        "SCION release URL check failed, but cached binaries exist; continuing."
                    )
                    return
                raise Exception("SCION release url is valid but not reachable")

        raise ValueError("Release location is Neither a valid HTTP URL nor a local path")

    def __is_http_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return result.scheme in ("http", "https") and bool(result.netloc)
        except ValueError:
            return False

    def __is_local_path(self, path: str) -> bool:
        return not self.__is_http_url(path)

    def __validateGitURL(self, url: str):
        if not url.endswith(".git"):
            raise ValueError("URL does not look like a Git repository (missing .git)")
        git_service_url = f"{url}/info/refs?service=git-upload-pack"
        try:
            response = requests.get(git_service_url, timeout=10)
            if not (response.status_code == 200 and "git-upload-pack" in response.text):
                raise ValueError("SCION build repository not found (or not reachable)")
        except requests.RequestException as e:
            logging.error(e)
            raise ValueError("Invalid SCION build repository (not reachable)")

    def __classifyGitCheckout(self, checkout: str) -> str:
        if re.match(r"^[0-9a-fA-F]{40}$", checkout):
            return "commit"
        if re.match(r"^[\w.-]+$", checkout):
            return "tag"
        if re.match(r"^[\w/.-]+$", checkout):
            return "branch"
        return "unknown"

    def __generateGitCloneString(self, repo_url: str, checkout: str) -> str:
        checkout_type = self.__classifyGitCheckout(checkout)
        if checkout_type == "branch":
            return f"git clone -b {checkout} {repo_url} scion"
        elif checkout_type == "tag":
            return f"git clone --branch {checkout} {repo_url} scion"
        elif checkout_type == "commit":
            return f"git clone {repo_url} scion && cd scion && git checkout {checkout}"
        else:
            raise ValueError("Invalid reference type. Must be 'branch', 'tag', or 'commit'.")

    def __generateBuild(self, spec: CheckoutSpecification) -> str:
        if spec.mode == "release":
            if not self.__is_local_path(spec.release_location):
                if not os.path.isdir(f".scion_build_output/scion_binaries_{spec.version}"):
                    SCION_RELEASE_TEMPLATE = f"""FROM alpine
RUN apk add --no-cache wget tar
WORKDIR /app
RUN wget -qO- {spec.release_location} | tar xvz -C /app
"""
                    dockerfile = BuildtimeDockerFile(SCION_RELEASE_TEMPLATE)
                    container = (
                        BuildtimeDockerImage(f"scion-release-fetch-container_{spec.version}")
                        .build(dockerfile)
                        .container()
                    )
                    current_dir = os.getcwd()
                    output_dir = os.path.join(current_dir, f".scion_build_output/scion_binaries_{spec.version}")
                    container.entrypoint("sh").mountVolume(output_dir, "/build").run(
                        '-c "cp -r /app/* /build"'
                    )
                    return output_dir
                else:
                    return os.path.join(os.getcwd(), f".scion_build_output/scion_binaries_{spec.version}")
            else:
                return spec.release_location

        # build from source
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
                '-c "cp -r scion/bin/* /build"'
            )
            return output_dir

        return os.path.join(os.getcwd(), f".scion_build_output/scion_binaries_{spec.checkout}")


class Scion(Layer, Graphable):
    """SCION inter-AS link layer."""

    __links: Dict[Tuple[IA, IA, str, str, LinkType], int]
    __ix_links: Dict[Tuple[int, IA, IA, str, str, LinkType], Dict[str, Any]]
    __if_ids_by_as = {}  # Dict[IA, Set[int]]

    def __init__(self):
        super().__init__()
        self.__links = {}
        self.__ix_links = {}
        self.addDependency("ScionIsd", False, False)

    def getName(self) -> str:
        return "Scion"

    @staticmethod
    def _setIfId(ia: IA, ifid: int):
        ifs = Scion.getIfIds(ia)
        v = ifid in ifs
        ifs.add(ifid)
        Scion.__if_ids_by_as[ia] = ifs
        return v

    @staticmethod
    def getIfIds(ia: IA) -> Set[int]:
        ifs = set()
        if ia in Scion.__if_ids_by_as.keys():
            ifs = Scion.__if_ids_by_as[ia]
        return ifs

    @staticmethod
    def peekNextIfId(ia: IA) -> int:
        ifs = Scion.getIfIds(ia)
        if not ifs:
            return 0
        last = Scion._fst_free_id(ifs)
        return last + 1

    @staticmethod
    def _fst_free_id(ifs: Set[int]) -> int:
        last = -1
        for i in ifs:
            if i - last > 1:
                return last + 1
            else:
                last = i
        return last

    @staticmethod
    def getNextIfId(ia: IA) -> int:
        ifs = Scion.getIfIds(ia)
        if not ifs:
            ifs.add(1)
            ifs.add(0)
            Scion.__if_ids_by_as[ia] = ifs
            return 1

        last = Scion._fst_free_id(ifs)
        ifs.add(last + 1)
        Scion.__if_ids_by_as[ia] = ifs
        return last + 1

    def addXcLink(
        self,
        a: Union[IA, Tuple[int, int]],
        b: Union[IA, Tuple[int, int]],
        linkType: LinkType,
        count: int = 1,
        a_router: str = "",
        b_router: str = "",
    ) -> "Scion":
        a, b = IA(*a), IA(*b)
        assert a.asn != b.asn, f"Cannot link as{a} to itself."
        assert (a, b, a_router, b_router, linkType) not in self.__links, (
            f"Link between as{a} and as{b} of type {linkType} exists already."
        )
        self.__links[(a, b, a_router, b_router, linkType)] = count
        return self

    def addIxLink(
        self,
        ix: int,
        a: Union[IA, Tuple[int, int]],
        b: Union[IA, Tuple[int, int]],
        linkType: LinkType,
        count: int = 1,
        a_router: str = "",
        b_router: str = "",
        **kwargs,
    ) -> "Scion":
        a, b = IA(*a), IA(*b)
        assert a.asn != b.asn, f"Cannot link as{a} to itself."
        assert (a, b, a_router, b_router, linkType) not in self.__links, (
            f"Link between as{a} and as{b} of type {linkType} at ix{ix} exists already."
        )

        key = (ix, a, b, a_router, b_router, linkType)

        if "if_ids" in kwargs:
            ids = kwargs["if_ids"]
            assert not Scion._setIfId(a, ids[0]), f"Interface ID {ids[0]} not unique for IA {a}"
            assert not Scion._setIfId(b, ids[1]), f"Interface ID {ids[1]} not unique for IA {b}"
        else:
            ids = (Scion.getNextIfId(a), Scion.getNextIfId(b))

        if key in self.__ix_links.keys():
            self.__ix_links[key]["count"] += count
        else:
            self.__ix_links[key] = {"count": count, "if_ids": set()}

        self.__ix_links[key]["if_ids"].add(ids)
        return self

    def configure(self, emulator: Emulator) -> None:
        reg = emulator.getRegistry()
        base_layer: ScionBase = reg.get("seedemu", "layer", "Base")
        assert issubclass(base_layer.__class__, ScionBase)
        self._configure_links(reg, base_layer)

    def render(self, emulator: Emulator) -> None:
        pass

    def _doCreateGraphs(self, emulator: Emulator) -> None:
        self._log("Creating SCION graphs...")
        graph = self._addGraph("Scion Connections", False)

        reg = emulator.getRegistry()
        scionIsd_layer: ScionIsd = reg.get("seedemu", "layer", "ScionIsd")

        for (a, b, a_router, b_router, rel), count in self.__links.items():
            a_shape = "doublecircle" if scionIsd_layer.isCoreAs(a.isd, a.asn) else "circle"
            b_shape = "doublecircle" if scionIsd_layer.isCoreAs(b.isd, b.asn) else "circle"

            if not graph.hasVertex(f"AS{a.asn}", f"ISD{a.isd}"):
                graph.addVertex(f"AS{a.asn}", f"ISD{a.isd}", a_shape)
            if not graph.hasVertex(f"AS{b.asn}", f"ISD{b.isd}"):
                graph.addVertex(f"AS{b.asn}", f"ISD{b.isd}", b_shape)

            if rel == LinkType.Core:
                for _ in range(count):
                    graph.addEdge(f"AS{a.asn}", f"AS{b.asn}", f"ISD{a.isd}", f"ISD{b.isd}", style="bold")
            if rel == LinkType.Transit:
                for _ in range(count):
                    graph.addEdge(
                        f"AS{a.asn}",
                        f"AS{b.asn}",
                        f"ISD{a.isd}",
                        f"ISD{b.isd}",
                        alabel="P",
                        blabel="C",
                    )
            if rel == LinkType.Peer:
                for _ in range(count):
                    graph.addEdge(
                        f"AS{a.asn}",
                        f"AS{b.asn}",
                        f"ISD{a.isd}",
                        f"ISD{b.isd}",
                        style="dashed",
                    )

        for (ix, a, b, a_router, b_router, rel), d in self.__ix_links.items():
            count = d["count"]
            ifids = d["if_ids"]
            assert count == len(ifids)
            a_shape = "doublecircle" if scionIsd_layer.isCoreAs(a.isd, a.asn) else "circle"
            b_shape = "doublecircle" if scionIsd_layer.isCoreAs(b.isd, b.asn) else "circle"

            if not graph.hasVertex(f"AS{a.asn}", f"ISD{a.isd}"):
                graph.addVertex(f"AS{a.asn}", f"ISD{a.isd}", a_shape)
            if not graph.hasVertex(f"AS{b.asn}", f"ISD{b.isd}"):
                graph.addVertex(f"AS{b.asn}", f"ISD{b.isd}", b_shape)

            if rel == LinkType.Core:
                for ids in ifids:
                    graph.addEdge(
                        f"AS{a.asn}",
                        f"AS{b.asn}",
                        f"ISD{a.isd}",
                        f"ISD{b.isd}",
                        label=f"IX{ix}",
                        style="bold",
                        alabel=f"#{ids[0]}",
                        blabel=f"#{ids[1]}",
                    )
            elif rel == LinkType.Transit:
                for ids in ifids:
                    graph.addEdge(
                        f"AS{a.asn}",
                        f"AS{b.asn}",
                        f"ISD{a.isd}",
                        f"ISD{b.isd}",
                        label=f"IX{ix}",
                        alabel=f"P #{ids[0]}",
                        blabel=f"C #{ids[1]}",
                    )
            elif rel == LinkType.Peer:
                for ids in ifids:
                    graph.addEdge(
                        f"AS{a.asn}",
                        f"AS{b.asn}",
                        f"ISD{a.isd}",
                        f"ISD{b.isd}",
                        f"IX{ix}",
                        style="dashed",
                        alabel=f"#{ids[0]}",
                        blabel=f"#{ids[1]}",
                    )
            else:
                assert False, f"Invalid LinkType: {rel}"

    def print(self, indent: int = 0) -> str:
        out = " " * indent + "ScionLayer:\n"
        indent += 4

        for (ix, a, b, a_router, b_router, rel), d in self.__ix_links.items():
            count = d["count"]
            out += " " * indent
            out += f"IX{ix}: AS{a}{'' if a_router == '' else '_' + a_router} -({rel})-> "
            out += f"AS{b}{'' if b_router == '' else '_' + b_router}"
            if count > 1:
                out += f" ({count} times)"
            out += "\n"

        for (a, b, a_router, b_router, rel), count in self.__links.items():
            out += " " * indent
            out += f"XC: AS{a}{'' if a_router == '' else '_' + a_router} -({rel})-> "
            out += f"AS{b}{'' if b_router == '' else '_' + b_router}"
            if count > 1:
                out += f" ({count} times)"
            out += "\n"

        return out

    def _configure_links(self, reg: Registry, base_layer: ScionBase) -> None:
        # cross-connect links
        for (a, b, a_router, b_router, rel), count in self.__links.items():
            a_reg = ScopedRegistry(str(a.asn), reg)
            b_reg = ScopedRegistry(str(b.asn), reg)
            a_as = base_layer.getAutonomousSystem(a.asn)
            b_as = base_layer.getAutonomousSystem(b.asn)

            if a_router == "" or b_router == "":
                try:
                    a_router, b_router = self.__get_xc_routers(a.asn, a_reg, b.asn, b_reg)
                except AssertionError:
                    assert False, f"cannot find XC to configure link as{a} --> as{b}"
            else:
                try:
                    a_router = a_reg.get("rnode", a_router)
                except AssertionError:
                    assert False, f"cannot find router {a_router} in as{a}"
                try:
                    b_router = b_reg.get("rnode", b_router)
                except AssertionError:
                    assert False, f"cannot find router {b_router} in as{b}"

            a_ifaddr, a_net, _ = a_router.getCrossConnect(b.asn, b_router.getName())
            b_ifaddr, b_net, _ = b_router.getCrossConnect(a.asn, a_router.getName())
            assert a_net == b_net
            net = reg.get("xc", "net", a_net)
            a_addr = str(a_ifaddr.ip)
            b_addr = str(b_ifaddr.ip)

            for _ in range(count):
                self._log(f"add scion XC link: {a_addr} as{a} -({rel})-> {b_addr} as{b}")
                self.__create_link(a_router, b_router, a, b, a_as, b_as, a_addr, b_addr, net, rel)

        # IX links
        for (ix, a, b, a_router, b_router, rel), d in self.__ix_links.items():
            count = d["count"]
            ix_reg = ScopedRegistry("ix", reg)
            a_reg = ScopedRegistry(str(a.asn), reg)
            b_reg = ScopedRegistry(str(b.asn), reg)
            a_as = base_layer.getAutonomousSystem(a.asn)
            b_as = base_layer.getAutonomousSystem(b.asn)

            ix_net = ix_reg.get("net", f"ix{ix}")
            if a_router == "" or b_router == "":
                a_routers = a_reg.getByType("rnode")
                b_routers = b_reg.getByType("rnode")
            else:
                a_routers = [a_reg.get("rnode", a_router)]
                b_routers = [b_reg.get("rnode", b_router)]

            try:
                a_ixrouter, a_ixif = self.__get_ix_port(a_routers, ix_net)
            except AssertionError:
                assert False, f"cannot resolve scion peering: as{a} not in ix{ix}"
            try:
                b_ixrouter, b_ixif = self.__get_ix_port(b_routers, ix_net)
            except AssertionError:
                assert False, f"cannot resolve scion peering: as{a} not in ix{ix}"

            if "if_ids" in d:
                self._log(f"add scion IX link: {a_ixif.getAddress()} AS{a} -({rel})-> {b_ixif.getAddress()} AS{b}")
                for ids in d["if_ids"]:
                    self.__create_link(
                        a_ixrouter,
                        b_ixrouter,
                        a,
                        b,
                        a_as,
                        b_as,
                        str(a_ixif.getAddress()),
                        str(b_ixif.getAddress()),
                        ix_net,
                        rel,
                        if_ids=ids,
                    )
            else:
                for _ in range(count):
                    self._log(f"add scion IX link: {a_ixif.getAddress()} AS{a} -({rel})-> {b_ixif.getAddress()} AS{b}")
                    self.__create_link(
                        a_ixrouter,
                        b_ixrouter,
                        a,
                        b,
                        a_as,
                        b_as,
                        str(a_ixif.getAddress()),
                        str(b_ixif.getAddress()),
                        ix_net,
                        rel,
                    )

    @staticmethod
    def __get_xc_routers(a: int, a_reg: ScopedRegistry, b: int, b_reg: ScopedRegistry) -> Tuple[Router, Router]:
        for router in a_reg.getByType("brdnode"):
            for peer, asn in router.getCrossConnects().keys():
                if asn == b and b_reg.has("brdnode", peer):
                    return (router, b_reg.get("brdnode", peer))
        assert False

    @staticmethod
    def __get_ix_port(routers: ScopedRegistry, ix_net: Network) -> Tuple[Router, Interface]:
        for router in routers:
            for iface in router.getInterfaces():
                if iface.getNet() == ix_net:
                    return (router, iface)
        assert False

    def __create_link(
        self,
        a_router: "ScionRouter",
        b_router: "ScionRouter",
        a_ia: IA,
        b_ia: IA,
        a_as: ScionAutonomousSystem,
        b_as: ScionAutonomousSystem,
        a_addr: str,
        b_addr: str,
        net: Network,
        rel: LinkType,
        if_ids=None,
    ):
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

        a_core = "core" in a_as.getAsAttributes(a_ia.isd)
        b_core = "core" in b_as.getAsAttributes(b_ia.isd)

        if a_core and b_core:
            assert rel == LinkType.Core, f"Between Core ASes there can only be Core Links! {a_ia} -- {b_ia}"

        a_iface = {
            "underlay": {"local": f"{a_addr}:{a_port}", "remote": f"{b_addr}:{b_port}"},
            "isd_as": str(b_ia),
            "link_to": rel.to_json(a_core, True),
            "mtu": net.getMtu(),
        }

        b_iface = {
            "underlay": {"local": f"{b_addr}:{b_port}", "remote": f"{a_addr}:{a_port}"},
            "isd_as": str(a_ia),
            "link_to": rel.to_json(b_core, False),
            "mtu": net.getMtu(),
        }

        if rel == LinkType.Peer:
            self._log("WARNING: As of February 2023 SCION peering links are not supported in upstream SCION")
            a_iface["remote_interface_id"] = int(b_ifid)
            b_iface["remote_interface_id"] = int(a_ifid)

        a_router.addScionInterface(int(a_ifid), a_iface)
        b_router.addScionInterface(int(b_ifid), b_iface)
