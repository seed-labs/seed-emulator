from __future__ import annotations
import subprocess
from collections import defaultdict
from os.path import join as pjoin
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, List, Optional, Set, Tuple

from seedemu.core import Emulator, Layer, Node, ScionAutonomousSystem
from seedemu.core.ScionAutonomousSystem import IA
from seedemu.layers import ScionBase


class ScionIsd(Layer):
    """!
    @brief SCION AS to ISD relationship layer.

    This layer configures the membership and status as core AS of SCION ASes in
    SCION Isolation Domains (ISDs). In principle a SCION AS can be a member of
    multiple ISDs simultaneously with different roles as core or non-core AS in
    each ISD. This layer's interface reflects that fact by allowing flexible
    assignment if ASNs to ISDs. In practice however, the current implementation
    of SCION treats the same ASN in different ISDs as entirely unrelated ASes
    [1]. Therefore, we restrict ASes to a single ISD for the moment. Assigning
    an AS to multiple ISDs is detected as an error during rendering.

    [1] [Issue #4293: Overlapping ISDs](https://github.com/scionproto/scion/issues/4293)
    """

    __isd_core: Dict[int, Set[int]]     # Core members (ASNs)
    __isd_members: Dict[int, Set[int]]  # Non-core members (ASNs)
    __cert_issuer: Dict[IA, int]

    def __init__(self):
        super().__init__()
        self.__isd_core = defaultdict(set)
        self.__isd_members = defaultdict(set)
        self.__cert_issuer = {}
        self.addDependency('Routing', False, False)

    def getName(self) -> str:
        return "ScionIsd"

    def addIsdAs(self, isd: int, asn: int, is_core: bool = False) -> 'ScionIsd':
        """!
        @brief Add an AS to an ISD.

        @param isd ID of the ISD.
        @param asn ASN of the AS which joins the ISD.
        @param is_core Whether the AS becomes a core AS of the ISD.

        @returns self
        """
        if is_core:
            self.__isd_core[isd].add(asn)
        else:
            self.__isd_members[isd].add(asn)

    def addIsdAses(self, isd: int, core: Iterable[int], non_core: Iterable[int]) -> 'ScionIsd':
        """!
        @brief Add multiple ASes to an ISD.

        @param isd ID of the ISD.
        @param core Set of ASes that will join as core ASes.
        @param non_core Set of ASes that will join as non-core ASes.

        @returns self
        """
        for asn in core:
            self.__isd_core[isd].add(asn)
        for asn in non_core:
            self.__isd_members[isd].add(asn)

    def getAsIsds(self, asn: int) -> List[Tuple[int, bool]]:
        """!
        @brief Get the ISDs an AS belongs to.

        @returns Pairs of ISD ids and status as core AS in that ISD.
        """
        isds = [(isd, True) for isd, ases in self.__isd_core.items() if asn in ases]
        isds += [(isd, False) for isd, ases in self.__isd_members.items() if asn in ases]
        return isds

    def isCoreAs(self, isd: int, asn: int) -> bool:
        """!
        @brief Check if an AS is a core AS in an ISD.

        @param isd ID of the ISD.
        @param asn ASN of the AS.

        @returns True if the AS is a core AS in the ISD.
        """
        return asn in self.__isd_core[isd]

    def setCertIssuer(self, as_: IA|Tuple[int, int], issuer: int) -> 'ScionIsd':
        """!
        @brief Set certificate issuer for a non-core AS. Ignored for core ASes.

        @param as_ AS for which to set the cert issuer.
        @param issuer ASN of a SCION core as in the same ISD.
        @return self
        """
        self.__cert_issuer[IA(*as_)] = issuer
        return self

    def getCertIssuer(self, as_: IA|Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """!
        @brief Get the cert issuer for a SCION AS in a certain ISD.

        @param as_ for which to get the cert issuer.
        @return ASN of the cert issuer or None if not set.
        """
        return self.__cert_issuer.get(IA(*as_))

    def configure(self, emulator: Emulator) -> None:
        """!
        @brief Set SCION AS attributes.
        """
        reg = emulator.getRegistry()
        base_layer: ScionBase = reg.get('seedemu', 'layer', 'Base')
        assert issubclass(base_layer.__class__, ScionBase)

        for isd, core in self.__isd_core.items():
            for asn in core:
                as_: ScionAutonomousSystem = base_layer.getAutonomousSystem(asn)
                as_.setAsAttributes(isd, ['core', 'voting', 'authoritative', 'issuing'])

    def render(self, emulator: Emulator) -> None:
        """!
        @brief Generate crypto material and sign TRCs.
        """
        reg = emulator.getRegistry()
        base_layer: ScionBase = reg.get('seedemu', 'layer', 'Base')
        assert issubclass(base_layer.__class__, ScionBase)

        with TemporaryDirectory(prefix="seed_scion") as tempdir:
            self.__gen_scion_crypto(base_layer, tempdir)
            for ((scope, type, name), obj) in reg.getAll().items():
                if type in ['rnode', 'csnode', 'hnode']:
                    node: Node = obj
                    asn = node.getAsn()
                    as_: ScionAutonomousSystem = base_layer.getAutonomousSystem(asn)
                    isds = self.getAsIsds(asn)
                    assert len(isds) == 1, f"AS {asn} must be a member of exactly one ISD"
                    self.__provision_crypto(as_, *isds[0], node, tempdir)

    def print(self, indent: int = 0) -> str:
        out = ' ' * indent
        out += 'ScionIsdLayer:\n'

        indent += 4
        for isd, core in self.__isd_core.items():
            out += ' ' * indent
            out += f'Core ASes of ISD{isd}: {core}\n'

        for isd, core in self.__isd_members.items():
            out += ' ' * indent
            out += f'Non-Core ASes of ISD{isd}: {core}\n'

        return out

    def __gen_scion_crypto(self, base_layer: ScionBase, tempdir: str):
        """Generate cryptographic material in a temporary directory on the host."""
        topofile = self.__gen_topofile(base_layer, tempdir)
        self._log("Calling scion-pki")
        try:
            result = subprocess.run(
                ["scion-pki", "testcrypto", "-t", topofile, "-o", tempdir, "--as-validity", "30d"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
        except FileNotFoundError:
            assert False, "scion-pki not found in PATH"

        for line in result.stdout.split('\n'):
            self._log(line)
        assert result.returncode == 0, "scion-pki failed"

    def __gen_topofile(self, base_layer: ScionBase, tempdir: str) -> str:
        """Generate a standard SCION .topo file representing the emulated network."""
        path = pjoin(tempdir, "seed.topo")

        with open(path, 'w') as f:
            f.write("ASes:\n")
            for asn in base_layer.getAsns():
                as_: ScionAutonomousSystem = base_layer.getAutonomousSystem(asn)
                isds = self.getAsIsds(asn)
                isd, is_core = isds[0]
                assert len(isds) == 1, f"AS {asn} must be a member of exactly one ISD"

                f.write(f'  "{isd}-{asn}": ')
                attributes = [f"'{attrib}': true" for attrib in as_.getAsAttributes(isd)]
                if not is_core:
                    assert (isd, asn) in self.__cert_issuer, f"non-core AS{asn} does not have a cert issuer in ISD{isd}"
                    issuer = self.__cert_issuer[(isd, asn)]
                    assert issuer in self.__isd_core[isd] and asn in self.__isd_members[isd]
                    attributes.append(f"'cert_issuer': {isd}-{issuer}")

                f.write("{{{}}}\n".format(", ".join(attributes)))

        return path

    def __provision_crypto(self, as_: ScionAutonomousSystem, isd: int, is_core: bool, node: Node, tempdir: str):
        basedir = "/etc/scion"
        asn = as_.getAsn()

        def copyFile(src, dst):
            # Tempdir will be gone when imports are resolved, therefore we must use setFile
            with open(src, 'rt', encoding='utf8') as file:
                content = file.read()
                # FIXME: The Docker compiler adds an extra newline in generated files
                # (https://github.com/seed-labs/seed-emulator/issues/125).
                # SCION does not accept PEM files with an extra newline, so we strip a newline here
                # that is later added again.
                if content.endswith('\n'):
                    content = content[:-1]
            node.setFile(dst, content)

        def myImport(name):
            copyFile(pjoin(tempdir, f"AS{asn}", "crypto", name), pjoin(basedir, "crypto", name))

        if is_core:
            for kind in ["sensitive", "regular"]:
                myImport(pjoin("voting", f"ISD{isd}-AS{asn}.{kind}.crt"))
                myImport(pjoin("voting", f"{kind}-voting.key"))
                myImport(pjoin("voting", f"{kind}.tmpl"))
            for kind in ["root", "ca"]:
                myImport(pjoin("ca", f"ISD{isd}-AS{asn}.{kind}.crt"))
                myImport(pjoin("ca", f"cp-{kind}.key"))
                myImport(pjoin("ca", f"cp-{kind}.tmpl"))
        myImport(pjoin("as", f"ISD{isd}-AS{asn}.pem"))
        myImport(pjoin("as", "cp-as.key"))
        myImport(pjoin("as", "cp-as.tmpl"))

        #XXX(benthor): trcs need to be known for other isds as well
        for isd in self.__isd_core.keys():
            trcname = f"ISD{isd}-B1-S1.trc"
            copyFile(pjoin(tempdir, f"ISD{isd}", "trcs", trcname), pjoin(basedir, "certs", trcname))

        # Master keys are generated only once per AS
        key0, key1 = as_.getSecretKeys()
        node.setFile(pjoin(basedir, "keys", "master0.key"), key0)
        node.setFile(pjoin(basedir, "keys", "master1.key"), key1)
