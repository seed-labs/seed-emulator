# How to add experimental codes.

* Create a new folder for your new-component under `seed-emulator/experiments`
i.e) seed-emulator/experiments/[new-component]


## Partially allow developers to update. 
:only Add not deleting or editing existing codes

```
DockerImageConstant
BaseSystem
Test codes
```

## How to use newly created service/layer class?

In the stage of experiment, create `lib` folder under your directory and place your newly created service or layer class instead of adding them directly into the `seedemu` package. After the experimental stage, our committee will decide to allow add the new features or not.

i.e) In case of `seed-emulator/experiments/ethereum-layer2`, it has `lib` directory. It contains `EthereumLayer2Service` package which is new service for the ethereum-layer2 component.

## Can we update the existing service class? 

We encourage not to update the existing codes. At the experimental stage, there is a way to use existing code without updating them directly. The way is to create a subclass of the existing class. After the experimental stage, our committee will decide to allow update the existing code or not.

In case of `ethereum-layer2`, it needs to add a method inside `Blockchain` and `Genesis` class. By using the `subclass` approach, we acheive this goal.

**Custom Genesis class code**
```
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
```

**Custom Blockchain class code**

```
from __future__ import annotations

from seedemu.services.EthereumService import Blockchain
from .EthUtil import CustomGenesis

class CustomBlockchain(Blockchain):
    
    def addCode(self, address: str, code: str) -> Blockchain:
        """!
        @brief Add code to an account by setting code field of genesis file.

        @param address The account's address.
        @param code The code to set.

        @returns Self, for chaining calls.
        """
        self._genesis.__class__ = CustomGenesis
        self._genesis.addCode(address, code)
        return self
```

In these code, they are creating new `CustomGenesis` and `CustomBlockchain` class that inherit `Genesis` class and `Blockchain` class. One thing you need to take a look is this line. :

```
self._genesis.__class__ = CustomGenesis
```

This code line is inside the method `CustomBlockchain::addCode`. As it is using a CustomGenesis type, we need to specify the type of `self._genesis` is `CustomGenesis` using this line.








