
import networkx as nx
import numpy as np
from enum import Enum
from dataclasses import dataclass, field
from typing import List, NamedTuple
import collections

#@dataclass
class ExpectNodeState(Enum):
    """
    we haven't parsed any nodes yet, and are waiting on a comment block with the introducing preamble
    """
    NotSeenAny = 0, # we are in a comment '#' block but haven't seen the 'NODES' label yet
    SeenNode = 1, # have encountered '# NODES' , but not the '===' not '---' dashed line yet
    SeenLine = 2, # we have seen the '==' line and are expecting the '--' dashed line
    Done = 3, 


    def advance_state(self, line: str) -> "ExpectNodeState":
        if self == ExpectNodeState.NotSeenAny:
            if line == NODE_HEADER[0]:
                return ExpectNodeState.SeenNode
            else:
                return self
        elif self == ExpectNodeState.SeenNode:
            if line == NODE_HEADER[1]:
                return ExpectNodeState.SeenLine
            else:
                return self
        elif self == ExpectNodeState.SeenLine:
            if line == NODE_HEADER[2]:
                return ExpectNodeState.Done
            else:
                return self
        return self

NODE_HEADER = ["# NODES\n","# =====\n", "# ------------------------------------\n"]

class ExpectEdgeState(Enum):
    """
     we haven't parsed any edges yet, and are waiting on a comment block with the introducing preamble    
    """
    NotSeenAny = 0, # we are in a comment '#' block but haven't seen the 'EDGES' label yet
    SeenEdge = 1, # have encountered '# EDGES' , but not the '===' nor '---' dashed line yet
    SeenLine = 2, # have encountered the '# ===' line
    Done = 3, # have encountered the '--' line

    def advance_state(self, line: str) -> "ExpectEdgeState":
        if self == ExpectEdgeState.NotSeenAny:
            if line == EDGE_HEADER[0]:
                return ExpectEdgeState.SeenEdge
            else:
                return self
        elif self == ExpectEdgeState.SeenEdge:
            if line == EDGE_HEADER[1]:
                return ExpectEdgeState.SeenLine
            else:
                return self
        elif self == ExpectEdgeState.SeenLine:
            if line == EDGE_HEADER[2]:
                return ExpectEdgeState.Done
            else:
                return self
        elif self == ExpectEdgeState.Done:
            raise AssertionError("state polled but expired")
            #return PARSING_EDGES( ParsingEdgesState().advance_state(line) )
        else:
            return self

EDGE_HEADER = ["# EDGES\n","# =====\n","# ---------------------------------------------------\n" ]

@dataclass
class ParsingNodesState:
    """
    we encountered the introducing NODES preamble, left the '#' comment block
    and are now parsing the nodes after the comment ended

    >>  Node	X	Y	Type (0 = WAN, 1 = MAN, 2 = LAN)  << 
    """
    node_count: int = 0
    graph: nx.Graph = nx.Graph()

    def advance_state(self, line: str):
        token = line.split()

        # the node list is continous without comments
        # so this must be the beginning of the EDGES preamble
        if token[0] == '#':
            return EXPECT_EDGES(graph=self.graph)
        else:
            self.graph.add_node(int(token[0]) , pos=np.array([float(token[1]),float(token[2])]), type=int(token[3]) )
            self.node_count+=1
            return PARSING_NODES( ParsingNodesState(self.node_count,self.graph) )

@dataclass
class EdgeCategory:
    current_id: int = 0

class WAN(EdgeCategory):
    # maybe count nr of edges here
    pass

class MAN(EdgeCategory):
    pass

class LAN(EdgeCategory):
    pass


@dataclass
class ParsingEdgesState:
    """
    we encountered the introducing EDGES preamble, 
    and now parse edges
    """
    graph: nx.Graph
    sub_state: EdgeCategory = WAN(0),
    wan_count: int = 0
    man_count: int = 0
    lan_count: int = 0
    edge_count: int = 0

    def advance_state(self,line):
        token = line.split()
        if len(token) <= 1: return self

        if token[0] == '#':
            if token[1] == 'WAN':
                self.sub_state = WAN(int(token[2]))
                self.wan_count += 1
            elif token[1] == 'MAN':
                self.sub_state = MAN(int(token[2]))
                self.man_count += 1
            elif token[1] == 'LAN':
                self.sub_state = LAN(int(token[2]))
                self.lan_count += 1
            return self
        else:
            link_attr = {}
            link_attr["delay"] = token[2]
            link_attr["bandwidth"] = token[3]
            link_attr["from_type"] = token[4]
            link_attr["to_type"] = token[5]
            link_attr["state"] = int( token[6] )
            net: str =""
            match self.sub_state:
                case MAN():
                    net = 'MAN'
                case WAN():
                    net = 'WAN'
                case LAN():
                    net = 'LAN'

            link_attr["affiliation"] = "{}{}".format(net,self.sub_state.current_id)

            self.graph.add_edge( int(token[0]), int(token[1]),**link_attr)
            return self


#@dataclass
class State:
        pass

@dataclass
class UNDEF:#(State):
        pass

@dataclass
class EXPECT_NODES:#(State):
    value: ExpectNodeState = ExpectNodeState.NotSeenAny

@dataclass
class PARSING_NODES:#(State):
    value: ParsingNodesState

@dataclass
class EXPECT_EDGES:#(State):
    graph: nx.Graph # carried over from predecessor Parsing_nodes state
    value: ExpectEdgeState = ExpectEdgeState.NotSeenAny

@dataclass
class PARSING_EDGES:#(State):
    value: ParsingEdgesState


def graphFromTiersTopoFile(topofile: str):
    
    """
    @brief reads Tiers topology file into networkx graph    
    """
    state = UNDEF()
    with  open(topofile, "r") as file:
        
        
        inside_comment = False
        
        for line in file:           
           token = line.split()

           match state:
              

               case  EXPECT_NODES(value):       
                   # TODO: move this branching into EXPECT_NODES::advance_state()                               
                   match value:
                       case ExpectNodeState.NotSeenAny|ExpectNodeState.SeenNode|ExpectNodeState.SeenLine:
                            state = EXPECT_NODES( value.advance_state(line) )                       
                       case ExpectNodeState.Done:
                            state = ParsingNodesState().advance_state(line)
                       case _:
                           pass

               case PARSING_NODES(val):
                   state = val.advance_state(line)

               case EXPECT_EDGES(g,val):
                   # TODO: move this branching into EXPECT_EDGES::advance_state()      
                   match val:
                       case ExpectEdgeState.NotSeenAny|ExpectEdgeState.SeenEdge|ExpectEdgeState.SeenLine:
                           state = EXPECT_EDGES(graph=g, value= val.advance_state(line) )                       
                       case ExpectEdgeState.Done:
                           state = PARSING_EDGES( ParsingEdgesState(graph=g).advance_state(line) )                           
                       case _ : 
                           pass
               case PARSING_EDGES(val):
                   state = PARSING_EDGES( val.advance_state(line) )
                   
               case UNDEF():
                   if token[0] == '#' and not inside_comment:
                       inside_comment = not inside_comment
                       vv = ExpectNodeState.NotSeenAny
                       
                       state = EXPECT_NODES(vv.advance_state(line))                       
                                        
    match state:
        case PARSING_EDGES(val)    :
            return val.graph
        case _:
            raise AssertionError("logic error")
        
