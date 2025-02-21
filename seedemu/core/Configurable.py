from .Emulator import Emulator
from typing import List

class Configurable(object):
    """!
    @brief Configurable class.

    Configurable classes are classes that need to be configure before rendering.
    """

    def __init__(self):
        """!
        @brief create a new Configurable object.
        """
        super().__init__()

    def configure(self, emulator: Emulator):
        """!
        @brief Configure the class.

        @param emulator emulator object to use.
        """
        return


# other ideas were: FeatureConfigurable, AdaptiveConfigurable or Tunable
class DynamicConfigurable(Configurable):
    """!
    @brief Dynamically Configurable class.

    @copydetails Configurable
    Opposed to ordinary static configurables, dynamic ones offer users
    to tune values for a set of options/parameters beforehand,
    which are then considered during configuration.
    """

    def __init__(self):
        """!
        @brief create a new Configurable object.
        """
        super().__init__()

    def getAvailableOptions(self) -> List["Option"]:
        """!
        @brief some configurables (such as Layers) might provide a set of options.
        @note Options are strong-types which are provided alongside the respective Layer.
        So the user cannot create just any, but only predefined ones,
        which you can code against in you Layer impl.

        """
        return []

    def _prepare(self, emulator: Emulator):
        """! @brief establish global default settings
        @note if users do not override options for individual Customizables
        such as Nodes or ASes the Layers will resort to global defaults as a fallback.
        Override this method in your Layer if you want more targeted
        setting of Options i.e. only on border-routers or hosts etc..
        """
        from .Scope import Scope, ScopeTier

        # set options on nodes directly
        reg = emulator.getRegistry()
        all_nodes = [
            obj
            for (scope, typ, name), obj in reg.getAll().items()
            if typ in ["rnode", "hnode", "csnode", "rsnode"]
        ]
        for n in all_nodes:
            for o in self.getAvailableOptions():
                n.setOption(o, Scope(ScopeTier.Global))

    def configure(self, emulator: Emulator):

        self._prepare(emulator)
        # here the options are needed for decision making..
        super().configure(emulator)
