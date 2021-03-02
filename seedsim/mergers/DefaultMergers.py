from .DefaultBaseMerger import DefaultBaseMerger
from .DefaultEbgpMerger import DefaultEbgpMerger
from .DefaultRoutingMerger import DefaultRoutingMerger

DEFAULT_MERGERS = [DefaultBaseMerger(), DefaultEbgpMerger(), DefaultRoutingMerger()]