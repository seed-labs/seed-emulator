FROM handsonsecurity/seedemu-multiarch-base:buildx-latest

ARG DEBIAN_FRONTEND=noninteractive

RUN mkdir -p /usr/share/doc/bird2/examples/
RUN touch /usr/share/doc/bird2/examples/bird.conf
RUN apt-get update && apt-get install -y --no-install-recommends bird2
