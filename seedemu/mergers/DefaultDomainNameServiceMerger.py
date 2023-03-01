from .ServiceMerger import ServiceMerger
from seedemu.services import DomainNameService, Zone
from re import match

class DefaultDomainNameServiceMerger(ServiceMerger):
    """!
    @brief default domain name service merger implementation.

    This is the default implementation which invokes the default service merger
    to handler merging installation targets, merge the zone tree, and combine
    masters.
    """

    def __mergeZone(self, a: Zone, b: Zone, dst: Zone, position: str = ''):
        names = set()

        self._log('merging zone: {}'.format('(root)' if position == '' else position))

        # merge regular records
        for r in a.getRecords():
            if r not in dst.getRecords(): dst.addRecord(r)
        for r in b.getRecords():
            # TODO: better checks?
            if r not in dst.getRecords(): dst.addRecord(r) 

        # merge gules
        for r in a.getGuleRecords(): dst.addGuleRecord(r)
        for r in b.getGuleRecords(): 
            # TODO: better checks?
            if r not in dst.getGuleRecords(): dst.addGuleRecord(r)

        # merge pending records (vnode)
        for (n, v) in a.getPendingRecords().items(): dst.resolveToVnode(n, v)
        for (n, v) in b.getPendingRecords().items():
            assert n not in dst.getPendingRecords(), 'found conflict: {} already points to a vnode'.format(n)
            dst.resolveToVnode(n, v)

        # look for all subzones
        for k in a.getSubZones().keys():
            self._log('{}.{} zone found in first emulator.'.format(k, position))
            names.add(k)
        for k in b.getSubZones().keys():
            self._log('{}.{} zone found in second emulator.'.format(k, position))
            names.add(k)
        
        # for all subzones,
        for name in names:
            # first test for conflicts.
            assert len([r for r in dst.getRecords() if match('{}\s+'.format(name), r)]) == 0, 'found conflict: {}.{} is both a record and a standalone zone.'.format(name, position)

            # then if no conflict, recursively merge them.
            self.__mergeZone(a.getSubZone(name), b.getSubZone(name), dst.getSubZone(name), '{}.{}'.format(name, position))

    def __mergeMaster(self, objectA: DomainNameService, objectB: DomainNameService, merged: DomainNameService):
        masterA = objectA.getMasterIp()
        masterB = objectB.getMasterIp()
        new_master = {key: value + masterB[key] for key, value in masterA.items()}
        merged.setAllMasterIp(new_master)

    def _createService(self) -> DomainNameService:
        return DomainNameService()

    def getName(self) -> str:
        return 'DefaultDomainNameServiceMerger'

    def getTargetType(self) -> str:
        return 'DomainNameServiceLayer'

    def doMerge(self, objectA: DomainNameService, objectB: DomainNameService) -> DomainNameService:
        """!
        @brief merge two DomainNameService.

        @param objectA first DomainNameService.
        @param objectB second DomainNameService.
        
        @returns merged DomainNameService.
        """

        merged: DomainNameService = super().doMerge(objectA, objectB)
        
        self.__mergeZone(objectA.getRootZone(), objectB.getRootZone(), merged.getRootZone())
        self.__mergeMaster(objectA, objectB, merged)
        return merged