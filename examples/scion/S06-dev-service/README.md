### Proposal: Remote Development Service

The DevelopmentService prepares a node for [Remote Development with VSCode](https://code.visualstudio.com/docs/remote/remote-overview).
It installs the VSCode Remote Server on the Node during the docker image build, which allows to ssh into the running container later i.e. to debug software.
As of now the primary anticipated use of the seed-emulator has been the deployment of fully developed applications into an emulated szenario i.e. to observe its behaviour.
With the DevService this paradigm can be adapted to meed the need of developing i.e. P2P software to maturity in a distributed environment.

The DevService allows for each individual node that it is installed on, to specify one or more Git repositories that shall be checked out (along with the desired filesystem path and branch) as well as the VSCode Extensions required for the projects software stack (i.e. golang.Go for the SCION implementation which is written in Go)
The DevService takes care to install the entirety of build and analysis tools that are needed for a given programming language at docker image build time (for Go this being i.e. the compiler, language server gopls, debugger delve) so that no annoying time delay arises once the emulator is running and you want to attach to a container. 
Any specified Git repositories are checked out on its own separate docker volume, for the changes to persist between runs of the simulator in case one forgets to push.

### Concerns:
- software development requires a 'real internet' connection of the container be it to git push/pull or fetch project dependencies for a build (i.e. go get, cargo build etc. ) Currently this is achieved by adding the nodes default gateway ( router node ) in the simulation to a docker-bridge network which it shares only with one other node, the docker-host that acts as a default gateway for the router. The subnetmask for these 'micro' networks is deliberately kept as big as possible, 
    to allow as least nodes as possible on it (ideally /30 for only: the router-node, docker-host , broadcast and network address )
    This is to inhibit 'short-circuiting' the simulated network topology (i.e. any crosstalk past the intended network topo among nodes)
    I tried an alternative approach of configuring these 'service-networks' as IPv6 [^1] to avoid confusion with the simulated IPv4 network and it worked just fine, but was nonetheless rendered impractical as github.com doesnt seem to support IPv6.

[^1]: requires some tinkering with the /etc/docker/daemon.json , setting the 'inet6' option in the /etc/resolv.conf so that any domain names resolve to AAAA records and setting a default ip -6 route 

### TODO:
- set up a script to install DROP rules in the POSTROUTING Chain of the docker hosts iptables to prevent crosstalk via the service network(s) 
- maybe its a better idea to have several subclasses of the server for different software stacks i.e. rust / Go /python etc. and leave only the basics i.e git in the service
- I have to look into the VSCode CLI again !! Time delays when first attaching to a container ought to be kept small, and thus as much as possible should be done at image build time
- I need to rework the way the PATH and other environment variables are reliably set in the containers ( it is annoying to always have to type i.e. 'export PATH=$PATH:/usr/local/go/bin')

