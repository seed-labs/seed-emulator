from .ServiceMerger import ServiceMerger
from seedsim.services import DomainNameService
from re import match

class DefaultDomainNameServiceMerger(ServiceMerger):

    def _createService(self) -> DomainNameService:
        return DomainNameService()

    def getName(self) -> str:
        return 'DefaultDomainNameServiceMerger'

    def getTargetType(self) -> str:
        return 'DomainNameServiceLayer'

    def doMerge(self, objectA: DomainNameService, objectB: DomainNameService) -> DomainNameService:
        merged: DomainNameService = super().doMerge(objectA, objectB)
        servers_A = objectA.getPendingTargets()
        servers_B = objectB.getPendingTargets()

        zones_A = []
        zones_B = []
        for i in servers_A:
            zones = servers_A[i].getZones()
            zones_A += [x for x in zones]

        for j in servers_B:
            zones = servers_B[j].getZones()
            zones_B += [x for x in zones]

        for zone in zones_A:
            zone_name = zone.getName()
            for rec in zone.getRecords():
                m = match('(\w+) A ', rec)
                if m:
                    sub_domain = m.group(1)
                    full_domain = sub_domain + "." + zone_name
                    if len(objectB.getZoneServerNames(full_domain)) > 0:
                        msg = 'There is a conflict in DomainNameService layer with zone {} during the merge process. Do you want to continue?'.format(full_domain)
                        choice = input("%s (y/N) " % msg).lower() == 'y'
                        if not choice:
                            exit()

        for zone in zones_B:
            zone_name = zone.getName()
            for rec in zone.getRecords():
                m = match('(\w+) A ', rec)
                if m:
                    sub_domain = m.group(1)
                    full_domain = sub_domain + "." + zone_name
                    if len(objectA.getZoneServerNames(full_domain)) > 0:
                        msg = 'There is a conflict in DomainNameService layer with zone {} during the merge process. Do you want to continue?'.format(full_domain)
                        choice = input("%s (y/N) " % msg).lower() == 'y'
                        if not choice:
                            exit()

        return merged