from .DefaultBaseMerger import DefaultBaseMerger
from .DefaultEbgpMerger import DefaultEbgpMerger
from .DefaultRoutingMerger import DefaultRoutingMerger
from .DefaultIbgpMerger import DefaultIbgpMerger

DEFAULT_MERGERS = [
    DefaultBaseMerger(), DefaultEbgpMerger(), DefaultRoutingMerger(),
    DefaultIbgpMerger()]