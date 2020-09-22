from typing import Dict
from .Printable import Printable

class Simulator(Printable):
    """!
    @brief The Simulator class.
    """

    __objects: Dict[str, object]

    def __init__(self):
        """!
        @brief Simulator constructor.
        """
        self.__objects = {}

    def register(self, name: str, obj: object) -> None:
        """!
        @brief Register an object with the internet.

        @param name name of the object.
        @param obj target object.
        @throws AssertionError if name exists.
        """
        assert name not in self.__objects, 'object with name {} already exist.'.format(name)
        self.__objects[name] = obj

    def get(self, name: str) -> object:
        """!
        @brief Retrive an object with name.

        @param name name of the object
        @throws AssertionError if name does not exist.
        @returns object.
        """
        assert name in self.__objects, 'object with name {} does not exist.'.format(name)
        return self.__objects[name]
