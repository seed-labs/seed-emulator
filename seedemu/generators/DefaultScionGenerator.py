from sys import stderr

from .providers import DataProvider
from . .core import Emulator, AutonomousSystem, InternetExchange, ScionAutonomousSystem
from . .layers import Base, Routing,  Ospf, Scion, ScionBase,ScionRouting, ScionIsd
from seedemu.layers.Scion import LinkType 
from typing import Type

class BorderRouterAllocation:
    """
    @brief a strategy object that decides how border routers map to AS interfaces
    """
    def getRouterForIX(self, ix_alias: int):
        pass
    def getRouterForXC(self, if_ids, peer_asn: int ):
        pass


class SeparateForEachIFAlone(BorderRouterAllocation):

    def __init__(self, _as: AutonomousSystem ):
        self._my_as = _as        

    def getRouterForIX(self, ix_alias : int ):
        br_name = 'router{}'.format(ix_alias)                
        return self._my_as.createRouter(br_name)

    def getRouterForXC(self, ifids, peer_asn: int ):
        # each IFID will get its own dedicated border router
        br_name = 'brd{}'.format(ifids[0])
        peer_br_name = 'brd{}'.format(ifids[1])                    

        if br_name not in self._my_as.getRouters():
            return self._my_as.createRouter(br_name ),peer_br_name
            
        else:
            return self._my_as.getRouter(br_name), peer_br_name
        


class CommonRouterForAllIF(BorderRouterAllocation):
    def __init__(self, _as: AutonomousSystem):
        self._my_as = _as
        self._my_as.createRouter('brd00')
    def getRouterForIX(self, ix_alias: int ):
        return self._my_as.getRouter('brd00')
    
    def getRouterForXC(self, if_ids, peer_asn: int ):
        return self._my_as.getRouter('br00'), 'brd00'

