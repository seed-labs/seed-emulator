from seedsim.mergers.DefaultDnssecMerger import DefaultDnssecMerger
from .DefaultBaseMerger import DefaultBaseMerger
from .DefaultEbgpMerger import DefaultEbgpMerger
from .DefaultRoutingMerger import DefaultRoutingMerger
from .DefaultIbgpMerger import DefaultIbgpMerger
from .DefaultOspfMerger import DefaultOspfMerger
from .DefaultMplsMerger import DefaultMplsMerger
from .DefaultDnssecMerger import DefaultDnssecMerger
from .DefaultCymruIpOriginServiceMerger import DefaultCymruIpOriginServiceMerger

DEFAULT_MERGERS = [
    DefaultBaseMerger(), DefaultEbgpMerger(), DefaultRoutingMerger(),
    DefaultIbgpMerger(), DefaultOspfMerger(), DefaultMplsMerger(),
    DefaultDnssecMerger(), DefaultCymruIpOriginServiceMerger()]