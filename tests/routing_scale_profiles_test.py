#!/usr/bin/env python3

import os
import tempfile
import unittest
from pathlib import Path

from seedemu.compiler import Docker
from seedemu.core import Emulator
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing


class RoutingLegacyDefaultsTest(unittest.TestCase):
    def _build_emulator(self):
        emulator = Emulator()
        base = Base()
        routing = Routing()
        ebgp = Ebgp()
        ibgp = Ibgp()
        ospf = Ospf()

        ix100 = base.createInternetExchange(100)
        _ = ix100

        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        r150_0 = as150.createRouter("r0").joinNetwork("net0")
        as150.createRouter("r1").joinNetwork("net0")
        r150_0.joinNetwork("ix100")
        r150_0.makeRouteReflector(True)

        as151 = base.createAutonomousSystem(151)
        as151.createNetwork("net0")
        r151_0 = as151.createRouter("r0").joinNetwork("net0")
        r151_0.joinNetwork("ix100")

        ebgp.addPrivatePeering(100, 150, 151, PeerRelationship.Peer)

        emulator.addLayer(base)
        emulator.addLayer(routing)
        emulator.addLayer(ebgp)
        emulator.addLayer(ibgp)
        emulator.addLayer(ospf)
        emulator.render()
        return emulator, base

    def test_legacy_default_routing_and_ospf_are_rendered(self):
        _, base = self._build_emulator()
        router = base.getAutonomousSystem(150).getRouter("r0")
        bird_conf = router.getFile("/etc/bird/bird.conf").get()[1]
        kernel_conf = router.getFile("/etc/bird/conf/kernel.conf").get()[1]

        self.assertIn('include "/etc/bird/conf/*.conf";', bird_conf)
        self.assertIn('hello 30;', bird_conf)
        self.assertIn('dead 36000;', bird_conf)
        self.assertIn('if source = RTS_DEVICE then accept;', kernel_conf)
        self.assertIn('if source = RTS_OSPF then accept;', kernel_conf)

    def test_protocol_names_keep_senior_prefixes(self):
        _, base = self._build_emulator()
        rr_router = base.getAutonomousSystem(150).getRouter("r0")
        peer_router = base.getAutonomousSystem(151).getRouter("r0")
        rr_conf = rr_router.getFile("/etc/bird/bird.conf").get()[1]
        peer_conf = peer_router.getFile("/etc/bird/bird.conf").get()[1]

        self.assertIn("protocol bgp Ibgp_to_cli_r1", rr_conf)
        self.assertIn("protocol bgp Ebgp_p_as151", rr_conf)
        self.assertIn("protocol bgp Ebgp_p_as150", peer_conf)

    def test_start_commands_do_not_autostart_bird(self):
        _, base = self._build_emulator()
        router = base.getAutonomousSystem(150).getRouter("r0")
        commands = [command for command, _ in router.getStartCommands()]
        self.assertNotIn("bird -d", commands)

    def test_generated_start_sh_does_not_include_bird_daemon(self):
        emulator, _ = self._build_emulator()
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                emulator.compile(Docker(selfManagedNetwork=True), tmp_dir, override=True)
                dockerfiles = list(Path(tmp_dir).rglob("Dockerfile"))
                self.assertTrue(dockerfiles, "expected generated Dockerfiles")
                checked = 0
                for dockerfile in dockerfiles:
                    content = dockerfile.read_text(encoding="utf-8")
                    match = None
                    for line in content.splitlines():
                        if line.startswith("COPY ") and line.endswith(" /start.sh"):
                            match = line.split()[1]
                            break
                    if not match:
                        continue
                    start_script = dockerfile.parent / match
                    if not start_script.exists():
                        continue
                    checked += 1
                    self.assertNotIn("bird -d", start_script.read_text(encoding="utf-8"))
                self.assertGreater(checked, 0, "expected at least one staged start script")
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
