import docker
from docker import DockerClient
from docker.models.containers  import *
import tarfile
import io
from os import mkdir, chdir, getcwd, path
from shutil import rmtree
import yaml
from seedemu import *

ContainerLabel: Dict[str, str] = {}
ContainerLabel['class'] = 'org.seedsecuritylabs.seedemu.meta.class'


class DockerController:
    """!
    @brief Docker controller class.

    This class represents a docker controller.
    """

    __client:DockerClient

    def __init__(self):
        """!
        @brief Docker controller construnctor
    
        """
        self.__client = docker.from_env()


    def getContainerById(self, id:str) -> Container:
        container = self.__client.containers.get(container_id=id)
        return container

    def getContainersByClassName(self, className:str) -> ContainerCollection:
        all_containers = self.__client.containers.list()
        containers = []
        for container in all_containers:
            if ContainerLabel['class'] in container.attrs['Config']['Labels'].keys():
               if container.attrs['Config']['Labels'][ContainerLabel['class']] == className:
                   containers.append(container)

        assert containers is not [], "No container className is "+className
        return containers

    def execContainer(self, container:Container, cmd, detach:bool=False, workdir:str=None) -> str:
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
        result = container.exec_run(cmd=cmd, detach=detach, workdir=workdir)
        
        assert result.exit_code == 0, "exit_code: "+result.exit_code+"\n"+result.output.decode()

        return result.output.decode()

    def execContainers(self, containers:ContainerCollection, cmd, detach:bool=False, workdir:str=None) -> Dict:
        results={}
        for container in containers:
            result = container.exec_run(cmd=cmd, detach=detach, workdir=workdir)
            results[container.name]=result

        return results

    def getNetworkInfo(self, container:Container) -> str:
        networkInfo = self.execContainer(container=container, cmd="ip addr")
        return networkInfo

    #tarFile update needed
    def readFile(self, container:Container, fileName:str):
        bits, stat = container.get_archive(fileName)
        file = b"".join(bits)

        tar = tarfile.TarFile(fileobj=io.BytesIO(file))
        for member in tar:
            print(tar.extractfile(member.name).read().decode())


    def addNode(self, emu:Emulator, scope:str, name:str, type:str='hnode'):
        client = self.__client
        output = "output"
        
        emu.render()
        obj = emu.getRegistry().get(type=type, scope=scope, name=name)
        docker = Docker()

        buildPath = "_".join([type, scope, name])
        
        cur = getcwd()
        if path.exists(output):
            rmtree(output)
            
        mkdir(output)
        chdir(output)

        dcInfo = yaml.safe_load(docker._compileNode(obj))[buildPath]

        chdir(cur)

        networks = list(dcInfo['networks'].keys())
        
        client.images.build(path=output+"/"+buildPath, tag=output+buildPath)
        

        if client.containers.list(all=True, filters={'name':dcInfo['container_name']}) != []:
            client.containers.list(all=True, filters={'name':dcInfo['container_name']})[0].stop()
            client.containers.prune()    

        
        container = client.containers.create(image = name, 
                            cap_add=['ALL'], 
                            sysctls={'net.ipv4.ip_forward':1, 
                                        'net.ipv4.conf.default.rp_filter':0, 
                                        'net.ipv4.conf.all.rp_filter':0},
                            privileged=True,
                            name=dcInfo['container_name'], 
                            network=output+"_"+networks[0],
                            labels=dict(dcInfo['labels']))

        self.__client.networks.get(output+"_"+networks[0]).disconnect(container)
        for network in networks:
            self.__client.networks.get(output+"_"+network).connect(container, ipv4_address=dcInfo['networks'][network]['ipv4_address'])
        
        container.start()


    


