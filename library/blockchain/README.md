# Libraries for Blockchain

This folder contains the libraries that can be used to
interact with the blockchain.


## Installation

Sometimes in building the emulator, we need to copy
some of the libraries to a node. We can copy them to the
`/emu_library` folder, and then run the following command
to install these libraries:
```
pip install -e file:/emu_library
```

This will create a symlink of the `/emu_library` folder to Python's default module
search path, so a program can `import` these libraries like importing other
standard libraries. 


## Dependency

These libraries are used by the following services, so if changes are made, testing
is required:

- `ChainlinkService`
- `ChainlinkUserService` 


