# SCION Emulator Tools

- `scion-output-checker`: a tool to validate if the output of the SEED-Docker Compiler constitutes a viable SCION topology that will actually run.
    This tool can save you a lot of time building misconfigured docker images that when run will yield a dysfunctional emulation.
    It is especially useful for developers who might want to tinker around with the SCION routing layers or DataProviders/Generators and need a test for their changes.

    So far it can detect the following common configuration errors:
     - mismatch  between topology.json and docker-compose.yml file regarding local border-router IP addresses in local-net as well as IX nets.
     - deviation of topology.json for nodes within the same AS

    TODO:
    - border router config .toml 
        - [general].id matches service(node) and directory 
        - TOML router name is element of topology.json 'border_routers'
    - check that each AS has control service and is actually reachable by hosts
    - check LinkTypes (when router A has 'PARENT' (and a node of remote AS B has already been encountered so its topology.json is known) retrieve AS B's config and check that link type is indeed the converse i.e.  'CHILD')

**Usage:** ```   ./scion-coutput-checker << path-to-SEED-output ( top dir containing  docker-compose.yml) >>  ```