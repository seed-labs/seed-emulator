### Demo System Manual

# Step 1: Start the Demo container

1. Build docker image: run `DOCKER_BUILDKIT=0 docker compose build` 
2. Start the container: run `docker compose up`
3. Access the demo site: `http://<host_ip>:5050`, where the IP address
   is the host machine's IP address. If you run the browser on the host
   machine, use `localhost` will be fine.   

# Step 2: Set up the Demo  

1. Go to `yesterday_once_more/setup_backend`, follow the instructions in `README.md`
   to set up the backend.

2. Go to `yesterday_once_more/setup_frontend`, follow the instructions in `README.md`
   to set up the frontend. 
