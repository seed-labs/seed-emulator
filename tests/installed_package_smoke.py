"""Validate an installed SeedEmu distribution outside its source checkout.

Run with python -I after installing only a wheel or sdist and its declared
runtime dependencies. No Docker daemon or emulation containers are started.
"""

import argparse
import importlib
from importlib import metadata, resources
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples", type=Path)
    parser.add_argument("--workflow", type=Path,
                        help="Read the compile matrix from the existing example CI workflow")
    parser.add_argument("--expected-version")
    args = parser.parse_args()

    import seedemu
    from seedemu.compiler import Docker, Platform
    from seedemu.containerBundle import ContainerBundle, InternetMap
    from seedemu.core import Binding, Emulator, Filter
    from seedemu.layers import Base, Ebgp, EtcHosts, Routing
    from seedemu.services import WebService
    from seedemu.testing import InternetTestRunner
    from seedemu.k8sTools import K8sTools
    import yaml

    installed = Path(seedemu.__file__).resolve()
    assert "site-packages" in installed.parts, installed
    version = metadata.version("seedemu")
    if args.expected_version:
        assert version == args.expected_version, (version, args.expected_version)
    assert all((ContainerBundle, InternetTestRunner, K8sTools))
    for name in ("seedemu.generators", "seedemu.mergers", "seedemu.raps",
                 "seedemu.utilities", "seedemu.k8sTools.config"):
        importlib.import_module(name)
    bundled = resources.files("seedemu.k8sTools.resources")
    for name in ("setup/ansible/k3s-install.yml", "setup/applyK3sCluster.py",
                 "running/manageRunningStage.py"):
        assert bundled.joinpath(name).is_file(), name
    assert yaml.safe_load(bundled.joinpath("setup/ansible/k3s-install.yml").read_text())

    with tempfile.TemporaryDirectory(prefix="seedemu-installed-") as temporary:
        temporary = Path(temporary)
        # Exercise rendered network APIs and both Docker architectures using
        # only the installed package and a temporary working directory.
        for platform in (Platform.AMD64, Platform.ARM64):
            emulator, base = Emulator(), Base()
            base.createInternetExchange(100)
            ebgp, web = Ebgp(), WebService()
            hosts = []
            for asn in (150, 151):
                system = base.createAutonomousSystem(asn)
                system.createNetwork("net0")
                system.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
                host = system.createHost("web").joinNetwork("net0")
                hosts.append(host)
                name = "web{}".format(asn)
                web.install(name)
                emulator.addBinding(Binding(name, filter=Filter(asn=asn, nodeName="web")))
                ebgp.addRsPeer(100, asn)
            for layer in (base, Routing(), ebgp, web,
                          EtcHosts().addRecord("xyz.seed.net", "10.150.0.30")):
                emulator.addLayer(layer)
            emulator.render()
            network = base.getAutonomousSystem(150).getNetwork("net0")
            assert network.getFullName() == "net_150_net0"
            assert network.isValidRouter("10.150.0.254")
            assert not network.isIpAddressAvailable("10.150.0.71")
            assert network.isIpAddressAvailable("10.150.0.30")
            assert len(network.getRouters()) == 1
            for host in hosts:
                assert "10.150.0.30 xyz.seed.net" in host.getFile("/tmp/etc-hosts").get()[1]
            compiler = Docker(platform=platform)
            internet_map = InternetMap(emulator, ".package-check")
            internet_map.setPorts([8091, 8092, 8093])
            compiler.addContainerBundle(internet_map)
            output = temporary / platform.name
            cwd = Path.cwd()
            try:
                emulator.compile(compiler, str(output))
            finally:
                os.chdir(cwd)
            compose = yaml.safe_load((output / "docker-compose.yml").read_text())
            assert "net_150_net0" in compose["networks"]
            assert len(compose["services"]) >= 6
            if shutil.which("docker"):
                subprocess.run(["docker", "compose", "-f", str(output / "docker-compose.yml"),
                                "config", "--quiet"], check=True, capture_output=True, text=True)
        print("SeedEmu {} wheel/sdist imports, resources and AMD64/ARM64 compilation passed".format(version))

        if args.examples:
            if not args.workflow:
                parser.error("--workflow is required with --examples")
            workflow = yaml.safe_load(args.workflow.read_text())
            matrix = workflow["jobs"]["compile-selected-examples"]["strategy"]["matrix"]["example"]
            examples = temporary / "examples"
            shutil.copytree(args.examples, examples,
                            ignore=shutil.ignore_patterns("output*", "__pycache__", "*.bin"))
            for item in matrix:
                manifest = temporary / item["manifest"]
                artifacts = temporary / "artifacts" / item["code"]
                result = subprocess.run(
                    [sys.executable, "-I", "-m", "seedemu.testing.cli", "compile", str(manifest),
                     "--artifact-dir", str(artifacts)],
                    cwd=temporary, capture_output=True, text=True, timeout=660,
                )
                if result.returncode:
                    details = "\n".join(p.read_text() for p in artifacts.rglob("*.log"))
                    raise RuntimeError(result.stdout + result.stderr + details)
                print("{} installed-package compilation passed".format(item["code"]), flush=True)
            print("All {} CI examples compiled with installed SeedEmu".format(len(matrix)))


if __name__ == "__main__":
    main()
