from seedemu.core import BaseOptionGroup, Option, OptionMode


class SysctlOpts(BaseOptionGroup):
# NOTE: the classname is dynamically changed to just 'sysctl' so the
# nested option names don't become too lengthy...

    class NetIpv4(BaseOptionGroup):

        class IP_FORWARD(Option):
            """net.ipv4.ip_forward flag"""
            value_type = bool
            @classmethod
            def supportedModes(cls) -> OptionMode:
                """!@brief 'ip_forward' sysctl flag can be changed in the 'sysctl:' section
                    of the node's service definition in docker-compose.yml file.
                    This does not require an image rebuild.
                """
                return OptionMode.BUILD_TIME|OptionMode.RUN_TIME
            @classmethod
            def default(cls):
                return True
            def __repr__(self):
                return f"net.ipv4.{self.getName().lower()}={'1' if self._mutable_value else '0'}"

        class Conf(BaseOptionGroup):
            """
            net.ipv4.conf.* flags
            @note the sequence is changed compared to linux sysctl.
                Name of the flag preceedes the name of the interface:
                    net.ipv4.conf.rp_filter.all = 1
                            .conf.rp_filter.net0 = 1
                                ...
                Add all interface settings directlz here:
                - log_martians
                - mc_forwarding
                - proxy_arp
                - forwarding
                .etc . . .
                The actual value of the options/sysctl-flags is a map
                 {interface_id(or 'all|default') -> option_value}

            """

            # /conf/[all|default|interface]/{rp_filter,log_martians, ..}
            # all..sets a value for all interfaces
            # 'interface' .. changes special settings per interface
            # (where "interface" is the name of your network interface)

            class RP_FILTER(Option):
                value_type = dict

                @classmethod
                def supportedModes(cls) -> OptionMode:
                    """@note values for 'all' & 'default' interfaces can be set in docker-compose.yml (RUNTIME).
                            However flags for interfaces with custom names (i.e. 'net0')
                            that are renamed by /interface_setup script on startup have to be set in /start.sh script(BUILD_TIME).

                    """
                    return OptionMode.BUILD_TIME|OptionMode.RUN_TIME

                def all(self) -> bool:
                    return self._mutable_value.get('all', False)

                def default(self) -> bool:
                    return self._mutable_value.get('default', False)

                @classmethod
                def default(cls):
                    return {'all': False, 'default': False}

                def __repr__(self):
                    vals = []
                    for _if, val in self._mutable_value.items():
                      vals.append( f"net.ipv4.conf.{_if}.{self.getName().lower()}={'1' if  val else '0'}" )
                    return '\n           '.join(vals)

                def repr_build_time(self):
                    vals = []
                    for _if, val in self._mutable_value.items():
                      if _if not in ['all', 'default']:
                        vals.append( f"net.ipv4.conf.{_if}.{self.getName().lower()}={'1' if  val else '0'}" )
                    return '\n           '.join(vals)

                def repr_runtime(self):
                    vals = []
                    for _if, val in self._mutable_value.items():
                      if _if in ['all', 'default']:
                        vals.append( f"net.ipv4.conf.{_if}.{self.getName().lower()}={'1' if  val else '0'}" )
                    return '\n           '.join(vals)

            #value_type =  bool for some 'int' for others

        class Udp(BaseOptionGroup):
            '''
            #NOTE must be set on docker-host
            class mem(Option):      # rename  total_mem or global_mem  ?!
                """!@brief Number of pages allowed for queueing by all UDP sockets.
                udp_mem - vector of 3 INTEGERs: min, pressure, max

                	min: Below this number of pages UDP is not bothered about its
                    	memory appetite. When amount of memory allocated by UDP exceeds
                    	this number, UDP starts to moderate memory usage.
                	pressure: This value was introduced to follow format of tcp_mem.
                	max: Number of pages allowed for queueing by all UDP sockets.
                	Default is calculated at boot time from amount of available memory.
                """
                value_type = tuple # (min,pressure,max) or better {'min': 4000, 'max': 32000 } ?!
                @classmethod
                def supportedModes(cls) -> OptionMode:
                    return OptionMode.BUILD_TIME|OptionMode.RUN_TIME
                @classmethod
                def default(cls):
                    # just the values of my laptop
                    return (183768, 245026, 367536)
                def __repr__(self):
                   return f"net.ipv4.udp_mem={self.value[0]} {self.value[1]} {self.value[2]}"
                def repr_runtime(self):
                    return self.__repr__()
                def repr_build_time(self):
                    return self.__repr__()
            '''

            class rmem_min(Option):
                """!@brief Minimal size of receive buffer used by UDP sockets in moderation.
                udp_rmem_min - INTEGER

                	Each UDP socket is able to use the size for receiving data, even if
                	total pages of UDP sockets exceed udp_mem pressure. The unit is byte.
                	Default: 4K
                """
                value_type = int
                @classmethod
                def supportedModes(cls) -> OptionMode:
                    return OptionMode.BUILD_TIME|OptionMode.RUN_TIME
                @classmethod
                def default(cls):
                    return 4000
                def __repr__(self):
                    return f"net.ipv4.udp_rmem_min={self.value}"
                def repr_runtime(self):
                    return self.__repr__()
                def repr_build_time(self):
                    return self.__repr__()

            class wmem_min(Option):
                """!@brief Minimal size of send buffer used by UDP sockets in moderation.
                udp_wmem_min - INTEGER
                	Each UDP socket is able to use the size for sending data, even if
                	total pages of UDP sockets exceed udp_mem pressure. The unit is byte.
                	Default: 4K
                """
                value_type = int
                @classmethod
                def supportedModes(cls) -> OptionMode:
                    return OptionMode.BUILD_TIME|OptionMode.RUN_TIME
                @classmethod
                def default(cls):
                    return 4000
                def __repr__(self):
                    return f"net.ipv4.udp_wmem_min={self.value}"
                def repr_runtime(self):
                    return self.__repr__()
                def repr_build_time(self):
                    return self.__repr__()

    class Tcp(BaseOptionGroup):
        '''
        #NOTE must be set on docker-host
        class mem(Option):
            """
            tcp_mem - vector of 3 INTEGERs: min, pressure, max
            	min: below this number of pages TCP is not bothered about its
            	memory appetite.

            	pressure: when amount of memory allocated by TCP exceeds this number
            	of pages, TCP moderates its memory consumption and enters memory
            	pressure mode, which is exited when memory consumption falls
            	under "min".

            	max: number of pages allowed for queueing by all TCP sockets.

            	Defaults are calculated at boot time from amount of available
            	memory.
            """
            value_type = tuple # (min,pressure,max) or better {'min': 4000, 'max': 32000 } ?!
            @classmethod
            def supportedModes(cls) -> OptionMode:
                return OptionMode.BUILD_TIME|OptionMode.RUN_TIME
            @classmethod
            def default(cls):
                return (91884, 122513, 183768)
            def __repr__(self):
                return f"net.ipv4.tcp_mem={self.value[0]} {self.value[1]} {self.value[2]}"
            def repr_runtime(self):
                return self.__repr__()
            def repr_build_time(self):
                return self.__repr__()
        '''
        class rmem(Option):
            """
            tcp_rmem - vector of 3 INTEGERs: min, default, max
            	min: Minimal size of receive buffer used by TCP sockets.
            	It is guaranteed to each TCP socket, even under moderate memory
            	pressure.
            	Default: 4K

            	default: initial size of receive buffer used by TCP sockets.
            	This value overrides net.core.rmem_default used by other protocols.
            	Default: 87380 bytes. This value results in window of 65535 with
            	default setting of tcp_adv_win_scale and tcp_app_win:0 and a bit
            	less for default tcp_app_win. See below about these variables.

            	max: maximal size of receive buffer allowed for automatically
            	selected receiver buffers for TCP socket. This value does not override
            	net.core.rmem_max.  Calling setsockopt() with SO_RCVBUF disables
            	automatic tuning of that socket's receive buffer size, in which
            	case this value is ignored.
            	Default: between 87380B and 6MB, depending on RAM size.
            """
            value_type = tuple # (min,default,max)
            @classmethod
            def supportedModes(cls) -> OptionMode:
                return OptionMode.BUILD_TIME|OptionMode.RUN_TIME
            @classmethod
            def default(cls):
                # (4096, 87380,)
                return (4096, 131072, 6291456)# again my laptop's values
            def __repr__(self):
                   return f'net.ipv4.tcp_rmem="{self.value[0]} {self.value[1]} {self.value[2]}"'

        class wmem(Option):
            """
            tcp_wmem - vector of 3 INTEGERs: min, default, max
            	min: Amount of memory reserved for send buffers for TCP sockets.
            	Each TCP socket has rights to use it due to fact of its birth.
            	Default: 4K

            	default: initial size of send buffer used by TCP sockets.  This
            	value overrides net.core.wmem_default used by other protocols.
            	It is usually lower than net.core.wmem_default.
            	Default: 16K

            	max: Maximal amount of memory allowed for automatically tuned
            	send buffers for TCP sockets. This value does not override
            	net.core.wmem_max.  Calling setsockopt() with SO_SNDBUF disables
            	automatic tuning of that socket's send buffer size, in which case
            	this value is ignored.
            	Default: between 64K and 4MB, depending on RAM size.
            """
            value_type = tuple# (min, default, max)
            @classmethod
            def supportedModes(cls) -> OptionMode:
                return OptionMode.BUILD_TIME|OptionMode.RUN_TIME
            @classmethod
            def default(cls):
                return (4096, 16384, 4194304)
            def __repr__(self):
                   return f'net.ipv4.tcp_wmem="{self.value[0]} {self.value[1]} {self.value[2]}"'

