FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

# Common for both host and router
RUN apt-get update \
    && apt-get -y install \
          iputils-ping \
          iproute2  \
          net-tools \
          curl \
          nano \
          mtr-tiny
      #   vim-nox \

# Specific for router
RUN apt-get -y install bird 
