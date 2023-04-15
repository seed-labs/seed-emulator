# Automatic Docker Topology Setup and Testing

Install docker-py and python-on-whales.

```bash
pip install docker python-on-whales
```

docker-py os the official Python SDK for Docker. python-on-whales is a wrapper for the Docker command line interface. We use it to invoke `docker compose` which is currently not supported by the SDK.

Note that python-on-whales uses docker compose version 2, i.e., the command `docker compose` instead of version 1 which is `docker-compose` (note the `-`). Docker compose v1 is implemented in Python, but unfortunately does not provide a stable API. Compose v2 is implemented in Go and has to be installed as a plugin for Docker.

## Network topology

The network topology is the same as in S03-bandwidth-test. Each AS has a `bwtest` host with the bwtester server running.

```python
import docker
import python_on_whales
```

We have to import the docker and python-on-whales libraries.

## Run an automatic bandwidth test

Running the example `docker-api.py` will create and render a SEED network, build Docker containers and bring the compose topology up.

```python
whales = python_on_whales.DockerClient(compose_files=["./output/docker-compose.yml"])
whales.compose.build()
whales.compose.up(detach=True)
```

We could use python-on-whales directly to execute commands in the containers, but for this example we are going to use the Python Docker client. First we have to instantiate the client and connect it to the Docker daemon. Then we can obtain references to the containers we have created through `docker compose`.

```python
client: docker.DockerClient = docker.from_env()
ctrs = {ctr.name: client.containers.get(ctr.id) for ctr in whales.compose.ps()}
```
Using the container objects we can run commands on the emulated hosts. In this case, we run bandwidth tests against the server in AS 1-150. A bandwidth tester client is started on each `bwtest` host one after the other and the results are printed.

```python
time.sleep(10) # Give SCION some time
for name, ctr in ctrs.items():
    if "bwtest" not in name:
        continue
    print("Run bwtest in", name, end="")
    ec, output = ctr.exec_run("scion-bwtestclient -s 1-150,10.150.0.30:40002")
    for line in output.decode('utf8').splitlines():
        print("  " + line)
```

Once the tests have finished, the network is shut down.

```python
whales.compose.down()
```
