# Interface 


I am putting some thoughts on APIs here. The actual API design goes to their corresponding documents (we have one document for each class).

## The Core Classes

For the AS, IXP, Network, Router, Host class, which are the core classes in the simulator, we should have the following APIs (the API names are not finalized). These APIs are mainly used by the ```Simulator``` class (internal APIs).

- ```createRouterDockerFiles```: for all that map to containers 
- ```createDockerComposeEntry```: for all that need to be added to ```docker-compose.yml``` (return string)
- ```createBirdConf_OSPF```: for routers only (return string)
- ```createBirdConf_BGP```: for BGP routers only (return string)


## Simulator

- ```build```: this API will build everything, including docker files, and docker-compose file. 