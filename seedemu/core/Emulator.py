from __future__ import annotations
from seedemu.core.enums import NetworkType, NodeRole
from .Merger import Mergeable, Merger
from .Registry import Registry, Registrable, Printable
from .Network import Network
from seedemu import core
from typing import Dict, Set, Tuple, List
from sys import prefix, stderr
from ipaddress import IPv4Network
import pickle

class BindingDatabase(Registrable, Printable):
    """!
    @brief Registrable wrapper for Bindings.

    classes needs to be Registrable to be saved in the Registry. wrapping
    bindings database with Registrable allows the bindings to be preserved in
    dumps.
    """

    db: List[core.Binding]
    vpnodes: Dict[str, core.Node]

    def __init__(self):
        """!
        @brief Create a new binding database.
        """

        ## Binding database
        self.db = []

        ## virtual "physical nodes"
        self.vpnodes = {}

    def print(self, indentation: int) -> str:
        """!
        @brief get printable string.

        @param indentation indentation.

        @returns printable string.
        """

        return ' ' * indentation + 'BindingDatabase\n'

class LayerDatabase(Registrable, Printable):
    """!
    @brief Registrable wrapper for Layers.

    classes needs to be Registrable to be saved in the Registry. wrapping
    layers database with Registrable allows the layers to be preserved in dumps.
    """

    db: Dict[str, Tuple[core.Layer, bool]]

    def __init__(self):
        """!
        @brief Build a new layers database.
        """

        ## Layers database
        self.db = {}

    def print(self, indentation: int) -> str:
        """!
        @brief get printable string.

        @param indentation indentation.

        @returns printable string.
        """

        return ' ' * indentation + 'LayerDatabase\n'

