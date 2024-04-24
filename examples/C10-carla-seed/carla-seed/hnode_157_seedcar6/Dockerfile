FROM 98a2693c996c2294358552f48373498d
ARG DEBIAN_FRONTEND=noninteractive
# Install software-properties-common to easily add new repositories
RUN apt-get update && \
    apt-get install -y software-properties-common

# Add the deadsnakes PPA for newer Python versions
RUN add-apt-repository -y ppa:deadsnakes/ppa

# Now that the PPA is added, install Python 3.7
RUN apt-get update && \
    apt-get install -y python3.7 python3-pip python3.7-distutils
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 1
RUN python3.7 -m pip install --upgrade pip
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
COPY d18858afc6bb66ec3a19d872077acfd2 /seedemu_sniffer
COPY 17ac2d812a99a91e7f747e1defb72a29 /seedemu_worker
COPY automatic_control/agents/ /carla/agents/
COPY automatic_control/get_car_info.py /carla/get_car_info.py
COPY automatic_control/headless_automatic_control.py /carla/headless_automatic_control.py
COPY automatic_control/requirements.txt /carla/requirements.txt
RUN chmod +x /start.sh
RUN chmod +x /seedemu_sniffer
RUN chmod +x /seedemu_worker
RUN chmod +x /carla/headless_automatic_control.py
RUN chmod +x /carla/get_car_info.py
RUN pip3.7 install --no-cache-dir -r /carla/requirements.txt
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
COPY 6a1e5579ad5a86c362c6aae90c32215e /tmp/etc-hosts
CMD ["/start.sh"]

