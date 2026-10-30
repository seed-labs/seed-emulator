FROM handsonsecurity/seedemu-base:2.0

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends software-properties-common gpg-agent
RUN add-apt-repository ppa:cz.nic-labs/bird
RUN apt-get update && apt-get install -y --no-install-recommends bird2