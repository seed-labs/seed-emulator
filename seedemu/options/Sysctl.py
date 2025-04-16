from seedemu.core import BaseOptionGroup, Option, OptionMode, OptionDomain


class SysctlOpts(BaseOptionGroup):
# NOTE: the classname is dynamically changed to just 'sysctl' so the
# nested option names don't become too lengthy...

    domain = OptionDomain.NODE

    class NetIpv4(BaseOptionGroup):
        domain = OptionDomain.NODE

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
            domain = OptionDomain.NODE
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

