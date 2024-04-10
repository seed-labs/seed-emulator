Notes

- The EtcHosts layer should be automatically added. During the rendering,
  if this layer is not there, create a new one and add it. If such a layer
  already exists, there is no need to add. 

- `node.md`: still empty

- `compiler.md`: The content for Docker compiler should be more. Although
  some of the content is in the overall document, here, we should add 
  more details. 

- Local DNS: we made some changes regarding how to set the local DNS servers 
  on each node. The changes have not been merged yet (pending more testing).
  With this change, we need to update the documents and examples.

- Example reorganization: after merging everything to the `development` branch, 
  we should reorganize the example folders, moving all the blockchain examples to
  the D category:
  - `D00-blockchain-poa`: this will be used as the base for other examples,
    so make sure it covers the basics well. 
  - Remove `B08-Remix-Connection`
  - Remove `B09-Smart-Contract-Attacks`: it is already in a lab. 
  - Move `C04-ethereum-pos` to `D04-blockchain-pos` 
  - Faucet: `D05-faucet`.  
  - Chainlink: `D06-chainlink`. 

- Separate blockchain-related services from the Internet-related services. 
  This way, users who do not need blockchain do not need to add `import blockchain`
  to their code. This will solve the dependency issue that we face, because
  the blockchain services require additional Python modules that are not 
  needed for other users. 
  - This might not solve all the issues as users might still use `from seedemu import *`.
  - Another solution is to import additional modules inside the class,
    so that the modules are needed only when the class is called. 
    Will investigate this idea. This can be done by using the 
    `__import__` method. See [this link](https://www.geeksforgeeks.org/how-to-dynamically-load-modules-or-classes-in-python/)


