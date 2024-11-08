# Buildtime Docker

This example demonstrates how to use a buildtime Docker container in the emulator build process.

## Read from Dockerfile

```python
from seedemu.utilities.BuildtimeDocker import BuildtimeDockerFile
with open(dockerfile_path, "r") as f:
    dockerfile = BuildtimeDockerFile(f.read())
```

## Build Docker Image

If it can be pulled from the Docker Hub:

```python
from seedemu.utilities.BuildtimeDocker import BuildtimeDockerImage
image = BuildtimeDockerImage("ethaccount")
```

If it needs to be built from a Dockerfile:

```python
from seedemu.utilities.BuildtimeDocker import BuildtimeDockerImage
image = BuildtimeDockerImage("ethaccount").build(dockerfile)
```

## Use Docker Image

```python
# Create a container from the image
container = image.container()
# Set entrypoint, command, and mount volumes
container.entrypoint("python").mountVolume(tmp_dir, "/app").run(
    "-c \"from eth_account import Account; f = open('account.txt', 'w'); f.write(Account.create().address); f.close()\""
)
```

It is recommended to pass `tmp_dir` as a volume to the container and copy the files back to output to avoid permission issues.

```python
import os
import shutil
import tempfile
tmp_dir = tempfile.mkdtemp(prefix="seedemu-ethaccount-")

# Do something with the container

output_dir = os.path.join(current_dir, "output")

shutil.rmtree(output_dir, ignore_errors=True)

shutil.copytree(tmp_dir, output_dir)

shutil.rmtree(tmp_dir, ignore_errors=True)
```

## Note

Older versions of `docker` have limit on the number of threads that can be created in a container.

When using `pip install` in the Dockerfile, it is recommended to use the `--progress-bar off` option to avoid issues with the progress bar.

Otherwise, users may encounter the following error when `pip install` is called:

```
RuntimeError: can't start new thread
```
