import xml.etree.ElementTree as ET
import networkx as nx
from collections import defaultdict
from seedemu.layers.Scion import LinkType

"""
CAIDA format
    <-- ASes Nodes -->
    <node id="2914" id.type="int">
        <property name="type" type="string">core</property>
        <property name="latency_coef" type="float">0.3605545717145815</property>
        <property name="bandwidth_coef" type="float">0.1392311023344719</property>
        <property name="AS_level_diversity_coef" type="float">0.17126575166007207</property>
        <property name="link_level_diversity_coef" type="float">0.2832171229633935</property>
    </node> 
    .....
    <-- Edges  - the geo coordinates correspond to an Internet exhange point -->
    <link>
        <from type="int">2914</from>
        <to type="int">6762</to>
        <property name="rel" type="string">core</property>
        <property name="latitude" type="float">48.85341</property>
        <property name="longitude" type="float">2.3488</property>
        <property name="capacity" type="int">40</property>    
    </link>
"""


def graphFromXmlTopoFileRaw( topofile: str ):
    """
    @brief reads a CAIDA .xml inter domain topofile with ASes an their links
    Raw means it just reads whats in the file, not more.
    This can be used if you have a preprocessed .xml file,
    were the IXP-Id property of links/edges need not be computed , but is already present in the file.
    """
    G = nx.MultiGraph()
    tree = ET.parse(topofile)
    root = tree.getroot()

    for node in root.iter('node'):
       node_attr = {'id':  node.attrib['id'] }
       for child in node:
          if child.tag == "property":
               node_attr[ child.attrib['name'] ] = child.text
          
       G.add_node( int(node.attrib['id']),  **node_attr)

    for link in root.findall('link'):
      link_attr = {}
      for child in link:
         if child.tag == "property":
               link_attr[ child.attrib['name'] ] = child.text

      G.add_edge( int(link.find('from').text) , int( link.find('to').text ), **link_attr  )


    return G

def graphFromXmlTopoFile(topofile: str): 
    """
    @brief reads a CAIDA .xml inter domain topofile with ASes an their links
    IDs of InternetExhange points are implicitly contained in the data as their geo coordinates (lat,long).
    ASes will become nodes, and edges between them will have the Id of the internet exchange point as an edge attribute
    that realises this connection.
    """
    G = nx.MultiGraph()
    tree = ET.parse(topofile)
    root = tree.getroot()

    # read in all ASes ( IDs are real ASNs not aliases for now )
    for node in root.iter('node'):
       node_attr = {'id':  node.attrib['id'] }
       for child in node:
          if child.tag == "property":
               node_attr[ child.attrib['name'] ] = child.text
          
       G.add_node( int(node.attrib['id']),  **node_attr)


    ASenum = {} # maps real AS number to its alias
    ASif = {} # maps AS alias to number of its interfaces
    ascnt =0 # number of ASes (used to generate AS aliases by counting them )

    locs_of_ixps : dict[(float,float),int] ={} # maps location of an IXP to its ID
    ixp_locs ={} # the inverse of locs_of_ixps
    ixp_presences = defaultdict(set) # maps ixpId to a list of AS that have a presence at this IXp (real AS numbers, no aliases)
    AStoIxps = defaultdict(set) # for an AS the list of IXPs it has joined (keys are real AS numbers no aliases)


    ixp_count =0 # number of ixps
    for link in root.findall('link'):
      lat:float =0.0
      long:float = 0.0
      link_attr = {}
      for child in link:
         if child.tag == "property":
               if child.attrib['name'] == "latitude":
                   lat = float(child.text)
               if child.attrib['name'] == "longitude":
                   long = float(child.text)
                   
               link_attr[ child.attrib['name'] ] = child.text
      fromAS = int(link.find('from').text) 
      toAS = int( link.find('to').text )
      if fromAS not in ASenum:
         ASif[ ascnt] = 0

         ASenum[fromAS] = ascnt
         ascnt+=1
      else:
        ASif[ ASenum[fromAS] ]+=1

      if toAS  not in   ASenum:
         ASif[ ascnt ] = 0
         ASenum[toAS] = ascnt
         ascnt+=1
      else:
         ASif[ ASenum[toAS] ] +=1

      if (lat,long) in locs_of_ixps:
         ixp_presences[locs_of_ixps[(lat,long)]].add( fromAS   )
         ixp_presences[locs_of_ixps[(lat,long)]].add( toAS   )
      else:
         locs_of_ixps[(lat,long)]=ixp_count
         ixp_locs[ixp_count] = (lat,long)        
         ixp_count+=1
        
         ixp_presences[locs_of_ixps[(lat,long)]].add( fromAS   )
         ixp_presences[locs_of_ixps[(lat,long)]].add( toAS   )

      AStoIxps[fromAS].add(locs_of_ixps[(lat,long)])
      AStoIxps[toAS].add(locs_of_ixps[(lat,long)])
      link_attr['ixp_id'] = locs_of_ixps[(lat,long)]
      link_attr['from_as_if_id'] = ASif[ ASenum[fromAS] ]
      link_attr['to_as_if_id'] = ASif[ ASenum[toAS] ]
   
      G.add_edge( fromAS, toAS, **link_attr )  
               
    assert ascnt == len(G.nodes())    
    attrib = dict()
    
    for (k,v) in AStoIxps.items(): # k is an ASN , v a set of Ixps 'k' has joined
        #G.set_node_attribute ( a, ixps= AStoIxps[a] )
        attrib[k]= {'ixp_presences':v }
    nx.set_node_attributes(G,attrib)
    
    return G


