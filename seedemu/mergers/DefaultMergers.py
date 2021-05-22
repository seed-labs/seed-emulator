from seedemu.mergers.DefaultDnssecMerger import DefaultDnssecMerger
from .DefaultBaseMerger import DefaultBaseMerger
from .DefaultEbgpMerger import DefaultEbgpMerger
from .DefaultRoutingMerger import DefaultRoutingMerger
from .DefaultIbgpMerger import DefaultIbgpMerger
from .DefaultOspfMerger import DefaultOspfMerger
from .DefaultMplsMerger import DefaultMplsMerger
from .DefaultDnssecMerger import DefaultDnssecMerger
from .DefaultCymruIpOriginServiceMerger import DefaultCymruIpOriginServiceMerger
from .DefaultWebServiceMerger import DefaultWebServiceMerger
from .DefaultDomainNameCachingServiceMerger import DefaultDomainNameCachingServiceMerger
from .DefaultReverseDomainNameServiceMerger import DefaultReverseDomainNameServiceMerger
from .DefaultDomainNameServiceMerger import DefaultDomainNameServiceMerger
from .DefaultBgpLookingGlassServiceMerger import DefaultBgpLookingGlassServiceMerger

DEFAULT_MERGERS = [
    DefaultBaseMerger(), DefaultEbgpMerger(), DefaultRoutingMerger(),
    DefaultIbgpMerger(), DefaultOspfMerger(), DefaultMplsMerger(),
    DefaultDnssecMerger(), DefaultCymruIpOriginServiceMerger(),
    DefaultWebServiceMerger(), DefaultDomainNameCachingServiceMerger(),
    DefaultReverseDomainNameServiceMerger(), DefaultDomainNameServiceMerger(),
    DefaultBgpLookingGlassServiceMerger()
]