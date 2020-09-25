from typing import Dict, Tuple, List
from .Printable import Printable

class Registrable(object):
    """!
    @brief The Registerable base class.

    Base class for all Registrable objects.
    """
    pass

class Registry(Printable):
    """!
    @brief The Registry class.

    Registry is the global container for all objects in the simulator.
    """

    __objects: Dict[Tuple[str, str, str], Registrable] = {}

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

    __reg = Registry()
    __scope: str

    def __init__(self, scope: str):
        """!
        @brief Scoped Registry ctor.

        @param scope scope to bind to.
        """
        self.__scope = scope

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

        @param scope scope of the object (e.g., asn).
        @param type type of the object (e.g., net/node)
        @param name name of the object.
        @returns True if exist, False otherwise.
        """
        return self.__reg.has(self.__scope, type, name)

    def getByType(self, type: str) -> List[Registrable]:
        """!
        @brief Retrive objects with type.

        @param scope scope of the object (e.g., asn).
        @param type type of the object (e.g., net/node)
        @returns objects.
        """
        return self.__reg.getByType(self.__scope, type)