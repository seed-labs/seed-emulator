import subprocess
from contextlib import contextmanager
import os
import tempfile
from typing import Dict

@contextmanager
def cd(path):
    """@private Not supposed to be imported. Any other module should not rely on this function."""
    old_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def sh(command, input=None):
    """@private Not supposed to be imported. Any other module should not rely on this function."""
    try:
        if isinstance(command, list):
            command = " ".join(command)
        p = subprocess.run(
            command,
            shell=True,
            input=input,
        )
        return p.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode

class BuildtimeDockerFile:
    def __init__(self, content: str):
        self.__content = content

    def getContent(self) -> str:
        return self.__content


class BuildtimeDockerImage:
    def __init__(self, imageName: str):
        self.__imageName = imageName

    def build(
        self,
        dockerfile: BuildtimeDockerFile,
        context: str = None,
        args: Dict[str, str] = None,
    ):
        if not context:
            context = tempfile.mkdtemp(prefix="seedemu-docker-")
        with cd(context):
            build_command = f"docker build -t {self.__imageName}"
            for arg, value in args.items():
                build_command += f" --build-arg {arg}={value}"
            sh(build_command + " -", input=dockerfile.getContent())
        return self

    def container(self):
        return BuildtimeDockerContainer(self.__imageName)


class BuildtimeDockerContainer:
    def __init__(self, imageName: str):
        self.__imageName = imageName
        self.__volumes = []
        self.__env = []
        self.__entrypoint = None
        self.__workdir = None

    def mountVolume(self, source: str, target: str):
        self.__volumes.append((source, target))
        return self

    def env(self, envName: str, envValue: str):
        self.__env.append((envName, envValue))
        return self

    def workdir(self, workdir: str):
        self.__workdir = workdir
        return self

    def entrypoint(self, entrypoint: str):
        self.__entrypoint = entrypoint
        return self

    def run(self, command: str = None):
        run_command = "docker run -it --rm"
        if self.__workdir:
            run_command += f" -w {self.__workdir}"
        for key, value in self.__env:
            run_command += f" -e {key}={value}"
        if self.__entrypoint:
            run_command += f" --entrypoint {self.__entrypoint}"
        for source, target in self.__volumes:
            run_command += f" -v {source}:{target}"
        run_command += f" {self.__imageName}"
        if command:
            run_command += f" {command}"
        sh(run_command)