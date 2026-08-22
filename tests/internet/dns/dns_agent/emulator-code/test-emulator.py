#!/usr/bin/env python3

import os
import sys


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
sys.path.insert(0, REPO_ROOT)

from examples.internet.B02a_domain_registration import domain_registration
from seedemu.compiler import Docker, Platform


emu = domain_registration.build_emulator()
emu.render()
emu.compile(Docker(platform=Platform.AMD64), "./output", override=True)
