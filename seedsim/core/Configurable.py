from .Simulator import Simulator

class Configurable(object):
    """!
    @brief Configurable class.

    Configurable classs are classes that need to be configure before rendering.
    """

    def configure(self, simulator: Simulator):
        """!
        @brief Configure the class.

        @param simulator simulator object to use.
        """
        raise NotImplementedError('configure not implemented.')