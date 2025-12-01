from __future__ import annotations
from typing import Dict, List, Set
from seedemu.core import Emulator
from seedemu.core.Registry import Registry


class PartitionApplier:
    """!
    @brief Apply partition result to split emulator into multiple sub-emulators.
    
    This class takes a partition result and splits the original emulator's
    Registry into multiple registries, each corresponding to a machine.
    """
    
    def __init__(self, emulator: Emulator, partition_result: Dict):
        """!
        @brief Initialize the partition applier.
        
        @param emulator Original rendered Emulator object.
        @param partition_result Partition result from solver.
                              Format: {machine_id: {'as_list': [...], 'ixp_list': [...]}}
        """
        assert emulator.rendered(), "emulator is not rendered."
        self.__emulator = emulator
        self.__partition_result = partition_result
        self.__original_registry = emulator.getRegistry()
    
    def apply(self) -> List[Emulator]:
        """!
        @brief Apply partition and create sub-emulators.
        
        @return List of Emulator objects, one for each machine.
        """
        sub_emulators = []
        
        for machine_id in sorted(self.__partition_result.keys()):
            machine_data = self.__partition_result[machine_id]
            as_list = set(machine_data['as_list'])
            ixp_list = set([ix_id for ix_id, _ in machine_data['ixp_list']])
            
            # Create new registry for this machine
            new_registry = self._create_partitioned_registry(as_list, ixp_list)
            
            # Create new emulator with the partitioned registry
            sub_emu = self._create_emulator_from_registry(new_registry)
            sub_emulators.append(sub_emu)
        
        return sub_emulators
    
    def _create_partitioned_registry(self, as_list: Set[int], ixp_list: Set[int]) -> Registry:
        """!
        @brief Create a new registry containing only objects for specified ASs and IXs.
        
        @param as_list Set of AS numbers to include.
        @param ixp_list Set of IX IDs to include.
        @return New Registry object.
        """
        # Get all objects from the original registry
        all_objects = self.__original_registry.getAll()
        
        # Convert AS list and IX list to strings for scope matching
        as_scopes = {str(asn) for asn in as_list}
        
        # Collect objects to keep
        objects_to_keep = set()
        
        # Keep seedemu-level objects (layers, bindings, hooks, etc.)
        for (scope, type, name), obj in all_objects.items():
            if scope == 'seedemu':
                objects_to_keep.add((scope, type, name))
        
        # Keep AS-related objects
        for (scope, type, name), obj in all_objects.items():
            if scope in as_scopes:
                objects_to_keep.add((scope, type, name))
        
        # Keep IX-related objects
        for (scope, type, name), obj in all_objects.items():
            if scope == 'ix':
                # Extract IX ID from name (format: 'ix100')
                if name.startswith('ix'):
                    try:
                        ix_id = int(name[2:])
                        if ix_id in ixp_list:
                            objects_to_keep.add((scope, type, name))
                    except ValueError:
                        pass
        
        # Create a new registry with only the objects to keep
        filtered_registry = Registry()
        for key in objects_to_keep:
            scope, type, name = key
            obj = all_objects[key]
            filtered_registry.register(scope, type, name, obj)
        
        # Update Base layer to only include relevant ASs and IXs
        # This is important because Base layer has internal __ases and __ixes dictionaries
        if filtered_registry.has('seedemu', 'dict', 'layersdb'):
            layersdb = filtered_registry.get('seedemu', 'dict', 'layersdb')
            if hasattr(layersdb, 'db'):
                from seedemu.layers import Base
                for layer_name, (layer, _) in layersdb.db.items():
                    if isinstance(layer, Base):
                        # Filter ASs and IXs in Base layer
                        # Access private attributes using name mangling
                        base_ases = getattr(layer, '_Base__ases', {})
                        base_ixes = getattr(layer, '_Base__ixes', {})
                        
                        # Keep only relevant ASs and IXs
                        filtered_ases = {asn: as_obj for asn, as_obj in base_ases.items() if asn in as_list}
                        filtered_ixes = {ix_id: ix_obj for ix_id, ix_obj in base_ixes.items() if ix_id in ixp_list}
                        
                        setattr(layer, '_Base__ases', filtered_ases)
                        setattr(layer, '_Base__ixes', filtered_ixes)
        
        return filtered_registry
    
    def _create_emulator_from_registry(self, registry: Registry) -> Emulator:
        """!
        @brief Create a new Emulator from a Registry.
        
        This method extracts layers from the registry and adds them to a new Emulator.
        First, it copies all non-layer objects to the new emulator's registry,
        then adds the layers (which will reference the copied objects).
        
        @param registry Registry object to use.
        @return New Emulator object.
        """
        # Create new emulator
        new_emu = Emulator()
        new_registry = new_emu.getRegistry()
        
        # First, copy all non-seedemu objects (AS nodes, networks, IX objects, etc.)
        # to the new emulator's registry
        all_objects = registry.getAll()
        for (scope, type, name), obj in all_objects.items():
            # Skip seedemu-level objects for now (layers, bindings, hooks)
            # We'll handle them separately
            if scope != 'seedemu':
                if not new_registry.has(scope, type, name):
                    new_registry.register(scope, type, name, obj)
        
        # Get and add layers from registry
        if registry.has('seedemu', 'dict', 'layersdb'):
            layersdb = registry.get('seedemu', 'dict', 'layersdb')
            if hasattr(layersdb, 'db'):
                # Add all layers to the new emulator
                for layer_name, (layer, _) in layersdb.db.items():
                    new_emu.addLayer(layer)
        
        # Get and add bindings from registry
        if registry.has('seedemu', 'list', 'bindingdb'):
            bindingdb = registry.get('seedemu', 'list', 'bindingdb')
            if hasattr(bindingdb, 'db'):
                for binding in bindingdb.db:
                    new_emu.addBinding(binding)
        
        # Get and add hooks from registry
        hooks = registry.getByType('seedemu', 'hook')
        for hook in hooks:
            new_emu.addHook(hook)
        
        # Set emulator as rendered since we're copying from an already rendered emulator
        # Access private __rendered attribute using name mangling
        setattr(new_emu, '_Emulator__rendered', True)
        
        return new_emu

