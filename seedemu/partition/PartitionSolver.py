from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import pulp
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary
import math


class PartitionSolver:
    """!
    @brief Solver for multi-machine partition problem.
    
    This class solves the problem of partitioning ASs and IXPs across multiple machines
    while minimizing IX partitions and respecting machine capacity constraints.
    """
    
    # Default constants
    DEFAULT_TIME_LIMIT_SECONDS = 180  # Default solver time limit
    
    def __init__(self, timeLimit: int = DEFAULT_TIME_LIMIT_SECONDS):
        """!
        @brief Initialize the partition solver.
        
        @param timeLimit Time limit for solver in seconds. Default is 180.
        """
        self.__time_limit = timeLimit
    
    def solve(self, 
              topo_data: Dict,
              machine_capacities: List[int],
              solver_name: str = 'pulp') -> Optional[Dict]:
        """!
        @brief Solve the partition problem.
        
        @param topo_data Topology data dictionary containing:
            - asns: List[Tuple[int, int]] - AS list with resources [(asn, resource), ...]
            - ixps: List[int] - IXP ID list
            - ix_as_connections: Dict[int, List[int]] - IX-AS connections
        @param machine_capacities List of machine capacities.
        @param solver_name Solver to use ('pulp', 'copt', 'cbc', 'glpk'). Default is 'pulp'.
        @return Dictionary containing partition result, or None if solving failed.
                Format: {machine_id: {'as_list': [...], 'ixp_list': [...]}}
        """
        # Extract data
        asns_data = topo_data.get('asns', [])
        ixps = topo_data.get('ixps', [])
        ix_as_connections = topo_data.get('ix_as_connections', {})
        
        if not asns_data or not machine_capacities:
            return None
        
        # Build model inputs
        K, n, m, w, M, S, A, asn_index_to_id, ix_index_to_id = self._build_model_inputs(
            asns_data, ixps, ix_as_connections, machine_capacities
        )
        
        # Solve the problem
        x, y, status = self._solve_optimization(K, n, m, w, M, S, A, solver_name)
        
        if status != pulp.LpStatusOptimal and status != pulp.LpStatusNotSolved:
            return None
        
        # Generate result
        result = self._generate_result(
            K, n, m, x, y, asn_index_to_id, ix_index_to_id, S
        )
        
        return result
    
    def _build_model_inputs(self,
                           asns_data: List[Tuple[int, int]],
                           ixps: List[int],
                           ix_as_connections: Dict[int, List[int]],
                           machine_capacities: List[int]):
        """!
        @brief Build model inputs from topology data.
        
        @param asns_data List of (asn, resource) tuples.
        @param ixps List of IXP IDs.
        @param ix_as_connections Dictionary mapping IX ID to list of connected AS IDs.
        @param machine_capacities List of machine capacities.
        @return Tuple of (K, n, m, w, M, S, A, asn_index_to_id, ix_index_to_id)
        """
        # Extract ASNs and resources
        all_asns = [asn for asn, _ in asns_data]
        w = [resource for _, resource in asns_data]
        
        n = len(all_asns)
        m = len(ixps)
        K = len(machine_capacities)
        
        # Create index mappings
        asn_id_to_index = {asn_id: i for i, asn_id in enumerate(all_asns)}
        ix_id_to_index = {ix_id: i for i, ix_id in enumerate(sorted(ixps))}
        
        asn_index_to_id = {i: asn_id for asn_id, i in asn_id_to_index.items()}
        ix_index_to_id = {i: ix_id for ix_id, i in ix_id_to_index.items()}
        
        # Build AS-IX connection sets S[i] = {AS indices connected to IX i}
        S = [set() for _ in range(m)]
        for ix_id, connected_asns in ix_as_connections.items():
            if ix_id in ix_id_to_index:
                ix_idx = ix_id_to_index[ix_id]
                for asn_id in connected_asns:
                    if asn_id in asn_id_to_index:
                        as_idx = asn_id_to_index[asn_id]
                        S[ix_idx].add(as_idx)
        
        # Machine capacities
        M = machine_capacities.copy()
        
        # Big-M constant
        A = n * 2
        
        return K, n, m, w, M, S, A, asn_index_to_id, ix_index_to_id
    
    def _solve_optimization(self,
                           K: int, n: int, m: int,
                           w: List[int], M: List[int], S: List[set],
                           A: int, solver_name: str):
        """!
        @brief Solve the optimization problem.
        
        @return Tuple of (x, y, status) where x and y are decision variables, status is solver status.
        """
        # Create model
        model = LpProblem(name="ix_partition", sense=LpMinimize)
        
        # Decision variables
        # x[j][k] = 1 if AS j is assigned to machine k
        x = [[LpVariable(name=f"x_{j}_{k}", cat=LpBinary) for k in range(K)] for j in range(n)]
        # y[i][k] = 1 if IX i has at least one AS on machine k
        y = [[LpVariable(name=f"y_{i}_{k}", cat=LpBinary) for k in range(K)] for i in range(m)]
        
        # Objective: minimize total IX partitions
        model += lpSum(y[i][k] for i in range(m) for k in range(K)), "Total_IX_Partitions"
        
        # Constraints
        
        # Constraint 1: Capacity constraints
        for k in range(K):
            model += lpSum(w[j] * x[j][k] for j in range(n)) <= M[k], f"capacity_k{k}"
        
        # Constraint 2: Each AS must be assigned to exactly one machine
        for j in range(n):
            model += lpSum(x[j][k] for k in range(K)) == 1, f"assign_j{j}"
        
        # Constraints 3 & 4: Link y and x variables
        for i in range(m):
            S_i = S[i]
            if not S_i:
                continue
            
            for k in range(K):
                sum_x_jk = lpSum(x[j][k] for j in S_i)
                # y[i][k] = 1 if any AS in S_i is on machine k
                model += A * y[i][k] >= sum_x_jk, f"y_link_A_{i}_{k}"
                model += y[i][k] <= sum_x_jk, f"y_link_B_{i}_{k}"
        
        # Solve
        solver = self._get_solver(solver_name)
        if solver:
            model.solve(solver)
        else:
            model.solve()
        
        status = model.status
        return x, y, status
    
    def _get_solver(self, solver_name: str):
        """!
        @brief Get solver instance.
        
        @param solver_name Solver name ('pulp', 'copt', 'cbc', 'glpk').
        @return Solver instance or None.
        """
        solver_name_lower = solver_name.lower()
        
        # Try COPT
        if solver_name_lower in ['copt', 'pulp']:
            try:
                solver = pulp.COPT_CMD(msg=False, timeLimit=self.__time_limit)
                if solver.available():
                    return solver
            except:
                pass
        
        # Try CBC
        if solver_name_lower in ['cbc', 'pulp']:
            try:
                solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=self.__time_limit)
                if solver.available():
                    return solver
            except:
                pass
        
        # Try GLPK
        if solver_name_lower == 'glpk':
            try:
                solver = pulp.GLPK_CMD(msg=False, options=[f"--tmlim {self.__time_limit}"])
                if solver.available():
                    return solver
            except:
                pass
        
        return None
    
    def _generate_result(self,
                        K: int, n: int, m: int,
                        x: List[List[LpVariable]],
                        y: List[List[LpVariable]],
                        asn_index_to_id: Dict[int, int],
                        ix_index_to_id: Dict[int, int],
                        S: List[set]) -> Dict:
        """!
        @brief Generate partition result from solution.
        
        @return Dictionary with format: {machine_id: {'as_list': [...], 'ixp_list': [...]}}
        """
        result = {}
        
        # Collect AS assignments
        for k in range(K):
            assigned_as_indices = [
                j for j in range(n) 
                if x[j][k].value() is not None and x[j][k].value() > 0.5
            ]
            assigned_as_ids = sorted([asn_index_to_id[j] for j in assigned_as_indices])
            
            if assigned_as_ids:
                result[k] = {
                    'as_list': assigned_as_ids,
                    'ixp_list': []
                }
        
        # Collect IXP assignments and determine Router Server placement
        # Strategy: For each IX, assign Router Server to exactly one machine (the first one)
        for i in range(m):
            ix_id = ix_index_to_id[i]
            S_i = S[i]
            
            if not S_i:
                continue
            
            # Find which machines have ASs connected to this IX
            machines_with_as = set()
            for j in S_i:
                for k in range(K):
                    if x[j][k].value() is not None and x[j][k].value() > 0.5:
                        machines_with_as.add(k)
                        break
            
            if not machines_with_as:
                continue
            
            # Select the first machine (lowest machine ID) to host Router Server for this IX
            # This ensures each IX has exactly one Router Server across all machines
            rs_machine = min(machines_with_as)
            
            # Add IX to each machine that has at least one connected AS
            for k in sorted(machines_with_as):
                if k not in result:
                    result[k] = {'as_list': [], 'ixp_list': []}
                
                # Router Server is needed only on the selected machine
                needs_rs = (k == rs_machine)
                
                result[k]['ixp_list'].append((ix_id, needs_rs))
        
        # Sort IXP lists by IX ID
        for k in result:
            result[k]['ixp_list'].sort(key=lambda x: x[0])
        
        return result

