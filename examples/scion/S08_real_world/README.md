# Networking Application Development in SEED

//### Connect the simulation to the 'real world' outside Internet


This example is similar to `A03_real_world`

 A real-world AS included in the emulation
will collect the real network prefixes from the real Internet,
and announce them inside the emulator. Packets reaching this AS
will exit the emulator and be routed to the real destination.
Responses from the outside will come back to this real-world AS
and be routed to the final destination in the emulator.



The DevelopmentService prepares a node for [Remote Development with VSCode](https://code.visualstudio.com/docs/remote/remote-overview).
It installs the VSCode Remote Server on the Node during the docker image build, which allows to ssh into the running container later i.e. to debug software.

As of now the primary anticipated use of the seed-emulator has been the deployment of fully developed applications into an emulated szenario i.e. to observe its behaviour.

The DevService adapts the emulators primary paradigm of deploying fully develped applications into an emulated szenario,
 to meet the need of developing i.e. P2P software to maturity in a distributed environment.

The DevService allows for each individual node that it is installed on, to specify one or more Git repositories that shall be checked out
(along with the desired filesystem path and branch) as well as the VSCode Extensions required for the projects software stack
(i.e. golang.Go for the SCION-proto implementation which is written in Go)
The DevService takes care to install the entirety of build and analysis tools that are needed for a given programming language at docker image build time (for Go this being i.e. the compiler, language server gopls, debugger delve) so that no annoying time delay arises once the emulator is running and you want to attach to a container.
Any specified Git repositories are checked out on its own separate docker volume, for the changes to persist between runs of the simulator in case one forgets to push.

Since software development requires a 'real Internet' connection of the container be it to git push/pull or fetch project dependencies for a build (i.e. go get, cargo build etc. )
 This is achieved by promoting the nodes default gateway ( router node ) in the simulation into a 'RealWorldRouter' (which has access to the `000_svc` service network)
Use of a separate service network inhibits 'short-circuiting' the simulated network topology (i.e. any crosstalk past the intended network topo among nodes)


```
    devsvc = GolangDevService('jane.doe', 'jane.doe@example.com')
    repo_url = 'https://github.com/scionproto/scion.git'
    repo_branch = 'v0.12.0'
    repo_path = '/home/root/repos/scion'

    svc = devsvc.install(f'dev_152_cs1')
    svc.checkoutRepo(repo_url, repo_path, repo_branch, AccessMode.shared)
    emu.addBinding(Binding(f'dev_152_cs1', filter=Filter(nodeName=as152_cs1.getName(), asn=152)))

    svc3 = devsvc.install(f'dev_153_cs1')
    svc3.checkoutRepo(repo_url, repo_path, repo_branch, AccessMode.shared)
    emu.addBinding(Binding(f'dev_153_cs1', filter=Filter(nodeName=as153_cs1.getName(), asn=153)))

```