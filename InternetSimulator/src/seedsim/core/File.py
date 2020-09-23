from .Printable import Printable

class File(Printable):
    """!
    @brief File class.

    This class represents a file on a node.
    """

    __content: str
    __path: str

    def __init__(self, path: str, content: str):
        """!
        @brief File constructor.

        Put a file onto a node.

        @param path path of the file.
        @param content content of the file.
        """

    def setPath(self, path: str):
        """!
        @brief Update file path.

        @param path new path.
        """
        self.__path = path

    def setContent(self, content: str):
        """!
        @brief Update file content.

        @param path new path.
        """
        self.__content = content

    def get(self) -> (str, str):
        """!
        @brief Get file path and content.

        @returns a tuple where the first element is path and second element is 
        content
        """
        return (self.__path, self.__content)
        