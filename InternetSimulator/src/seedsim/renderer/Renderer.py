from seedsim.core import Printable, ScopedRegistry
from seedsim.layers import Layer
from typing import List, Tuple, Dict
from sys import stderr

class Renderer(Printable):
    """!
    @brief The Renderer.
    """

    __layers: Dict[str, Tuple[Layer, bool]]
    __reg = ScopedRegistry('seedsim')

    def __init__(self):
        """!
        @brief Renderer constructor.
        """
        self.__layers = {}

    def addLayer(self, layer: Layer):
        """!
        @brief Add a layer.

        @param layer layer to add.
        @throws AssertionError if layer already exist.
        """

        lname = layer.getName()
        assert lname not in self.__layers, 'layer {} already added.'.format(lname)
        self.__layers[lname] = (layer, False)
        self.__reg.register('layer', lname, layer)

    def __render(self, layerName: str):
        """!
        @brief Render a layer.
        
        @param layerName name of layer.
        @throws AssertionError if dependencies unmet 
        """
        self.__log('requesting render: {}'.format(layerName))

        assert layerName in self.__layers, 'Layer {} requried but missing'.format(layerName)

        (layer, done) = self.__layers[layerName]
        if done:
            self.__log('{}: already rendered, skipping'.format(layerName))
            return

        for dep in layer.getDependencies():
            self.__log('{}: requesting dependency render: {}'.format(layerName, dep))
            self.__render(dep)

        if layer.getName() in layer.reverseDependencies:
            rdeps = layer.reverseDependencies[layer.getName()]
            for dep in rdeps:
                self.__log('{}: requesting reverse-dependency render: {}'.format(layerName, dep))
                self.__render(dep)

        self.__log('rendering {}...'.format(layerName))
        layer.onRender()
        self.__log('done: {}'.format(layerName))
        self.__layers[layerName] = (layer, True)

    def render(self):
        """!
        @brief Render.

        @throws AssertionError if dependencies unmet 
        """
        for layerName in self.__layers.keys():
            self.__render(layerName)

    def print(self, indent: int) -> str:
        out = ''
        for (k, (v, _)) in self.__layers.items():
            out += v.print(indent)

        return out

    def __log(self, message: str):
        print('== Renderer: {}'.format(message), file=stderr)


        
