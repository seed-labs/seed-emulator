# Instructions for building your docker images locally

Since sometimes pulling docker images from remote docker hub is pretty slow while pulling from local docker hub is much faster, we recommend you to build your docker images locally.

We have provided all the necessary Dockerfile and docker-compose files to build your docker images locally.

Please enter the corrosponding folder and use command line to build your docker images.

For instance, if you want to build the docker image for the multiarch base image in our emulator, please enter the folder `docker_images/multiarch/seedemu-base` and use command line:

```bash
docker build -t handsonsecurity/seedemu-multiarch-base:buildx-latest .
```

This will build the docker image for the multiarch base image in your local docker hub, which will first be accessed instead of the remote docker hub when we pull the image `handsonsecurity/seedemu-multiarch-base:buildx-latest`.

According to our test, you can just build two images, `handsonsecurity/seedemu-multiarch-base:buildx-latest` and `handsonsecurity/seedemu-multiarch-router:buildx-latest`.