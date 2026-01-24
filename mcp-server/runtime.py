import sys
import os

# Add parent directory to path to import seedemu
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from seedemu.core import Emulator
from seedemu.layers import Base

class EmulatorRuntime:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmulatorRuntime, cls).__new__(cls)
            cls._instance.reset()
        return cls._instance

    def reset(self):
        self.emulator = Emulator()
        self.base = Base()
        self.emulator.addLayer(self.base)
        self.rendered = False

    def get_emulator(self) -> Emulator:
        return self.emulator

    def get_base(self) -> Base:
        return self.base

# Global singleton
runtime = EmulatorRuntime()
