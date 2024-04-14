from enum import Enum

class Distribution(Enum):
    """An enumerated class that defines the valid operating systems/distributions for Kubo.
    """
    LINUX = 'linux'
    FREEBSD = 'freebsd'
    OPENBSD = 'openbsd'
    WINDOWS = 'windows'
    DARWIN = 'darwin'

class Architecture(Enum):
    """An enumerated class that defines the valid architectures for Kubo.
    """
    X64 = 'amd64'
    X86 = '386'
    ARM64 = 'arm64'
    ARM = 'arm'