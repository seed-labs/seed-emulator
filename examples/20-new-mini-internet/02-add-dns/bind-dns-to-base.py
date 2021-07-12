#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.hooks import ResolvConfHook
from seedemu.compiler import Docker


emuA = Emulator()
emuB = Emulator()

emuA.load('../base-component.bin')
emuB.load('./dns-component.bin')

emu = emuA.merge(emuB, DEFAULT_MERGERS)

###############################################
# Bind virtual node

emu.addBinding(Binding('a-root-server', filter=Filter(asn=171), action=Action.FIRST))
emu.addBinding(Binding('b-root-server', filter=Filter(asn=150), action=Action.FIRST))
emu.addBinding(Binding('a-com-server', filter=Filter(asn=151), action=Action.FIRST))
emu.addBinding(Binding('b-com-server', filter=Filter(asn=152), action=Action.FIRST))
emu.addBinding(Binding('a-net-server', filter=Filter(asn=152), action=Action.FIRST))
emu.addBinding(Binding('a-edu-server', filter=Filter(asn=153), action=Action.FIRST))
emu.addBinding(Binding('a-cn-server', filter=Filter(asn=154), action=Action.FIRST))
emu.addBinding(Binding('b-cn-server', filter=Filter(asn=160), action=Action.FIRST))
emu.addBinding(Binding('ns-twitter-com', filter=Filter(asn=161), action=Action.FIRST))
emu.addBinding(Binding('ns-google-com', filter=Filter(asn=162), action=Action.FIRST))
emu.addBinding(Binding('ns-example-net', filter=Filter(asn=163), action=Action.FIRST))
emu.addBinding(Binding('ns-syr-edu', filter=Filter(asn=164), action=Action.FIRST))
emu.addBinding(Binding('ns-weibo-cn', filter=Filter(asn=170), action=Action.FIRST))

###############################################
# Render and compile
emu.render()
emu.compile(Docker(), './output')

