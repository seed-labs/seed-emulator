#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.hooks import ResolvConfHook
from seedemu.compiler import Docker


emuA = Emulator()
emuB = Emulator()

emuA.load('../base-component.bin')
emuB.load('dns-component.bin')

emu = emuA.merge(emuB, DEFAULT_MERGERS)

###############################################
# Bind virtual node



emu.render()
emu.compile(Docker(), './dns-binding')


