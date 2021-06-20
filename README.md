Internet Emulator
---

The goal of this project is to build a emulator of the Internet, containing necessary components that will enable us to build replicas of the real-world Internet infrastructure. 

We can already experiment with small-scale attacks like ARP poisoning, TCP hijacking, and DNS poisoning, but our goal is to provide a emulation where users are allowed to conduct attacks on a macroscopic level. The emulation will enable users to launch attacks against the entire Internet. The emulator for the Internet allows users to experiment with various Internet technologies that people usually would not have access to, like BGP. This emulator will enable users to perform a nation-level BGP hijack to bring down the Internet for an entire nation, perform MITM on a core ISP router, or launch DNS poisoning attacks on the TLD name servers.

Users can join the simulated Internet with VPN client software. This emulation is completely transparent to users joining it, allowing many different possibilities. This allows users to conduct and experience in real-time, as if it was happening in the real world. Simulation is popular in every field of engineering, especially for those activities that are expensive or dangerous to conduct. However, popular Internet emulators usually do not do well in a real-time application, as they are mainly designed to be used for research and runs slow. Also, lots of no-for-research-use emulators have very high system requirements, rendering them unfeasible for large-scale emulations.

### Design

The emulator is built from four components: 

- Core classes, which provide the essential abstraction of the key emulator components like Network, Network Interface Card, Node (Router and Server),
- Layers, which provide a high-level API for building the emulation on different levels,
- Renderer, which "renders" the different layer and build a complete emulation, and
- Compiler, which "compiles" the product from renderer to actual emulation.

### Getting started

To get started with the emulator, install docker, docker-compose, and python3. Then, take a look at the `examples/` folder for examples. To run an example:

1. Pick an example; say we want `00-simple-peering`.
2. Add `seedemu` to `PYTHONPATH`. This can be done by running `source development.env` under the project root directory.
3. Bulid the emulation. For example 00, run `python3 examples/00-simple-peering/00-simple-peering.py`.
4. Build and run the containers. For example 00, step 3 should output the emulation to `simple-peering/`. To run it, first `cd simple-peering/`, then do `docker-compose build && docker-compose up`.
5. Optionally, start the seedemu web client. Open a new terminal window, navigate to the project root directory, cd to `client/`, and run `docker-compose build && docker-compose up`. seedemu client will be available at http://127.0.0.1:8080.

### FAQ

#### I'm getting `error: pool overlaps with other one on this address space`

If a previous emulation was not properly shut down, the networks it created might be left in docker. Those networks can conflict with the networks in the current emulation you try to run. 

To solve this, shut down the previous emulation properly by running `docker-compose down` in the previous emulation folder. If that somehow failed, or the previous emulation folder has been removed, try doing `docker network prune` - it will remove all networks that are not currently in use.

#### I'm getting `Unable to fetch some archives, maybe run apt-get update or try with --fix-missing?`

Docker caches previous build steps. One of the steps was `apt-get update`. This means if the apt repository was updated after the step being cached in a previous emulation build, docker would skip the `apt-get update` step, and the `apt-get install` steps will fail.

To solve this, run build without cache by providing the `--no-cache` option: `docker-compose build --no-cache`.