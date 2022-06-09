
from __future__ import annotations
import docker
from docker import DockerClient
from docker.models.containers  import *
import tarfile
import io, json
from seedemu import *


ContainerLabel: Dict[str, str] = {}
ContainerLabel['class'] = 'org.seedsecuritylabs.seedemu.meta.class'

class DockerController:
    """!
    @brief Docker controller base class.

    The base class for all controller.
    """

    __client:DockerClient

    def __init__(self):
        """!
        @brief Docker controller construnctor
    
        """
        self.__client = docker.from_env()

    def _getContainerById(self, id:str) -> Container:
        container = self.__client.containers.get(container_id=id)
        return container

    def _getContainersByClassName(self, className:str) -> ContainerCollection:
        all_containers = self.__client.containers.list()
        containers = []
        classes = []
        for container in all_containers:
            if ContainerLabel['class'] in container.attrs['Config']['Labels'].keys():
                classes = json.loads(container.attrs['Config']['Labels'][ContainerLabel['class']])
                if className in classes:
                    containers.append(container)
        return containers

    def getContainerById(self, id) -> DockerContainer:
        return DockerContainer(self._getContainerById(id))

    def getContainersByClassName(self, className:str) -> List[DockerContainer]:
        return list(map(DockerContainer, self._getContainersByClassName(className)))

    def executeCommandInContainers(self, containers:List[DockerContainer], cmd, detach:bool=False, workdir:str=None) -> Dict:
        assert containers != [], 'containers is empty'
        results={}
        for container in containers:
            result = container.executeCommand(cmd=cmd, detach=detach, workdir=workdir)
            results[container.getName()]=result

        return results
    
    # Not Implemented
    def buildImage(self, buildPath:str, tag:str):        
        self.__client.images.build(path=buildPath, tag=buildPath)
        
    def appendContainer(self, name:str, image:str, networks:list, labels:dict):
        client = self.__client
        output = "output"
        
        container = client.containers.create(image = image, 
                            cap_add=['ALL'], 
                            sysctls={'net.ipv4.ip_forward':1, 
                                        'net.ipv4.conf.default.rp_filter':0, 
                                        'net.ipv4.conf.all.rp_filter':0},
                            privileged=True,
                            name=name, 
                            network=networks[0],
                            labels=labels)

        '''client.networks.get(output+"_"+networks[0]).disconnect(container)
        for network in networks:
            client.networks.get(output+"_"+network).connect(container, ipv4_address=dcInfo['networks'][network]['ipv4_address'])
        '''
        container.start()

    def removeContainer(self):
        return

    def stopContainers(self):
        return
    
    def startContainers(self):
        return


class DockerContainer:
    """!
    @brief Docker Container base class.

    The base class for all containers.
    """
    __container:Container

    # Add api to check whether the container is still alive or not. 
    
    def __init__(self, container:Container):
        self.__container = container

    def executeCommand(self, cmd, detach:bool=False, workdir:str=None) -> str:
        """!
        Args:
            cmd (str or list): Command to be executed
            detach (bool): If true, detach from the exec command.
                Default: False
            workdir (str): Path to working directory for this exec session

        Returns:
            (ExecResult): A tuple of (exit_code, output)
                exit_code: (int):
                    Exit code for the executed command or ``None`` if
                    either ``stream`` or ``socket`` is ``True``.
                output: (generator, bytes, or tuple):
                    If ``stream=True``, a generator yielding response chunks.
                    If ``socket=True``, a socket object for the connection.
                    If ``demux=True``, a tuple of two bytes: stdout and stderr.
                    A bytestring containing response data otherwise.
        """
        result = self.__container.exec_run(cmd=cmd, detach=detach, workdir=workdir)
        
        assert result.exit_code == 0, "exit_code: "+str(result.exit_code)+"\n"+result.output.decode()

        return result.output.decode()

    def getName(self) -> str:
        return self.__container.name

    def getNetworkInfo(self) -> dict:
        networkInfo = json.loads(self.executeCommand(cmd="ip -j addr"))
        return networkInfo

    def copyFileFromContainer(self, src:str, dst:str):
        bits, stat = self.__container.get_archive(src)
        file = b"".join(bits)
        tar = tarfile.TarFile(fileobj=io.BytesIO(file))
        tar.extractall(dst)

# delete printFileFromContainer()
    def printFileFromContainer(self, src:str, dst:str):
        bits, stat = self.__container.get_archive(src)
        file = b"".join(bits)

        tar = tarfile.TarFile(fileobj=io.BytesIO(file))
        for member in tar:
            print(tar.extractfile(member.name).read().decode())

    # Not Implemented
    def copyFileToContainer(self, src:str, dst:str):
        return 

    def stopContainer(self):
        return

    def startContainer(self):
        return