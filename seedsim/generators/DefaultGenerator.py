from sys import stderr

from .providers import DataProvider
from . .core import Simulator, AutonomousSystem, InternetExchange
from . .layers import Base, Routing, Ebgp, Ibgp, Ospf

class DefaultGenerator:

    __provider: DataProvider

    def __init__(self, provider: DataProvider) -> None:
        self.__provider = provider
        pass

    def __log(self, message: str) -> None:
        """!
        @brief Log to stderr.
        """
        print('== DefaultGenerator: {}'.format(message), file=stderr)

    def __generate(self, asn: int, simulator: Simulator, depth: int):
        if depth <= 0: return

        self.__log('generating AS{}...'.format(asn))

        base: Base = simulator.getLayer('Base')
        bgp: Ebgp = simulator.getLayer('Ebgp')
        routing: Routing = simulator.getLayer('Routing')

        if asn in base.getAsns():
            self.__log('AS{} already done, skipping...'.format(asn))
            return
        
        self.__log('getting list of IXes joined by AS{}...'.format(asn))
        ixes = self.__provider.getInternetExchanges()

        self.__log('getting list of prefixes announced by AS{}...'.format(asn))
        prefixes = self.__provider.getPrefixes()

        self.__log('getting list of peers of AS{}...'.format(asn))
        peers = self.__provider.getPeers()

        current_as = base.createAutonomousSystem(asn)

        router = current_as.createRouter('router0')

        net_count = 0

        self.__log('creating {} networks for AS{}...'.format(len(prefixes), asn))
        for prefix in prefixes:
            netname = 'net{}'.format(net_count)

            self.__log('creating {} with prefix {} for AS{}...'.format(netname, prefix, asn))

            current_as.createNetwork(netname, prefix)
            router.joinNetwork(netname)
            routing.addDirect(asn, netname)

            net_count += 1

        self.__log('looking for details of {} IXes joined by AS{}...'.format(len(ixes), asn))
        for ix in ixes:
            if ix in base.getInternetExchangeIds():
                self.__log('IX{} already created, skipping...')
                continue

            self.__log('creating new IX, IX{}; getting prefix...'.format(ix))
            base.createInternetExchange(ix, prefix = self.__provider.getInternetExchangePrefix(ix))

            self.__log('getting members of IX{}...'.format(ix))
            members = self.__provider.getInternetExchangeMembers(ix)

            self.__log('joining IX{} with AS{}...'.format(ix, asn))
            router.joinNetwork('ix{}'.format(ix), members[asn])
            
            self.__log('creating {} other ASes in IX{}...'.format(len(members.keys()), ix))
            for member in members.keys():
                self.__generate(member, simulator, depth - 1)
                if member in peers.keys():
                    rel = peers[member]
                    self.__log('peering AS{} with AS{} in IX{} using relationship {}...'.format(member, asn, ix, rel))
                    bgp.addPrivatePeering(ix, member, asn, rel)


    def generate(self, startAsn: int, depth: int) -> Simulator:
        sim = Simulator()
        sim.addLayer(Base())
        sim.addLayer(Routing())
        sim.addLayer(Ebgp())
        sim.addLayer(Ibgp())
        sim.addLayer(Ospf())

        self.__generate(startAsn, sim, depth)

        return sim