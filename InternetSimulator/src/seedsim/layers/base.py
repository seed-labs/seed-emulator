from .layer import Layer

class Base(Layer):
    """!
    The base layer.
    """

    def getName(self) -> str:
        return "Base"

    def getDependencies(self):
        return []

    def onRender(self, simulator: Simulator) -> None:
        pass