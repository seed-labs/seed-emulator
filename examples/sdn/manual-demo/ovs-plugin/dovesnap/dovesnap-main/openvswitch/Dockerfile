FROM debian:bookworm-slim as builder
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates make autoconf wget gcc git libc6-dev python3-dev openssl
WORKDIR /
ENV OVS_VERSION 3.2.2
RUN wget https://www.openvswitch.org/releases/openvswitch-$OVS_VERSION.tar.gz && \
 tar -xzvf openvswitch-$OVS_VERSION.tar.gz && \
 mv openvswitch-$OVS_VERSION openvswitch
WORKDIR /openvswitch
RUN ./configure && make -j "$(nproc)" && make install
RUN mkdir -p /usr/local/var/run/openvswitch

FROM debian:bookworm-slim
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip python3 python3-setuptools git supervisor openssl \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local /usr/local
# Configure supervisord
RUN mkdir -p /var/log/supervisor/
COPY supervisord.conf /etc/
COPY configure-ovs.sh /usr/local/share/openvswitch
RUN mkdir -p /etc/openvswitch
# Create the database
RUN ovsdb-tool create /etc/openvswitch/conf.db /usr/local/share/openvswitch/vswitch.ovsschema
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
HEALTHCHECK --interval=30s --timeout=5s CMD ovs-vsctl show
