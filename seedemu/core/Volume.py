from .Registry import Registrable
from yaml import *
from typing import Dict, Tuple, List, Set

# use collections defaultdict ?!
class ddict(dict):

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value
    
    def clean_dict(self):
        return {k: v for k, v in self.items() if v not in [None, [], {}]}


class YAMLMultiObjectMetaclass(YAMLObjectMetaclass):
    """
    The metaclass for YAMLMultiObject.
    """

    def __init__(cls, name, bases, kwds):
        super(YAMLMultiObjectMetaclass, cls).__init__(name, bases, kwds)
        if "yaml_tag" in kwds and kwds["yaml_tag"] is not None:
            # cls.yaml_loader.add_multi_constructor(cls.yaml_tag, cls.from_yaml)
            cls.yaml_dumper.add_multi_representer(cls, cls.to_yaml)


class YAMLMultiObject(YAMLObject, metaclass=YAMLMultiObjectMetaclass):
    """
    An object that dumps itself to a stream.

    Use this class instead of YAMLObject in case 'to_yaml' and 'from_yaml' should
    be inherited by subclasses.
    """

    pass


class BaseVolume(YAMLMultiObject):
    """
    @brief representation of a docker-compose volume

    It can have one of the following types:
    - 'bind' for shared folders (bind-mounts)
    - 'volume' for anonymus or named docker volumes
        (depending on wether 'name' is set)
    - tmpfs
    """

    yaml_tag = "!BaseVolume"

    def __init__(self, **kwargs):
        self._data = ddict()
        self.mode = "base"

        # services level volume elements
        self._data["type"] = "volume"
        self._data["source"] = None
        self._data["target"] = None

        # bind: {propagation:  , selinux: , create_host_path: }
        self._data["read_only"] = False
        # volume: {nocopy: bool }

        # Volumes top-level elements
        self._data["driver"] = None  # str
        self._data["name"] = None  # str
        self._data["labels"] = []
        self._data["driver_opts"] = ddict()
        self._data["external"] = (
            None  # might be bool or {name: external-name-to-lookup}
        )

        self._data["subdir"] = None

        for key, value in kwargs.items():
            # only handle valid keys, docker knows about
            if key in self._data:
                if key == "labels":
                    self._data[key].append(value)
                else:
                    self._data[key] = value

        super().__init__()

    def __hash__(self):
        return hash((self._data["type"], self._data["target"], self._data["source"]))

    def __eq__(self, other):
        return (self._data["type"], self._data["source"], self._data["target"]) == (
            other.asDict()["type"],
            other.asDict()["source"],
            other.asDict()["target"],
        )

    @classmethod
    def to_yaml(cls, dumper, data):
        return basevol_representer(dumper, data)

    def __repr__(self) -> str:
        vals = []
        if self._data["type"] != None:
            vals.append("type={}".format(self._data["type"]))
        if self._data["source"] != None:
            vals.append("source={}".format(self._data["source"]))
        if self._data["target"] != None:
            vals.append("target={}".format(self._data["target"]))

        return "Volume(%r)" % (", ".join(vals))

    def asDict(self):
        return self._data

    def getType(self) -> str:
        """!@brief  returns the type of the volume
        one of
            - sharedFolder -> bind
            - named or anonymous volume -> volume
            - tmpfs
        """
        return self._data["type"]

    def setType(self, _type: str):
        """
        one of 'volume' , 'bind', 'tmpfs'
        """
        assert _type in ['volume' , 'bind', 'tmpfs'], f'unknown docker volume type: {_type}'
        self._data["type"] = _type
        return self

    def setSource(self, src: str):

        self._data["source"] = src
        return self


# prints all attributes
def basevol_representer(dumper, data: BaseVolume):
    if data.mode == "base":
        return dumper.represent_dict(            
                data.asDict().clean_dict()          
        )
    elif data.mode == "service":
        return dumper.represent_dict(
            filter(
                lambda kv: kv[0] in ["type", "source", "target", "read_only"],
                data.asDict().clean_dict().items(),
            )
        )
    elif data.mode == "toplevel":
        return dumper.represent_dict(
            filter(
                lambda kv: kv[0] in ["driver", "name", "labels", "external", "driver_opts"],
                data.asDict().clean_dict().items(),
            )
        )


add_representer(BaseVolume, basevol_representer)


class ServiceLvlVolume(BaseVolume):
    # def __init__(**kwargs):
    #    super().__init__(kwargs)
    yaml_tag = "!SvcVolume"

    def __init__(self, obj):
        super().__init__()
        self._data = obj._data

    @classmethod
    def to_yaml(cls, dumper, data):
        return svcvol_representer(dumper, data)


def svcvol_representer(dumper, data: BaseVolume):
    return dumper.represent_dict(
        filter(
            lambda kv: kv[0] in ["type", "source", "target"],
            data.asDict().clean_dict().items(),
        )
    )


add_representer(ServiceLvlVolume, svcvol_representer)


class TopLvlVolume(BaseVolume):
    # def __init__(self,**kwargs):
    #    super().__init__(kwargs)
    yaml_tag = "!Volume"

    def __init__(self, obj):
        super().__init__()
        self._data = obj._data

    @classmethod
    def to_yaml(cls, dumper, data):
        return topvol_representer(dumper, data)


def topvol_representer(dumper, data):
    return dumper.represent_dict(
        filter(
            lambda kv:  kv[0] in ["driver", "name", "labels", "external", "driver_opts"],
            data.asDict().clean_dict().items(),
        )
    )


add_representer(TopLvlVolume, topvol_representer)
