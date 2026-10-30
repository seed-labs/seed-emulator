#!/usr/bin/env python3
# encoding: utf-8

from argparse import ArgumentParser
from pathlib import Path

from seedemu import *
from examples.basic.A01_transit_as import transit_as


def parse_args():
    parser = ArgumentParser(description="Customize a SeedEmu node.")
    parser.add_argument("--platform", choices=("amd", "arm"), default="amd")
    parser.add_argument("--output", default="output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    platform = Platform.AMD64 if args.platform == "amd" else Platform.ARM64
    output = Path(args.output)

    # Load the pre-built component from example A01_transit_as.
    transit_as.run(dumpfile="./base_component.bin")

    emu = Emulator()
    emu.load("./base_component.bin")

    base = emu.getLayer("Base")
    as152 = base.getAutonomousSystem(152)
    node = as152.getHost("host0")

    # Select a runtime profile; the compiler decides how to realize it.
    node.setBaseSystem(BaseSystem.SEEDEMU_ROUTER)
    assert node.getBaseSystem() == BaseSystem.SEEDEMU_ROUTER

    assert BaseSystem.SEEDEMU_ROUTER.contains(BaseSystem.SEEDEMU_BASE)
    assert BaseSystem.SEEDEMU_BASE.contains(BaseSystem.UBUNTU_20_04)

    # Dockerfile: RUN apt-get update && apt-get install -y
    #                     --no-install-recommends python3
    node.addSoftware("python3")

    # Dockerfile: RUN curl http://example.com
    node.addBuildCommand("curl http://example.com")

    # Dockerfile: COPY <generated-name> /myprog.py
    node.importFile(
        hostpath=str(Path.cwd() / "myprog.py"),
        containerpath="/myprog.py",
    )

    # Dockerfile: COPY <generated-name> /file.txt
    node.setFile(path="/file.txt", content="hello world")

    # Add a finite ping check to start.sh.
    node.insertStartCommand(0, "ping -c 1 1.2.3.4 >/dev/null || true")

    # Add "python3 /myprog.py &" to start.sh.
    node.appendStartCommand("python3 /myprog.py", fork=True)

    emu.render()
    docker = Docker(platform=platform)
    # Add Internet visualization services: topology, geographic map, and traffic observation.
    # The second argument is a container name suffix that distinguishes bundle instances.
    internet_map_bundle = InternetMap(emu, ".map.seed")
    # Provide a host port pool (range excludes the stop value); InternetMap needs at least 3 ports.
    internet_map_bundle.setPorts(list(range(8081, 8089)))
    # Register the bundle with the Docker compiler to generate its containers during emu.compile().
    docker.addContainerBundle(internet_map_bundle)
    emu.compile(docker, str(output), override=True)


if __name__ == "__main__":
    main()