class Emulator:
    """!
    @brief The Emulator class.

    Emulator class is the entry point for emulations. 
    """

    __registry: Registry
    __layers: LayerDatabase
    __dependencies_db: Dict[str, Set[Tuple[str, bool]]]
    __rendered: bool
    __bindings: BindingDatabase
    __resolved_bindings: Dict[str, core.Node]

    __service_net: Network
    __service_net_prefix: str

    def __init__(self, serviceNetworkPrefix: str = '192.168.66.0/24'):
        """!
        @brief Construct a new emulation.
        
        @param serviceNetworkPrefix (optional) service network prefix for this
        emulator. A service network is a network that does not take part in the
        emulation, and provide access between the emulation nodes and the host
        node. Service network will not be created unless some layer/service/as
        asks for it.
        """
        self.__rendered = False
        self.__dependencies_db = {}
        self.__resolved_bindings = {}
        self.__registry = Registry()
        self.__layers = LayerDatabase()
        self.__bindings = BindingDatabase()

        self.__registry.register('seedemu', 'dict', 'layersdb', self.__layers)
        self.__registry.register('seedemu', 'list', 'bindingdb', self.__bindings)

        self.__service_net_prefix = '192.168.160.0/23'
        self.__service_net = None

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

        hooks: List[core.Hook] = []
        for hook in self.__registry.getByType('seedemu', 'hook'):
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
        """!
        @brief Load dependencies list.

        @param deps dependencies list.
        """
        for (layer, deps) in deps.items():
            if not layer in self.__dependencies_db:
                self.__dependencies_db[layer] = deps
                continue

            self.__dependencies_db[layer] |= deps

    def __log(self, message: str):
        """!
        @brief log to stderr.

        @param message message.
        """
        print('== Emulator: {}'.format(message), file=stderr)

    def rendered(self) -> bool:
        """!
        @brief test if the emulator is rendered.

        @returns True if rendered
        """
        return self.__rendered

    def addHook(self, hook: core.Hook) -> Emulator:
        """!
        @brief Add a hook.

        @param hook Hook.

        @returns self, for chaining API calls.
        """
        self.__registry.register('seedemu', 'hook', hook.getName(), hook)

        return self

    def addBinding(self, binding: core.Binding) -> Emulator:
        """!
        @brief Add a binding.

        @param binding binding.

        @returns self, for chaining API calls.
        """
        self.__bindings.db.append(binding)

        return self

    def getBindings(self) -> List[core.Binding]:
        """!
        @brief Get all bindings.

        @returns list of bindings.
        """
        return self.__bindings.db

    def addLayer(self, layer: core.Layer) -> Emulator:
        """!
        @brief Add a layer.

        @param layer layer to add.
        @throws AssertionError if layer already exist.

        @returns self, for chaining API calls.
        """

        lname = layer.getName()
        assert lname not in self.__layers.db, 'layer {} already added.'.format(lname)
        self.__registry.register('seedemu', 'layer', lname, layer)
        self.__layers.db[lname] = (layer, False)

        return self

    def getLayer(self, layerName: str) -> core.Layer:
        """!
        @brief Get a layer.

        @param layerName of the layer.
        @returns layer.
        """
        return self.__registry.get('seedemu', 'layer', layerName)

    def getLayers(self) -> List[core.Layer]:
        """!
        @brief Get all layers.

        @returns list of layers.
        """
        return self.__registry.getByType('seedemu', 'layer')

    def resolvVnode(self, vnode: str) -> core.Node:
        """!
        @brief resolve physical node for the given virtual node.

        @param vnode virtual node name.

        @returns physical node.
        """
        if vnode in self.__resolved_bindings: return self.__resolved_bindings[vnode]
        for binding in self.getBindings():
            pnode = binding.getCandidate(vnode, self, True)
            if pnode == None: continue
            return pnode
        assert False, 'cannot resolve vnode {}'.format(vnode)

    def getBindingFor(self, vnode: str) -> core.Node:
        """!
        @brief get physical node for the given virtual node from the
        pre-populated vnode-pnode mappings.

        Note that the bindings are processed in the early render stage, meaning
        calls to this function will always fail before render, and only virtual
        node names that have been used in service will be available to be
        "resolve" to the physical node using this function.

        This is meant to be used by services to find the physical node to
        install their servers on and should not be used for any other purpose. 
        if you try to resolve some arbitrary vnode names to physical node,
        use the resolveVnode function instead.

        tl;dr: don't use this, use resolvVnode, unless you know what you are
        doing.

        @param vnode virtual node.

        @returns physical node.
        """
        assert vnode in self.__resolved_bindings, 'failed to find binding for vnode {}.'.format(vnode)
        return self.__resolved_bindings[vnode]

    def getServiceNetwork(self) -> Network:
        """!
        @brief get the for-service network of this emulation. If one does not
        exist, a new one will be created.

        A for-service network is a network that does not take part in the
        emulation, and provide access between the emulation nodes and the host
        node.

        @returns service network.
        """
        if self.__service_net == None:
            self.__service_net = self.__registry.register('seedemu', 'net', '000_svc', Network('000_svc', NetworkType.Bridge, IPv4Network(self.__service_net_prefix), direct = False))

        return self.__service_net

    def render(self) -> Emulator:
        """!
        @brief Render to emulation.

        @throws AssertionError if dependencies unmet 
        
        @returns self, for chaining API calls.
        """
        assert not self.__rendered, 'already rendered.'

        for (layer, _) in self.__layers.db.values():
            self.__loadDependencies(layer.getDependencies())

        # render base first
        self.__render('Base', False, True)

        # collect all pending vnode names
        self.__log('collecting virtual node names in the emulation...')
        vnodes: List[str] = []
        for (layer, _) in self.__layers.db.values():
            if not isinstance(layer, core.Service): continue
            for (vnode, _) in layer.getPendingTargets().items():
                assert vnode not in vnodes, 'duplicated vnode: {}'.format(vnode)
                vnodes.append(vnode)
        self.__log('found {} virtual nodes.'.format(len(vnodes)))

        # resolv bindings for all vnodes
        self.__log('resolving binding for all virtual nodes...')
        for binding in self.getBindings():
            for vnode in vnodes:
                if vnode in self.__resolved_bindings: continue
                pnode = binding.getCandidate(vnode, self)
                if pnode == None: continue
                self.__log('vnode {} bound to as{}/{}'.format(vnode, pnode.getAsn(), pnode.getName()))
                self.__resolved_bindings[vnode] = pnode

        self.__log('applying changes made to virtual physical nodes to real physical nodes...')
        vpnodes = self.__bindings.vpnodes
        for (vnode, pnode) in self.__resolved_bindings.items():
            if not vnode in vpnodes: continue
            vpnode = vpnodes[vnode]

            self.__log('applying changes made on vnode {} to pnode as{}/{}...'.format(vnode, pnode.getAsn(), pnode.getName()))
            pnode.copySettings(vpnode)

        for layerName in self.__layers.db.keys():
            self.__render(layerName, False, True)

        # FIXME
        for (name, (layer, _)) in self.__layers.db.items():
            self.__layers.db[name] = (layer, False)

        for layerName in self.__layers.db.keys():
            self.__render(layerName, False, False)

        self.__rendered = True

        return self

    def compile(self, compiler: core.Compiler, output: str, override: bool = False) -> Emulator:
        """!
        @brief Compile the simulation.

        @param compiler to use.
        @param output output directory path.
        @param override (optional) override the output folder if it already
        exist. False by defualt.

        @returns self, for chaining API calls.
        """
        compiler.compile(self, output, override)

        return self
    
    def updateOutputDirectory(self, compiler: core.Compiler, callbacks: list) -> Emulator:
        """!
        @brief update the output directory in a flexible way. Each service might need to update it in a different way
        @param compiler to use
        @param callbacks which is a list of custom functions that will be executed to update the output directory
        """

        for func in callbacks:
            func(compiler)

    def getRegistry(self) -> Registry: 
        """!
        @brief Get the Registry.

        @returns Registry.
        """
        return self.__registry

    def getVirtualNode(self, vnode_name: str) -> core.Node:
        """!
        @brief get a virtual "physical" node.

        This API allows you to create a "virtual" physical node for a virtual
        node. A real "Node" instance will be returned, you can make any changes
        to it, and those changes will be copied to the real physical node the
        virtual node has bound to during render.

        Note that all the APIs that require the node to be in an AS will not
        work. Like `getAsn`, `joinNetwork`, etc. You will get an error if you
        use them.

        @param vnode_name virtual node name.

        @returns node
        """
        if vnode_name not in self.__bindings.vpnodes:
            self.__bindings.vpnodes[vnode_name] = core.Node(vnode_name, NodeRole.Host, 0)

        return self.__bindings.vpnodes[vnode_name]

    def setVirtualNode(self, vnode_name: str, node: core.Node) -> Emulator:
        """!
        @brief set a virtual node.

        This API allows you to overwrite an existing, or create new virtual node
        with the given node object.

        You should use the getVirtualNode API instead, unless you know what you
        are doing.

        @param vnode_name virtual node name.
        @param node virtual physical node.

        @returns self, for chaining API calls.
        """
        assert node.getAsn() == 0, 'vponde asn must be 0.'
        self.__bindings.vpnodes[vnode_name] = node

        return self

    def getVirtualNodes(self) -> Dict[str, core.Node]:
        """!
        @brief get dict of virtual "physical" nodes.

        @return dict of nodes where key is virual node name.
        """
        return self.__bindings.vpnodes

    def merge(self, other: Emulator, mergers: List[Merger] = [], vnodePrefix: str = '') -> Emulator:
        """!
        @brief merge two emulators.

        @param other the other emulator.
        @param mergers list of merge handlers.
        @param vnodePrefix prefix to add to the vnodes from the other emulator.

        @returns new emulator.
        """

        new_layers: Dict[Mergeable] = {}
        other_layers: Dict[Mergeable] = {}

        for l in self.getLayers(): new_layers[l.getTypeName()] = l
        for l in other.getLayers(): other_layers[l.getTypeName()] = l

        for l in other_layers.values():
            typename = l.getTypeName()

            if isinstance(l, core.Service):
                l.addPrefix(vnodePrefix)

            if typename not in new_layers.keys():
                new_layers[typename] = l
                continue

            merged = False

            for merger in mergers:
                if merger.getTargetType() != typename: continue
                new_layers[typename] = merger.doMerge(new_layers[typename], l)
                merged = True
            
            assert merged, 'abort: no merger found for {}'.format(typename)

        new_sim = Emulator()
        for l in new_layers.values(): new_sim.addLayer(l)

        for binding in self.getBindings(): new_sim.addBinding(binding)
        for binding in other.getBindings(): new_sim.addBinding(binding)
        
        for hook in self.getRegistry().getByType('seedemu', 'hook'): new_sim.addHook(hook)
        for hook in other.getRegistry().getByType('seedemu', 'hook'): new_sim.addHook(hook)

        for (v, n) in other.getVirtualNodes().items(): new_sim.setVirtualNode(v, n)
        for (v, n) in self.getVirtualNodes().items(): new_sim.setVirtualNode(v, n)

        return new_sim

    def dump(self, fileName: str) -> Emulator:
        """!
        @brief dump the emulation to file.

        @param fileName output path.
        @throws AssertionError if the emulation is already rendered.

        @returns self, for chaining API calls.
        """

        assert not self.__rendered, 'cannot dump emulation after render.'
        with open(fileName, 'wb') as f:
            pickle.dump(self.__registry, f)

        return self

    def load(self, fileName: str) -> Emulator:
        """!
        @brief load emulation from file.

        @param fileName path to the dumped emulation.

        @returns self, for chaining API calls.
        """

        with open(fileName, 'rb') as f:
            self.__rendered = False
            self.__dependencies_db = {}
            self.__registry = pickle.load(f)
            self.__layers = self.__registry.get('seedemu', 'dict', 'layersdb')
            self.__bindings = self.__registry.get('seedemu', 'list', 'bindingdb')

        return self
