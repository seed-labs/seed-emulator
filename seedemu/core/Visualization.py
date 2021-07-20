from __future__ import annotations

class Vertex(object):
    """!
    @brief a Vertex in the SEED emulator client map.
    """

    __displayname: str
    __description: str

    def __init__(self) -> None:
        """!
        @brief create a new vertex.
        """
        super().__init__()
        self.__displayname = None
        self.__description = None

    def setDisplayName(self, name: str) -> Vertex:
        """!
        @brief set display name of this vertex on the map. This will be shown as
        the lable under the vertex on the map.

        @param name name text, or None to clear display name

        @returns self, for chaining API calls.
        """
        self.__displayname = name

        return self

    def getDisplayName(self) -> str:
        """!
        @brief get display name of this vertex on the map.

        @returns display name, or none if unset.
        """
        return self.__displayname

    def setDescription(self, description: str) -> Vertex:
        """!
        @brief set description of this vertex on the map. This will be shown as
        the description at the details panel when the vertex is selected.

        @param description description text, or None to clear description.

        @returns self, for chaining API calls.
        """
        self.__description = description

        return self

    def getDescription(self) -> str:
        """!
        @brief get description of this vertex on the map.

        @returns description, or none if unset.
        """
        return self.__description