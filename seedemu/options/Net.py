from seedemu.core import BaseOptionGroup, Option, OptionMode


class NetOpts(BaseOptionGroup):

    class Mtu(Option):
        """!@ Maximum Transmission Unit of a Network in [byte]
        """
        value_type = int
        @classmethod
        def supportedModes(cls):
            return OptionMode.BUILD_TIME
        
        @classmethod
        def default(cls):
            """the default MTU of Ethernet is 1500bytes"""
            return 1500
        
    class Latency(Option):
        """!@ propagation latency of a link in [ms]
        """
        value_type = int
        @classmethod
        def supportedModes(cls):
            return OptionMode.BUILD_TIME
        
        @classmethod
        def default(cls):
            """default is unlimited datarate (infinite propagation speed, causing no delay)"""
            return 0
        
    class Bandwidth(Option):
        """!@ capacity of a link in [bits/second]
        """
        value_type = int
        @classmethod
        def supportedModes(cls):
            return OptionMode.BUILD_TIME
        
        @classmethod
        def default(cls):
            """default is unlimited bandwidth"""
            return 0
        
    class PacketLoss(Option):
        """!@ probability of packet loss on a link [0,1)
        """
        value_type = float
        @classmethod
        def supportedModes(cls):
            return OptionMode.BUILD_TIME
        
        @classmethod
        def default(cls):
            """default is perfect ideal link without loss"""
            return 0