def graphFromXmlTopoFileAliased(topofile: str): 
    """
    @brief reads a CAIDA .xml inter domain topofile with ASes an their links
    IDs of InternetExhange points are implicitly contained in the data as their geo coordinates (lat,long).
    ASes will become nodes, and edges between them will have the Id of the internet exchange point as an edge attribute
    that realises this connection.
    ASes will be enumerated and refered to by counting aliases instead of real ASNs in the returned graph.
    """
    G = nx.MultiGraph()
    tree = ET.parse(topofile)
    root = tree.getroot()

    ASenum = {} # maps real AS number to its alias
    ASif = {} # maps AS alias to number of its interfaces
    ascnt = 2 # number of ASes (used to generate AS aliases by counting them )
    # '0' is an invalid AS number (wildcard AS , meaning "just any AS")

    locs_of_ixps : dict[(float,float),int] ={} # maps location of an IXP to its ID
    ixp_locs ={} # the inverse of locs_of_ixps
    ixp_presences = defaultdict(set) # maps ixpId to a list of AS that have a presence at this IXp (alias AS numbers, no real ASNs)
    AStoIxps = defaultdict(set) # for an AS the list of IXPs it has joined (keys are alias AS numbers no real ASNs)

    # read in all ASes ( IDs are AS aliases not real ASNs )
    for node in root.iter('node'):
       node_attr = {'id':  node.attrib['id'] }
       for child in node:
          if child.tag == "property":
               node_attr[ child.attrib['name'] ] = child.text
       asn = int(node.attrib['id'])
       ASenum[asn] = ascnt 
       G.add_node( ascnt,  **node_attr)
       ascnt+=1  

    assert len(ASenum) == ascnt - 2

 
    link_count = 0

    ixp_count =0 # number of ixps
    for link in root.findall('link'):
      link_count += 1
      lat: float =0.0
      long:float = 0.0

      fromAS = int(link.find('from').text) 
      toAS = int( link.find('to').text )
      fromAlias = ASenum[fromAS]
      toAlias = ASenum[toAS]

      link_attr = {}
      for child in link:
         if child.tag == "property":
               if child.attrib['name'] == "latitude":
                   lat = float(child.text)
               if child.attrib['name'] == "longitude":
                   long = float(child.text)
               if child.attrib['name'] == "rel":
                   link_attr['link_type'] = { } 
                   if child.text == 'core':                  
                     link_attr['link_type'][fromAS] = LinkType.Core
                     link_attr['link_type'][toAS] = LinkType.Core
                   elif child.text == 'peer':
                     link_attr['link_type'][fromAS] = LinkType.Peer
                     link_attr['link_type'][toAS] = LinkType.Peer
                   elif child.text == 'customer':
                     link_attr['link_type'][fromAS] = LinkType.Transit
                     link_attr['link_type'][toAS] = LinkType.Transit
                      
                   
               link_attr[ child.attrib['name'] ] = child.text

      if fromAlias not in ASif:
         ASif[ fromAlias] = 0         
         
      else:
        ASif[ fromAlias ]+=1

      if toAlias  not in   ASif:
         ASif[ toAlias ] = 0                  
      else:
         ASif[ toAlias ] +=1

      if (lat,long) in locs_of_ixps:
         ixp_presences[locs_of_ixps[(lat,long)]].add( fromAlias   )
         ixp_presences[locs_of_ixps[(lat,long)]].add( toAlias   )
      else:
         locs_of_ixps[(lat,long)]=ixp_count
         ixp_locs[ixp_count] = (lat,long)        
         ixp_count+=1
        
         ixp_presences[locs_of_ixps[(lat,long)]].add( toAlias   )
         ixp_presences[locs_of_ixps[(lat,long)]].add( fromAlias   )

      AStoIxps[ fromAlias].add(locs_of_ixps[(lat,long)])
      AStoIxps[toAlias].add(locs_of_ixps[(lat,long)])
      link_attr['ixp_id'] = locs_of_ixps[(lat,long)]
      link_attr['if_ids'] = {}
      link_attr['if_ids'][fromAlias] =ASif[fromAlias]
      link_attr['if_ids'][toAlias] =ASif[toAlias]

      link_attr['from_as_if_id'] = ASif[ fromAlias ]
      link_attr['to_as_if_id'] = ASif[ toAlias ]
   
      assert toAlias in ASenum.values() and fromAlias in ASenum.values()
      G.add_edge( fromAlias, toAlias, **link_attr )    
               
    nodecnt = len(G.nodes)
    print(G.nodes)
    print(ASenum)
    assert ascnt -2 == nodecnt
    assert ixp_count > 0
    edgecnt = len( list(G.edges))
    assert link_count == edgecnt
   
    attrib = dict()

    for (k,v) in AStoIxps.items(): # k is an ASN , v a set of Ixps 'k' has joined
        #G.set_node_attribute ( a, ixps= AStoIxps[a] )
        attrib[k]= {'ixp_presences':v }
    nx.set_node_attributes(G,attrib)
    
    return G