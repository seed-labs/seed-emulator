package ovs

import (
	"fmt"

	"github.com/docker/libnetwork/iptables"
)

func mustIptablesRaw(args ...string) []byte {
	output, err := iptables.Raw(args...)
	if err != nil {
		panic(err)
	}
	return output
}

// TODO: reconcile with what libnetwork does and port mappings
func natOut(cidr string, op string) error {
	masquerade := []string{
		"POSTROUTING", "-t", "nat",
		"-s", cidr,
		"-j", "MASQUERADE",
	}
	incl := append([]string{op}, masquerade...)
	if output, err := iptables.Raw(incl...); err != nil {
		return err
	} else if len(output) > 0 {
		return &iptables.ChainError{
			Chain:  "POSTROUTING",
			Output: output,
		}
	}
	_, err := iptables.Raw("-P", "FORWARD", "ACCEPT")
	return err
}

func mustPortMap(op string, bridgeName string, ipProto string, gatewayIP string, hostIP string, hostPort string, port string) {
	dst := fmt.Sprintf("%s:%s", hostIP, port)
	mustIptablesRaw("-t", "nat", op, "DOCKER", "-p", ipProto, "-d", gatewayIP, "--dport", hostPort, "-j", "DNAT", "--to-destination", dst)
	mustIptablesRaw("-t", "nat", op, "OUTPUT", "-p", ipProto, "-d", gatewayIP, "--dport", hostPort, "-j", "DNAT", "--to-destination", dst)
	mustIptablesRaw("-t", "nat", op, "POSTROUTING", "-p", ipProto, "-s", hostIP, "-d", hostIP, "--dport", port, "-j", "MASQUERADE")
	mustIptablesRaw("-t", "filter", op, "DOCKER", "!", "-i", bridgeName, "-o", bridgeName, "-p", "tcp", "-d", hostIP, "--dport", port, "-j", "ACCEPT")
}

func mustAddGatewayPortMap(bridgeName string, ipProto string, gatewayIP string, hostIP string, hostPort string, port string) {
	mustPortMap("-A", bridgeName, ipProto, gatewayIP, hostIP, hostPort, port)
}

func mustDeleteGatewayPortMap(bridgeName string, ipProto string, gatewayIP string, hostIP string, hostPort string, port string) {
	mustPortMap("-D", bridgeName, ipProto, gatewayIP, hostIP, hostPort, port)
}
