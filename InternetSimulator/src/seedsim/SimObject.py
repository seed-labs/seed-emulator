class SimObject:
    """!
    @brief parent class of all seedsim classes
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