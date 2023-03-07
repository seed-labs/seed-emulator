from __future__ import annotations
from typing import List, Set

class DockerImage(object):
    """!
    @brief The DockerImage class.

    This class represents a candidate image for docker compiler.
    """

    __software: Set[str]
    __name: str
    __local: bool
    __dirName: str

    def __init__(self, name: str, software: List[str], local: bool = False, dirName: str = None) -> None:
        """!
        @brief create a new docker image.

        @param name name of the image. Can be name of a local image, image on
        dockerhub, or image in private repo.
        @param software set of software pre-installed in the image, so the
        docker compiler can skip them when compiling.
        @param local (optional) set this image as a local image. A local image
        is built locally instead of pulled from the docker hub. Default to False.
        @param dirName (optional) directory name of the local image (when local
        is True). Default to None. None means use the name of the image.
        """
        super().__init__()

        self.__name = name
        self.__software = set()
        self.__local = local
        self.__dirName = dirName if dirName != None else name

        for soft in software:
            self.__software.add(soft)

    def getName(self) -> str:
        """!
        @brief get the name of this image.

        @returns name.
        """
        return self.__name

    def getSoftware(self) -> Set[str]:
        """!
        @brief get set of software installed on this image.
        
        @return set.
        """
        return self.__software

    def getDirName(self) -> str:
        """!
        @brief returns the directory name of this image.

        @return directory name.
        """
        return self.__dirName
    
    def isLocal(self) -> bool:
        """!
        @brief returns True if this image is local.

        @return True if this image is local.
        """
        return self.__local
    
    def addSoftwares(self, software) -> DockerImage:
        """!
        @brief add softwares to this image.

        @return self, for chaining api calls.
        """
        for soft in software:
            self.__software.add(soft)