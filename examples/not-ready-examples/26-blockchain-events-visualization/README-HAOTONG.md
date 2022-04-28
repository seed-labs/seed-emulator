# Visualization

## Preparation for launching 

### Emulator Building

- Go to the PoA manual execution example and follow the README file to build the emulator.

### Client: docker-compose.yml

- Overview: To send and receive data, the client container must attach the network to the internet and use the relevant router as routing. We need to do this because the client container is built separately. As a result, we need to do an additional two configurations. 

- Configuration 1: Modify the `docker-compose.yml` in the `/seed-emulator/client/` folder

  - ```dockerfile
    version: "3"
    
    services:
        seedemu-client:
            build: .
            container_name: seedemu_client
            volumes:
                - /var/run/docker.sock:/var/run/docker.sock
            ports:
                - 8080:8080
    #the information below is new added
            cap_add:
                - ALL
            sysctls:
                - net.ipv4.ip_forward=1
                - net.ipv4.conf.default.rp_filter=0
                - net.ipv4.conf.all.rp_filter=0
            privileged: true
            networks:
            		#emulator_net_3_net3 is a demo, please read info below to find a useful one in your network
                emulator_net_3_net3:
                		# 10.3.3.99 is a demo, please read info below to find a useful one in your network
                    ipv4_address: 10.3.3.99
    networks:
        emulator_net_3_net3:
            external: true
    ```

    - The way to find the `emulator_net_3_net3` in your network
      
      
  
- Configuration 2: Add routing at the client container (Config1 must be finished before beginning config2)

  - Step1: Use cmd `docker ps | grep client` to find the client container id

    - Suppose we get `9155befoiqjwiogj` as the client container id.

  - Step 2: Use cmd `docker exec -it \<your container id> bash` to enter the terminal of the client container.

    - Using the example in step1, the cmd will be `docker exec -it 9155bef bash.`

  - Step 3: Use the cmd below to re-create the routing

    - ```
      $:ip route show
      #You will see an entry for a default route
      $:ip route del default
      #Delete this default route
      $:ip route add default via <ip>
      #the ip of the BGP router in the map. Any packet that doesn't match other routing rules will be routed by default to this new ip you provide.
      $:ip route show
      ```

      - The way to find the `\<ip>`above
        
        

## Launching the project

- In POA consensus
  - Step1: finish all steps in preparation for launching
  - Step2: type the cmd `start newBlockHeaders` in the block button
  - Step3: use cmd `sudo su` to change the account to superuser and run the script named `5_send_transaction.sh`
    - Wait a few minutes; you will see the signer container flash purple.
      - ![](./images/newBH-Flash.png)
  - Step4: type the cmd `start pendingTransactions` in the block button
  - Step5: use cmd `sudo su` to change the account to superuser and run the script named `5_send_transaction.sh`
    - Wait a few minutes; the pending transaction container will flash orange.
      - ![](./images/pendTr-Flash.png)
- In POW consensus
  - Step1: finish all steps in preparation for launching
  - Step2: type the cmd `start newBlockHeaders` in the block button
    - Wait a few minutes, which depends on the miner number, speed, and your machine performance. And you will see miner container will flash purple.
      - ![](./images/newBH-Flash.png)
  - Step3: type the cmd `start pendingTransactions` in the block button
  - Step4: use cmd `sudo su` to change the account to superuser and run the script named `5_send_transaction.sh`
    - Wait a few minutes; the pending transaction container will flash orange.
      - ![](./images/pendTr-Flash.png)

## Client Design

- Overview:
  - The whole project is divided into two parts: frontend and backend. Frontend takes charge of user input and graph drawing using the data from backend, and the the backend process the user input and send back the drawing data to frontend.
- Frontend: 
  - Take the user input
  - Send the user input to the backend
  - Receive the drawing cmd from backend to re-draw the map
- Backend:
  - Receive the user input from frontend
  - Use plugin-type architecture to process the user input
    - We can now create a new plugin for different projects that fetch data from the emulator and passes it to the frontend
  - Send drawing data back to frontend
- Drawing Data Exchange standard
  - According to the `vis.js` documents, the node's color, shape, border and size can be changed. For the flashing purpose, we select the color, border as the exchange standard.
    - Node color's example
      - https://visjs.github.io/vis-network/examples/static/jsfiddle.aec0f22e3d245b3c6f85d183374a64aa5350c42ea32e60a09a1ca6cca89a99f3.html
    - Node shape's example
      - https://visjs.github.io/vis-network/examples/static/jsfiddle.5ee8db0327d36431ab286eacdfc731eaaef45d4d9d1da85b42a093b51f2525fc.html

## Implementation of Client Design



## Standard Test

- After type the `start newBlockHeaders`, the data from backend to frontend should contain the usable container ID.
- After type the `start pendingTransactions`, the data from backend to frontend should contain the usable container ID.

## Future Work

- The visulization work of other project should also follow the design of blockchain plugin.