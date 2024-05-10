# Ethereum Blockchain (POA)




## Other useful APIs

These APIs are not used in this example, but they might be useful
to satisfy additional emulation needs.


- Set custom `geth` command option: for commonly-used options, we already
  have APIs to set them. However, for options not covered by these APIs,
  users can use this generic API to set them. 
  ```
  eth_node.setCustomGethCommandOption("--http --http.addr 0.0.0.0")
  ```

- Use custom `geth` binary file: some users want to run a modified version
  of the `geth` software on a particular node. They can do this
  using the following API.
  ```
  eth_node.setCustomGeth("./custom_geth_binary")
  ```

