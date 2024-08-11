from __future__ import annotations

from seedemu.services.EthereumService.EthUtil import Genesis


class CustomGenesis(Genesis):
    """!
    @brief Genesis manage class
    """

    def addCode(self, address: str, code: str) -> Genesis:
        """!
        @brief add code to genesis file.

        @param address address to add code.
        @param code code to add.

        @returns self, for chaining calls.
        """
        if self._genesis["alloc"][address[2:]] is not None:
            self._genesis["alloc"][address[2:]]["code"] = code
        else:
            self._genesis["alloc"][address[2:]] = {"code": code}

        return self