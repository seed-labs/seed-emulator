import networkx as nx
from collections import defaultdict
import json

def FromSCIONTopoJSON( file_name ):
    """
    @brief reads a SCION topology.json file into a networkx MultiGraph 
        with ASes as nodes 
    """

    alias = 2
    AS2alias ={}# maps as string to alias_id

    G = nx.MultiGraph()

    with open( file_name , 'r') as fcc_file:
        x = json.load( fcc_file )

        for _as in x["ASes"]:

            dic = x["ASes"][_as]
            
            AS2alias[_as] = alias
            G.add_node(alias,ia=_as, **dic )
            alias += 1
            
        for _link in x["links"]:
            _from = _link["a"]
            _to = _link["b"]

            _froms = _from.split('#')
            _tos  = _to.split('#')

            from_alias =  AS2alias[ _froms[0] ]
            to_alias = AS2alias[ _tos[0] ]

            linkcpy = _link.copy()
            linkcpy["linkAtoB"] = '{}#{}#{}'.format(from_alias,linkcpy['linkAtoB'],to_alias)
            del linkcpy["a"]
            del linkcpy["b"]

            asifids = {}  #  maps ASNs to their IFID for this link
            asifids[from_alias] = int(_froms[1])
            asifids[to_alias] = int(_tos[1])
            
            G.add_edge( from_alias,
                        to_alias,
                        from_as_if = int(_froms[1]) ,
                        to_as_if  = int(_tos[1]) ,
                        ifids = asifids,
                        **linkcpy )
            
    return G