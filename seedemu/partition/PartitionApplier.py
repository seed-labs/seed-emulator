from __future__ import annotations
from typing import Dict, List, Set
from seedemu.core import Emulator
from seedemu.core.Registry import Registry


class PartitionApplier:
    """!
    @brief Apply partition result to split emulator into multiple sub-emulators.
    
    This class takes a partition result and splits the original emulator's
    Registry into multiple registries, each corresponding to a machine.
    After render, all objects (nodes, networks, Route Servers, etc.) are in Registry.
    We simply extract relevant objects for each machine and create new registries.
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
            ixp_list_with_rs = machine_data['ixp_list']  # List of (ix_id, needs_rs)
            
            # Create new registry for this machine
            new_registry = self._create_partitioned_registry(as_list, ixp_list_with_rs)
            
            # Create new emulator with the partitioned registry
            sub_emu = self._create_emulator_from_registry(new_registry)
            sub_emulators.append(sub_emu)
        
        return sub_emulators
    
    def _create_partitioned_registry(self, as_list: Set[int], ixp_list_with_rs: List) -> Registry:
        """!
        @brief Create a new registry containing only objects for specified ASs and IXs.
        
        @param as_list Set of AS numbers to include.
        @param ixp_list_with_rs List of (ix_id, needs_rs) tuples indicating which IXs to include
                                and whether each IX needs a Route Server on this machine.
        @return New Registry object.
        """
        # Get all objects from the original registry
        all_objects = self.__original_registry.getAll()
        
        # Convert AS list to strings for scope matching
        as_scopes = {str(asn) for asn in as_list}
        
        # Build IX list and Route Server requirements
        ixp_list = set()
        ixp_needs_rs = {}  # Dict mapping ix_id to needs_rs boolean
        for ix_id, needs_rs in ixp_list_with_rs:
            ixp_list.add(ix_id)
            ixp_needs_rs[ix_id] = needs_rs
        
        # Create a new registry
        new_registry = Registry()
        
        # Copy AS-related objects (nodes, networks)
        for (scope, type, name), obj in all_objects.items():
            if scope in as_scopes:
                # Types: 'net', 'hnode', 'rnode', 'brdnode'
                new_registry.register(scope, type, name, obj)
        
        # Copy IX-related objects (networks and optionally Route Servers)
        for (scope, type, name), obj in all_objects.items():
            if scope == 'ix':
                # Extract IX ID from name (format: 'ix100')
                if name.startswith('ix'):
                    try:
                        ix_id = int(name[2:])
                        if ix_id in ixp_list:
                            # Always include IX network
                            if type == 'net':
                                new_registry.register(scope, type, name, obj)
                            # Only include Route Server if needed on this machine
                            elif type == 'rs' and ixp_needs_rs.get(ix_id, False):
                                new_registry.register(scope, type, name, obj)
                    except ValueError:
                        pass
        
        return new_registry
    
    def _create_emulator_from_registry(self, registry: Registry) -> Emulator:
        """!
        @brief Create a new Emulator from a Registry.
        
        Simply create a new emulator and set its internal registry to the partitioned registry.
        
        @param registry Partitioned Registry object.
        @return New Emulator object.
        """
        # Create new emulator
        new_emu = Emulator()
        
        # Replace the emulator's registry with our partitioned registry
        # Access private __registry attribute using name mangling
        setattr(new_emu, '_Emulator__registry', registry)
        
        # Set emulator as rendered since we're copying from an already rendered emulator
        setattr(new_emu, '_Emulator__rendered', True)
        
        return new_emu

