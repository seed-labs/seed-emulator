FROM golang:1.22 AS build
LABEL maintainer="Charlie Lewis <clewis@iqt.org>"
COPY . /go/src/dovesnap
WORKDIR /go/src/dovesnap
RUN go build -o /out/dovesnap .
FROM ubuntu:22.04
COPY --from=build /out/dovesnap /
RUN apt-get update && apt-get install -y --no-install-recommends \
    iptables dbus && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
RUN update-alternatives --set iptables /usr/sbin/iptables-legacy
RUN apt-get update && apt-get install -y --no-install-recommends \
    ethtool iproute2 \
    openvswitch-common \
    openvswitch-switch \
    udhcpc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
COPY udhcpclog.sh /udhcpclog.sh
ENTRYPOINT ["/dovesnap"]
