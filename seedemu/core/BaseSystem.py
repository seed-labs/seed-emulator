from .SystemProfile import SystemProfile


class BaseSystem:
    """Built-in SeedEmu system profiles."""

    UBUNTU_20_04 = SystemProfile("ubuntu20.04")
    SEEDEMU_BASE = SystemProfile("seedemu-base", subset=UBUNTU_20_04)
    SEEDEMU_ROUTER = SystemProfile("seedemu-router", subset=SEEDEMU_BASE)
    DEFAULT = SEEDEMU_BASE
