from __future__ import annotations
from .Merger import Merger
from .Registry import Registry, Registrable, Printable
from typing import Dict, Set, Tuple, List
from sys import stderr
import pickle

class LayerDatabase(Registrable, Printable):

    db: Dict[str, Tuple[Layer, bool]]

    def __init__(self):
        self.db = {}

    def print(self, indentation: int) -> str:
        return ' ' * indentation + 'LayerDatabase\n'

class Simulator:

    __registry: Registry
    __layers: Dict[str, Tuple[Layer, bool]]
    __dependencies_db: Dict[str, Set[Tuple[str, bool]]]
    __rendered: bool

    def __init__(self):
        self.__rendered = False
        self.__dependencies_db = {}
        self.__registry = Registry()
        self.__layers = LayerDatabase()
        self.__registry.register('seedsim', 'dict', 'layersdb', self.__layers)

    def __render(self, layerName, optional: bool, configure: bool):
        """!
        @brief Render a layer.
        
        @param layerName name of layer.
        @throws AssertionError if dependencies unmet 
        """
        verb = 'configure' if configure else 'render'

        self.__log('requesting {}: {}'.format(verb, layerName))

        if optional and layerName not in self.__layers.db:
            self.__log('{}: not found but is optional, skipping'.format(layerName))
            return

        assert layerName in self.__layers.db, 'Layer {} requried but missing'.format(layerName)

        (layer, done) = self.__layers.db[layerName]
        if done:
            self.__log('{}: already done, skipping'.format(layerName))
            return

        if layerName in self.__dependencies_db:
            for (dep, opt) in self.__dependencies_db[layerName]:
                self.__log('{}: requesting dependency render: {}'.format(layerName, dep))
                self.__render(dep, opt, configure)

        self.__log('entering {}...'.format(layerName))

        hooks: List[Hook] = []
        for hook in self.__registry.getByType('seedsim', 'hook'):
            if hook.getTargetLayer() == layerName: hooks.append(hook)
        
        if configure:
            self.__log('invoking pre-configure hooks for {}...'.format(layerName))
            for hook in hooks: hook.preconfigure(self)
            self.__log('configureing {}...'.format(layerName))
            layer.configure(self)
            self.__log('invoking post-configure hooks for {}...'.format(layerName))
            for hook in hooks: hook.postconfigure(self)
        else:
            self.__log('invoking pre-render hooks for {}...'.format(layerName))
            for hook in hooks: hook.prerender(self)
            self.__log('rendering {}...'.format(layerName))
            layer.render(self)
            self.__log('invoking post-render hooks for {}...'.format(layerName))
            for hook in hooks: hook.postrender(self)
        
        self.__log('done: {}'.format(layerName))
        self.__layers.db[layerName] = (layer, True)
    
    def __loadDependencies(self, deps: Dict[str, Set[Tuple[str, bool]]]):
        for (layer, deps) in deps.items():
            if not layer in self.__dependencies_db:
                self.__dependencies_db[layer] = deps
                continue

            self.__dependencies_db[layer] |= deps

    def __log(self, message: str):
        print('== Simulator: {}'.format(message), file=stderr)

    def rendered(self) -> bool:
        """!
        @brief test if the simulator is rendered.

        @retrns True if rendered
        """
        return self.__rendered

    def addHook(self, hook: Hook):
        self.__registry.register('seedsim', 'hook', hook.getName(), hook)

    def addLayer(self, layer: Layer):
        """!
        @brief Add a layer.

        @param layer layer to add.
        @throws AssertionError if layer already exist.
        """

        lname = layer.getName()
        assert lname not in self.__layers.db, 'layer {} already added.'.format(lname)
        self.__registry.register('seedsim', 'layer', lname, layer)
        self.__layers.db[lname] = (layer, False)

    def getLayer(self, layerName: str) -> Layer:
        return self.__registry.get('seedsim', 'layer', layerName)

    def render(self):
        """!
        @brief Render.

        @throws AssertionError if dependencies unmet 
        """
        assert not self.__rendered, 'already rendered.'

        for (layer, _) in self.__layers.db.values():
            self.__loadDependencies(layer.getDependencies())

        for layerName in self.__layers.db.keys():
            self.__render(layerName, False, True)

        # FIXME
        for (name, (layer, _)) in self.__layers.db.items():
            self.__layers.db[name] = (layer, False)

        for layerName in self.__layers.db.keys():
            self.__render(layerName, False, False)

        self.__rendered = True

    def compile(self, compiler: 'Compiler', out: str, override: bool = False):
        """!
        @brief Compile the simulation.

        @param compiler to use.
        @param output output directory path.
        @param override (optional) override the output folder if it already
        exist. False by defualt.
        """
        compiler.compile(self, out, override)

    def getRegistry(self) -> Registry: 
        return self.__registry

    def removeLayer(self, layerName: str) -> bool:
        raise NotImplementedError('todo')

    def merge(self, other: Simulator, mergers: List[Merger]) -> Simulator:
        raise NotImplementedError('todo')

    def dump(self, fileName: str):
        assert self.__render, 'cannot dump simulation after render.'
        with open(fileName, 'wb') as f:
            pickle.dump(self.__registry, f)

    def load(self, fileName: str):
        with open(fileName, 'rb') as f:
            self.__rendered = False
            self.__dependencies_db = {}
            self.__registry = pickle.load(f)
            self.__layers = self.__registry.get('seedsim', 'dict', 'layersdb')
