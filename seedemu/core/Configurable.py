from .Emulator import Emulator

class Configurable(object):
    """!
    @brief Configurable class.

    Configurable classs are classes that need to be configure before rendering.
    """

    def configure(self, emulator: Emulator):
        """!
        @brief Configure the class.

        @param emulator emulator object to use.
        """
        return