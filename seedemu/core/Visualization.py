class Vertex(object):
    """!
    @brief a Vertex in the SEED emulator client map.
    """

    __displayname: str
    __description: str

    def __init__(self) -> None:
        super().__init__()
        self.__displayname = None
        self.__description = None

    def setDisplayName(self, name: str):
        """!
        @brief set display name of this vertex on the map. This will be shown as
        the lable under the vertex on the map.

        @param name name text, or None to clear display name
        """
        self.__displayname = name

    def getDisplayName(self) -> str:
        """!
        @brief get display name of this vertex on the map.

        @returns display name, or none if unset.
        """
        return self.__displayname

    def setDescription(self, description: str):
        """!
        @brief set description of this vertex on the map. This will be shown as
        the description at the details panel when the vertex is selected.

        @param description description text, or None to clear description
        """
        self.__description = description

    def getDescription(self) -> str:
        """!
        @brief get description of this vertex on the map.

        @returns description, or none if unset.
        """
        return self.__description