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
    UBUNTU_20_04        = 'ubuntu20.04'
    SEEDEMU_BASE        = 'seedemu-base'
    SEEDEMU_ROUTER      = 'seedemu-router'
    SEEDEMU_ETHEREUM    = 'seedemu-ethereum'
    DEFAULT             = SEEDEMU_BASE

    # The relationship of the images: B is a subset of A means that 
    # A is built on top of A and has 
    SUBSET: Dict[str, list(str)] = {
                UBUNTU_20_04: [],
                SEEDEMU_BASE: [UBUNTU_20_04],
                SEEDEMU_ROUTER: [UBUNTU_20_04, SEEDEMU_BASE],
                SEEDEMU_ETHEREUM: [UBUNTU_20_04, SEEDEMU_BASE],
            }
    
    @staticmethod 
    def doesAContainB(A: BaseSystem, B: BaseSystem):  
        """!
        @brief Check if B is subset of A.

        @param A : BaseSystem
        @param B : BaseSystem

        @returns True if B is a subset of A.
        """
        if B.value in BaseSystem.SUBSET.value[A.value]:
            return True
        else:
            return False