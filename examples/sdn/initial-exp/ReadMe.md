# This experiment will create a small SDN network(sdn0) in the Autonomous System (AS-150)

## Steps to recreate the result
1. Go to `seed-emulator` directory
2. Run this command to prepare python environment to run seed-emulator.
    ```
    source development.env
    ```
3. Go to the directory `seed-emulator/examples/sdn/initial-exp`
    ```
    cd seed-emulator/examples/sdn/initial-exp
    ```
4. Start the emulation of the small sdn network.

    ```
    dcdown && docker-compose up --remove-orphans
    ```
    Caveats: I ran the emulation on an arm-machine. Hence, I used the `seed-ubuntu:large-arm`. If you're running the emulation on an x86 machine, you need to replace `seed-ubuntu:large-arm` with `seed-ubuntu:large`.

5. Build the emulation for mini-internet.
    ```
    python3 mini-internet-with-sdn.py
    ```
<!-- Some caveats, If you're running on a x86 machine, you need to uncomment  -->

6. Go to output directory and start the emulation of mini-internet. 
    ```
    cd output && dcdown && docker-compose up --remove-orphans
    ```
7. After all the docker-cotainers are up, go the the parent directory (`initial-exp`) run the `demo-bgp.sh` script.
    ```
    cd .. && ./demo-bgp.sh
    ```
8. At this stage both the sdn network and regular mini-internet is ready. But you need to configure the BGP router of as-150 to peer with the bgp router of sdn. 
    ```
    docksh as150r-router0-10.150.0.254
    vim /etc/bird.bird.conf
    ```
    (a) In the config file add sdn0 interface to the direct local_nets protocol. This is basically including the sdn network in the autonomus system. 

    ```
    protocol direct local_nets {
        ipv4 {
            table t_direct;
            import all;
        };
        interface "net0";
    }
    ``` 
    So, direct local_nets protocol now looks like this: 
    ```
    protocol direct local_nets {
        ipv4 {
            table t_direct;
            import all;
        };
        interface "net0", "sdn0";
    }
    ```
    (b) Add a bgp protocol to peer with the bgp router of sdn controller. Include this at the end of the config file.
    ```
    protocol bgp faucet {
        ipv4 {
            export all;
            import all;
        };
        local 10.150.1.254 as 150;
        neighbor 10.150.1.253 port 9179 as 65000;
    }
    ```
    (c) restart the bird router to reload the config 
    ```
    birdc
    birdc> graceful restart
    bird
    ```

9. At this stage, your autonomous system AS-150 has two networks: `net0 (regular network: 10.150.0.0/24)` and `sdn0 (sdn network: 10.150.1.0/24)`. Network topology is:

