# Naming Conventions


We need to give each entity of the simulator a name. These names are not only for program's internal uses, they are also to name the container. When users see the name, they should immediately know the purpose of the container. Therefore, names must be meaningful and easy to recognize. That means we need to encode meaningful information in the names. Here is the current naming conventions. We may need to make changes in the future. We define the template here, so if we need to change the naming convention, this is the only place that we need to change. ***We should never hardcode the naming scheme in the rest of the code***.  

```
class SimConstants:
    ASNAME = 'as{1}'                # For autonomous system
    IXNAME = 'ix{1}'                # For internet exchange 
    ASNETNAME = 'net_as{1}'         # For the network inside an AS
    IXNETNAME = 'net_ix{1}'         # For the network inside an IXP

    # For BGP router; argument 1: AS number; argument 2: AS number
    BGPRouterNAME = 'rt_as{1}_ix{2}'

    # For router server; argument: AS number
    RSNAME = 'rs_ix{1}'            

    # For host; argument 1: AS name; argument 2: host index
    HOSTNAME = 'host_{1}_{2}'        

    # For host with special tag (e.g. DNS). The third argument is the tag
    HOSTNAMEWITHTAG = 'host_{1}_{2}_{3}' 
```