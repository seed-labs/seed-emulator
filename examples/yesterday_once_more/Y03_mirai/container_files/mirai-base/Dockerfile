FROM handsonsecurity/seedemu-multiarch-base:buildx-latest
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3.8-distutils\
        python3 \
        python3-pip \
        wget \
        net-tools \
        python3-dev \
        python3-distutils \
        build-essential \
        curl \
        git \
        unzip \
        hping3 \
        && rm -rf /var/lib/apt/lists/*

RUN pip3 install telnetlib3==1.0.4
# RUN pip3 install py-cryptonight
RUN pip3 install mss==5.0.0
RUN pip3 install WMI==1.4.9
RUN pip3 install numpy
RUN pip3 install pyxhook==1.0.0
RUN pip3 install twilio==6.35.4
RUN pip3 install colorama==0.4.3
RUN pip3 install requests==2.22.0
RUN pip3 install PyInstaller
RUN pip3 install pycryptodome==3.9.6
RUN pip3 install pycrypto==2.6.1


