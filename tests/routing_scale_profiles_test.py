#!/usr/bin/env python3

import unittest

from seedemu.core import Emulator
from seedemu.layers import Base, Ibgp, Ospf, Routing


class RoutingScaleProfileTest(unittest.TestCase):
    def _build_router_conf(self, routing_mode: str = 'default', ospf_mode: str = 'default') -> tuple[str, str]:
        emulator = Emulator()
        base = Base()
        routing = Routing().setKernelExportMode(routing_mode)
        ospf = Ospf().setTimingProfile(ospf_mode)
        ibgp = Ibgp()

        emulator.addLayer(base)
        emulator.addLayer(routing)
        emulator.addLayer(ospf)
        emulator.addLayer(ibgp)

        asn = 150
        asobj = base.createAutonomousSystem(asn)
        asobj.createNetwork('net0')
        asobj.createRouter('r0').joinNetwork('net0')
        asobj.createRouter('r1').joinNetwork('net0')

        emulator.render()

        router = base.getAutonomousSystem(asn).getRouter('r0')
        bird_conf = router.getFile('/etc/bird/bird.conf').get()[1]
        kernel_conf = ''
        for file_obj in router.getFiles():
            path, content = file_obj.get()
            if path == '/etc/bird/conf/kernel.conf':
                kernel_conf = content
                break
        return bird_conf, kernel_conf

    def test_default_routing_profile_keeps_inline_kernel_protocol(self):
        bird_conf, kernel_conf = self._build_router_conf(routing_mode='default')

        self.assertIn('protocol kernel {', bird_conf)
        self.assertNotIn('include "/etc/bird/conf/*.conf";', bird_conf)
        self.assertEqual(kernel_conf, '')

    def test_device_ospf_only_profile_writes_kernel_override(self):
        bird_conf, kernel_conf = self._build_router_conf(routing_mode='device_ospf_only')

        self.assertIn('include "/etc/bird/conf/*.conf";', bird_conf)
        self.assertNotIn('protocol kernel {', bird_conf)
        self.assertIn('protocol kernel {', kernel_conf)
        self.assertIn('if source = RTS_DEVICE then accept;', kernel_conf)
        self.assertIn('if source = RTS_OSPF then accept;', kernel_conf)
        self.assertIn('reject;', kernel_conf)

    def test_default_ospf_profile_keeps_fast_hello(self):
        bird_conf, _ = self._build_router_conf(ospf_mode='default')

        self.assertIn('hello 1; dead count 2;', bird_conf)
        self.assertNotIn('tick 3;', bird_conf)

    def test_large_scale_ospf_profile_uses_slow_timers(self):
        bird_conf, _ = self._build_router_conf(ospf_mode='large_scale')

        self.assertIn('tick 3;', bird_conf)
        self.assertIn('hello 30; dead 36000; type pointopoint; retransmit 20;', bird_conf)


if __name__ == '__main__':
    unittest.main()
