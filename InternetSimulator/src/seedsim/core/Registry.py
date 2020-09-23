from typing import Dict, Tuple, List
from .Printable import Printable

class Registry:
    """!
    @brief The Registry class.

    Registry is the global container for all objects in the simulator.
    """

    __objects: Dict[Tuple[str, str, str], object] = {}

    def register(self, scope: str, type: str, name: str, obj: object) -> object:
        """!
        @brief Register an object with the internet.

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

    def get(self, scope: str, type: str, name: str) -> object:
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

    def getByType(self, scope: str, type: str) -> List[object]:
        """!
        @brief Retrive objects with type.

        @param scope scope of the object (e.g., asn).
        @param type type of the object (e.g., net/node)
        @returns objects.
        """
        rslt: List[object] = []

        for key, obj in self.__objects.items():
            (s, t, _) = key
            if s == scope and t == type: rslt.append(obj)

        return rslt

    def getByScope(self, scope: str) -> List[object]:
        """!
        @brief Retrive objects with scope.

        @param scope scope of the object (e.g., asn).
        @returns objects.
        """
        rslt: List[object] = []

        for key, obj in self.__objects.items():
            (s, _, _) = key
            if s == scope: rslt.append(obj)

        return rslt