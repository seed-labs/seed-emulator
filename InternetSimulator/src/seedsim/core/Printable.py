class Printable:
    """!
    @brief Printable class.

    Implement this class for indentable print.
    """

    def print(self, indentation: int = 0) -> str:
        """!
        @brief get printable string.

        @param indentation indentation.

        @returns printable string.
        """

        raise NotImplementedError("print not implemented.")

    def __str__(self) -> str:
        return self.print(0)