from __future__ import annotations
from enum import Enum
from typing import Dict

class BaseSystem(Enum):
    """!
    @brief Base System Enum.
    """

    # These are code names for the systems that can be used as 
    # the base for the node. During the Docker compilation time, these
    # names will be used to find the corresponding docker images. 
    UBUNTU_20_04      = 'ubuntu20.04'
    GETH_1_10     = 'geth1.10'
    LIGHTHOUSE_3_2_1 = 'lighthouse3.2.1'
    LCLI_3_2_1 = 'lcli3.2.1'
    DEFAULT        = UBUNTU_20_04

    # The relationship of the images: B is a subset of A means that 
    # A is built on top of A and has 
    SUBSET: Dict[str, list(str)] = {
                GETH_1_10: [UBUNTU_20_04],
                LIGHTHOUSE_3_2_1: [UBUNTU_20_04, GETH_1_10],
                LCLI_3_2_1: [UBUNTU_20_04]
            }
    
    @staticmethod 
    def isSubset(self, A: BaseSystem, B: BaseSystem):  
        if B.value in self.SUBSET[A.value]:
            return True
        else:
            return False