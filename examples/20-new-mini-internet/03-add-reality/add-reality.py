#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.hooks import ResolvConfHook
from seedemu.compiler import Docker
from seedemu.services import DomainNameService, DomainNameCachingService
from seedemu.layers import Base, Ebgp, PeerRelationship
from seedemu.raps import OpenVpnRemoteAccessProvider


emu = Emulator()

# Load the pre-built components and merge them
emu.load('./prebuilt-emulator.bin')
base: Base = emu.getLayer('Base')
ebgp: Ebgp = emu.getLayer('Ebgp')
ovpn    = OpenVpnRemoteAccessProvider()


as11872 = base.createAutonomousSystem(11872)
as11872.createRealWorldRouter('rw').joinNetwork('ix101', '10.101.0.118')

ebgp.addPrivatePeering(101, 2, 11872, abRelationship = PeerRelationship.Unfiltered)


# Enable Remote Access on net0 in AS-152
as152 = base.getAutonomousSystem(152)
as152.getNetwork('net0').enableRemoteAccess(ovpn)



###############################################
# Render the emulation and further customization
emu.render()

# After the rendering, we can now find the physical node for
# a given virtual node, and further customize the physical node.
emu.getBindingFor('a-root-server').setDisplayName('A-Root')
emu.getBindingFor('b-root-server').setDisplayName('B-Root')
emu.getBindingFor('a-com-server').setDisplayName('A-COM')
emu.getBindingFor('b-com-server').setDisplayName('B-COM')
emu.getBindingFor('a-net-server').setDisplayName('NET')
emu.getBindingFor('a-edu-server').setDisplayName('EDU')
emu.getBindingFor('a-cn-server').setDisplayName('A-CN')
emu.getBindingFor('b-cn-server').setDisplayName('B-CN')
emu.getBindingFor('ns-twitter-com').setDisplayName('Twitter')
emu.getBindingFor('ns-google-com').setDisplayName('Google')
emu.getBindingFor('ns-example-net').setDisplayName('Example')
emu.getBindingFor('ns-syr-edu').setDisplayName('Syracuse')
emu.getBindingFor('ns-weibo-cn').setDisplayName('微博')

emu.getBindingFor('global-dns').setDisplayName('Global DNS')


###############################################
# Render the emulation

emu.compile(Docker(), './output')
