from typing import Dict, Tuple, List
from .Printable import Printable

class Registrable(object):
    """!
    @brief The Registerable base class.

    Base class for all Registrable objects.
    """
    _rscope: str
    _rtype: str
    _rname: str
    _attrs: Dict[str, object]

    def __init__(self):
        """!
        @brief Registerable class constructor.
        """
        super().__init__()
        self.__scope = 'undefined'
        self._rtype = 'undefined'
        self._rname = 'undefined'

    def doRegister(self, scope: str, type: str, name: str):
        """!
        @brief Handle registration.

        @param scope scope.
        @param type type.
        @param name name.
        """
        self._rscope = scope
        self._rtype = type
        self._rname = name
        self._attrs = {}
    
    def getRegistryInfo(self) -> Tuple[str, str, str]:
        """!
        @brief Get registry info

        @returns Tuple of scope, type and name
        """
        return (self._rscope, self._rtype, self._rname)

    def getAttribute(self, name: str, default: object = None) -> object:
        """!
        @brief Get an attribute.

        @param name name of attribute.
        @param default value to set and return if name not exist.

        @returns value, or None if not exist.
        """
        if name not in self._attrs:
            if default != None:
                self.setAttribute(name, default)
                return self._attrs[name]
            return None
        return self._attrs[name]

    def setAttribute(self, name: str, value: object):
        """!
        @brief Set an attribute.

        @param name name of attribute.
        @param value value of attribute.
        """
        self._attrs[name] = value

    def hasAttribute(self, name: str) -> bool:
        """!
        @brief Check if an attribute exists.

        @param name name of attribute.
        
        @returns True if exist, False otherwise.
        """
        return name in self._attrs

class Registry(Printable):
    """!
    @brief The Registry class.

    Registry is the global container for all objects in the emulator.
    """

    __objects: Dict[Tuple[str, str, str], Registrable]

    def __init__(self):
        """!
        @brief create a new Registry.
        """
        self.__objects = {}

    def register(self, scope: str, type: str, name: str, obj: Registrable) -> Registrable:
        """!
        @brief Register an object.

        @param scope scope of the object (e.g., asn).
        @param type type of the object (e.g., net/node)
        @param name name of the object.
        @param obj target object.
        @returns registered object
        @throws AssertionError if name exists.
        """
        assert (scope, type, name) not in self.__objects, 'object with name {} already exist.'.format(name)
        obj.doRegister(scope, type, name)
        self.__objects[(scope, type, name)] = obj
        return self.__objects[(scope, type, name)]

    def get(self, scope: str, type: str, name: str) -> Registrable:
        """!
        @brief Retrive an object with name.

        @param scope scope of the object (e.g., asn).
        @param type type of the object (e.g., net/node)
        @param name name of the object.
        @throws AssertionError if name does not exist.
        @returns object.
        """
        assert (scope, type, name) in self.__objects, 'object with name {} does not exist.'.format(name)
        return self.__objects[(scope, type, name)]

    def has(self, scope: str, type: str, name: str) -> bool:
        """!
        @brief Test if an object exist.

        @param scope scope of the object (e.g., asn).
        @param type type of the object (e.g., net/node)
        @param name name of the object.
        @returns True if exist, False otherwise.
        """
        return (scope, type, name) in self.__objects

    def getByType(self, scope: str, type: str) -> List[Registrable]:
        """!
        @brief Retrive objects with type.

        @param scope scope of the object (e.g., asn).
        @param type type of the object (e.g., net/node)
        @returns objects.
        """
        rslt: List[Registrable] = []

        for key, obj in self.__objects.items():
            (s, t, _) = key
            if s == scope and t == type: rslt.append(obj)

        return rslt

    def getAll(self) -> Dict[Tuple[str, str, str], Registrable]:
        """!
        @brief Get all objects in the Global Registry.

        @returns dictionary, where keys in tuple (scope, type, name) and value
        is object
        """
        return self.__objects

    def getByScope(self, scope: str) -> List[Registrable]:
        """!
        @brief Retrive objects with scope.

        @param scope scope of the object (e.g., asn).
        @returns objects.
        """
        rslt: List[Registrable] = []

        for key, obj in self.__objects.items():
            (s, _, _) = key
            if s == scope: rslt.append(obj)

        return rslt
    
    def print(self, indent: int):
        out = (' ' * indent) + 'Registry:\n'
        indent += 4
        for keys, val in self.__objects.items():
            [scope, type, name] = keys
            out += (' ' * indent) + 'Object {}/{}/{}:\n'.format(scope, type, name)
            out += val.print(indent + 4)

        return out

class ScopedRegistry(Registry):
    """!
    @brief Scoped Registry class.

    Scoped wrapper for Registry class.
    """

    __reg: Registry
    __scope: str

    def __init__(self, scope: str, parent: Registry):
        """!
        @brief Scoped Registry ctor.

        @param scope scope to bind to.
        @param parent parent Registry object.
        """
        self.__scope = scope
        self.__reg = parent

    def register(self, type: str, name: str, obj: Registrable) -> Registrable:
        """!
        @brief Register an object.

        @param type type of the object (e.g., net/node)
        @param name name of the object.
        @param obj target object.
        @returns registered object
        @throws AssertionError if name exists.
        """
        return self.__reg.register(self.__scope, type, name, obj)

    def get(self, type: str, name: str) -> object:
        """!
        @brief Retrive an object with name.

        @param type type of the object (e.g., net/node)
        @param name name of the object.
        @throws AssertionError if name does not exist.
        @returns object.
        """
        return self.__reg.get(self.__scope, type, name)

    def has(self, type: str, name: str) -> bool:
        """!
        @brief Test if an object exist.

        @param type type of the object (e.g., net/node)
        @param name name of the object.
        @returns True if exist, False otherwise.
        """
        return self.__reg.has(self.__scope, type, name)

    def getByType(self, type: str) -> List[Registrable]:
        """!
        @brief Retrive objects with type.

        @param type type of the object (e.g., net/node)
        @returns objects.
        """
        return self.__reg.getByType(self.__scope, type)