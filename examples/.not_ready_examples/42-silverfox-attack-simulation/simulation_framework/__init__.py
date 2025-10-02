"""
银狐木马攻击仿真复现实验 - 仿真框架包
Silver Fox Trojan Attack Simulation - Simulation Framework Package

该包包含攻击仿真的核心组件：
- AttackOrchestrator: 攻击编排器
- LateralMovementSimulator: 横向移动模拟器  
- DataExfiltrationSimulator: 数据外泄模拟器
"""

from .attack_orchestrator import AttackOrchestrator
from .lateral_movement import LateralMovementSimulator
from .data_exfiltration import DataExfiltrationSimulator

__all__ = [
    'AttackOrchestrator',
    'LateralMovementSimulator', 
    'DataExfiltrationSimulator'
]