class DefaultScionGenerator:
    """!
    @brief Default topology generator implementation.

    The topology generator providers a way to generate emulation scenarios from
    real-world topology.

    WIP.
    TODO: check what happens if a DataProvider has both, XC cross connects and IX exchange points
          this is yet untested
    """

    __provider: DataProvider
    

    def __init__(self, provider: DataProvider , alloc: Type[BorderRouterAllocation] = SeparateForEachIFAlone ):
        """!
        @brief create a new topology generator.

        @param provider data provider.
        """
        self.__provider = provider
        self._alloc_type = alloc
        pass

    def __log(self, message: str) -> None:
        """!
        @brief Log to stderr.

        @param message message.
        """
        print('== DefaultGenerator: {}'.format(message), file = stderr)
    
    def _ASNforIXp(self, ix_id: int ) -> int:
        """
        @brief return an ASN for the IXp with id 'ix_id'
        """
        # ASNs of 'real' ASes and those of IXps must not collide , right ?!
        return len(self.__provider.getASes()) +3 +ix_id

    def __generate(self, asn: int, emulator: Emulator, depth: int):
        """!
        @brief recursively (depth-first) generate topology.

        @param asn asn to start on.
        @param emulator emulator to commit changes on.
        @param depth levels to traverse.
        """
        if depth <= 0: return

        self.__log('generating AS{}...'.format(asn))

        base: ScionBase = emulator.getLayer('Base')
        scion: Scion = emulator.getLayer('Scion')
        scion_isd: ScionIsd = emulator.getLayer('ScionIsd')
        
        routing: ScionRouting = emulator.getLayer('Routing')

        if asn in base.getAsns():
            self.__log('AS{} already done, skipping...'.format(asn))
            return
        
        self.__log('getting list of IXes joined by AS{}...'.format(asn))
        ixes_joined_by_asn = self.__provider.getInternetExchanges(asn)

        self.__log('getting list of prefixes announced by AS{}...'.format(asn))
        prefixes_of_asn = self.__provider.getPrefixes(asn)

        self.__log('getting list of peers of AS{}...'.format(asn))
        peers = self.__provider.getPeers(asn)

        self.__log('getting list of cross connects of AS{}...'.format(asn))
        cross_connects = self.__provider.getSCIONCrossConnects(asn)
                
        current_as = base.createAutonomousSystem(asn)
        scion_isd.addIsdAs(1, asn, is_core= self.__provider.isCore(asn))
        
        if not self.__provider.isCore(asn):
            issu =  self.__provider.getCertIssuer(asn)
            assert issu != None
            scion_isd.setCertIssuer((1, asn), issuer=issu)

 
        net_count = 0
        nr_prefixes = len(prefixes_of_asn)
        nr_joined_ixes = len(ixes_joined_by_asn)


        self.__log('looking for details of {} IXes joined by AS{}...'.format(len(ixes_joined_by_asn), asn))

        # simplest case
        if nr_prefixes == 1:
            # create one border router for each joined IX and have each join the same net (for the single existing prefix)
            # mot often the prefix will be 'auto' anyway, so we will end up here


            self.__log('creating {} networks for AS{}...'.format(nr_prefixes, asn))
            
            prefix = prefixes_of_asn[0] # there is only one
            netname = 'net{}'.format(net_count)

            self.__log('creating {} with prefix {} for AS{}...'.format(netname, prefix, asn))
            
            net = current_as.createNetwork(netname, prefix)
            attr = self.__provider.getAttributes(asn)
            if 'mtu' in attr:
                net.setMtu( attr['mtu'] )
            
            current_as.createControlService('cs1').joinNetwork(netname)      
            router_alloc = self._alloc_type(current_as)      

            for ix in ixes_joined_by_asn:
                ix_alias = self._ASNforIXp(ix)
                if ix_alias not in base.getInternetExchangeIds():              
                             
                    # only create ix if it didnt already exist !!
                    #if ix not in base.getInternetExchangeIds():
                    self.__log('creating new IX, IX{}; getting prefix...'.format(ix_alias))
                    base.createInternetExchange( ix_alias, prefix = self.__provider.getInternetExchangePrefix(ix) , create_rs= False)

                self.__log('getting members of IX{}...'.format(ix_alias))
                members = self.__provider.getInternetExchangeMembers(ix)

                self.__log('joining IX{} with AS{}...'.format(ix_alias, asn))
                ip_of_asn_in_ix = members[asn]
                       
                router = router_alloc.getRouterForIX(ix_alias)
                #router.joinNetwork(netname) 
                router.updateNetwork(netname)
                router.joinNetwork('ix{}'.format(ix_alias), ip_of_asn_in_ix)
            
                self.__log('creating {} other ASes in IX{}...'.format(len(members.keys()), ix_alias))
                for member in members.keys():
                    self.__generate(member, emulator, depth - 1)
                    if member in peers.keys():
                        # FIXME: right = peer is customer, left = peer is provider
                        rel = peers[member]
                        self.__log('peering AS{} with AS{} in IX{} using relationship {}...'.format(member, asn, ix_alias, rel))
                                       
                        scion.addIxLink(ix_alias, (1, member), (1, asn),rel)         

            for (peerasn,v) in cross_connects.items():
                for vv in v:
                    addr =vv[0]
                    linktype = vv[1]
                    ifids = vv[2]                                        

                    router,peer_br_name = router_alloc.getRouterForXC(vv[2],peerasn)
                    router.updatesNetwork(netname)
                    router.crossConnect(peerasn, peer_br_name, addr )

                        
                    # do not add transit links in both directions
                    if linktype == LinkType.Transit:
                        if not ((1,peerasn),(1,asn),linktype ) in scion.getXcLinks():
                            scion.addXcLink((1,asn),(1,peerasn), linktype )
                    else:
                        scion.addXcLink((1,asn),(1,peerasn), linktype )

                self.__generate(peerasn, emulator, depth - 1)

        elif nr_prefixes > nr_joined_ixes:
            # here we have to decice which brnode shall join which net/prefix ..
            # Or create subnets of the prefix and have each brnode join one of them ?! Help
            raise NotImplementedError("this case is unimplemented")
        
        elif nr_prefixes == nr_joined_ixes:
            # maybe map each brnode to its own prefix ?!
            raise NotImplementedError("cant handle this case yet")
      


    def generate(self, startAsn: int, depth: int) -> Emulator:
        """!
        @brief generate a new emulation.

        @param startAsn ASN to start on.
        @param depth levels to traverse.

        @returns generated emulator.
        """
        sim = Emulator()
        ospf = Ospf()        
        base = ScionBase()
        routing = ScionRouting()
        scion_isd = ScionIsd()
        scion = Scion()
        
        sim.addLayer(base)
        sim.addLayer(routing)
        sim.addLayer(scion_isd)
        sim.addLayer(scion)     
        sim.addLayer(ospf)

        
        base.createIsolationDomain(1)   

        self.__generate(startAsn, sim, depth) # TODO: compute an upper bound for the depth, it can default to

        return sim