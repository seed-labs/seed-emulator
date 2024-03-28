## Build Custom Chainlink Image
This guide will walk you through the process of building a custom Chainlink image using a Dockerfile. We are using version 2.3.0 of the Chainlink repository.

### Prerequisites
- [Go v1.20](https://golang.org/doc/install)
- [Node.js v16](https://nodejs.org/en/download/package-manager/)
- [pnpm via npm](https://pnpm.io/installation)

### Changes made to the Dockerfile
- Changed the ENTRYPOINT to `["bash"]` to allow for running the Chainlink node in the background

### Steps for building the custom Chainlink docker image
1. Clone the Chainlink repository
    ```bash
    git clone https://github.com/smartcontractkit/chainlink && cd chainlink
    ```
2. Change the branch to verison release/2.3.0
    ```bash
    git checkout release/2.3.0
    ```
3. Build the Chainlink binaries
    ```bash
    make install
    ```
4. Go to the `core` directory
    ```bash
    cd core
    ```
5. Copy [this Dockerfile](./chainlink.Dockerfile) in the current folder
6. Go back to the root directory
    ```bash
    cd ..
    ```
7. Build the custom Chainlink image
    ```bash
     docker build . -t chainlink-develop:latest -f ./core/chainlink.Dockerfile
    ```

