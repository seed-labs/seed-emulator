package ovs

import (
	"fmt"
	"net"
	"strings"
	"time"

	log "github.com/sirupsen/logrus"
)

func (ovsdber *ovsdber) show() (string, error) {
	return VsCtl("show")
}

func (ovsdber *ovsdber) waitForOvs() {
	for i := 0; i < ovsStartupRetries; i++ {
		_, err := ovsdber.show()
		if err == nil {
			break
		}
		log.Infof("Waiting for open vswitch")
		time.Sleep(5 * time.Second)
	}
	_, err := ovsdber.show()
	if err != nil {
		panic(fmt.Errorf("could not connect to open vswitch"))
	}
	log.Infof("Connected to open vswitch")
}

func (ovsdber *ovsdber) ifUp(ifName string) bool {
	byNameInterface, err := net.InterfaceByName(ifName)
	if err != nil {
		return false
	}
	if strings.Contains(byNameInterface.Flags.String(), "up") {
		return true
	}
	return false
}

// checks if a bridge already exists
func (ovsdber *ovsdber) bridgeExists(bridgeName string) (string, error) {
	return VsCtl("br-exists", bridgeName)
}

// addBridge adds the OVS bridge
func (ovsdber *ovsdber) addBridge(bridgeName string) (string, error) {
	VsCtl("--if-exists", "del-br", bridgeName)
	return VsCtl("add-br", bridgeName, "--", "set", "Bridge", bridgeName, "stp_enable=false")
}

// addBridgeExists adds the OVS bridge or does nothing if it already exists
func (ovsdber *ovsdber) addBridgeExists(bridgeName string) (string, error) {
	return VsCtl("--may-exist", "add-br", bridgeName, "--", "set", "Bridge", bridgeName, "stp_enable=false")
}

func (ovsdber *ovsdber) mustDeleteBridge(bridgeName string) string {
	return mustVsCtl("del-br", bridgeName)
}

func (ovsdber *ovsdber) makeMirrorBridge(bridgeName string, mirrorBridgeOutPort OFPortType) {
	mustOfCtl("del-flows", bridgeName)
	mustOfCtl("add-flow", bridgeName, "priority=0,actions=drop")
	mustOfCtl("add-flow", bridgeName, fmt.Sprintf("priority=1,actions=output:%d", mirrorBridgeOutPort))
}

func (ovsdber *ovsdber) makeLoopbackBridge(bridgeName string) (err error) {
	err = nil
	defer func() {
		if rerr := recover(); rerr != nil {
			err = fmt.Errorf("cannot makeLoopbackBridge: %v", rerr)
		}
	}()

	mustOfCtl("del-flows", bridgeName)
	mustOfCtl("add-flow", bridgeName, "priority=0,actions=drop")
	mustOfCtl("add-flow", bridgeName, "priority=1,actions=output:in_port")
	return err
}

func (ovsdber *ovsdber) parseAddPorts(add_ports string, addPorts *map[string]OFPortType, addPortsAcls *map[OFPortType]string) {
	if add_ports == "" {
		return
	}
	for _, add_port_params_str := range strings.Split(add_ports, ",") {
		add_port_params := strings.Split(add_port_params_str, "/")
		add_port := add_port_params[0]
		(*addPorts)[add_port] = 0

		if len(add_port_params) >= 2 {
			port_no, err := ParseUint32(add_port_params[1])
			if err != nil {
				panic(err)
			}
			(*addPorts)[add_port] = OFPortType(port_no)
			if len(add_port_params) == 3 && addPortsAcls != nil {
				(*addPortsAcls)[OFPortType(port_no)] = add_port_params[2]
			}
		}
	}
}

func (ovsdber *ovsdber) createBridge(bridgeName string, controller string, dpid string, add_ports string, exists bool, userspace bool, ovsLocalMac string) error {
	if exists {
		if _, err := ovsdber.addBridgeExists(bridgeName); err != nil {
			log.Errorf("Error creating ovs bridge [ %s ] : [ %s ]", bridgeName, err)
			return err
		}
	} else {
		if _, err := ovsdber.addBridge(bridgeName); err != nil {
			log.Errorf("Error creating ovs bridge [ %s ] : [ %s ]", bridgeName, err)
			return err
		}
	}
	var ovsConfigCmds [][]string

	if userspace {
		ovsConfigCmds = append(ovsConfigCmds, []string{"set", "bridge", bridgeName, "datapath_type=netdev"})
	}

	if ovsLocalMac != "" {
		ovsConfigCmds = append(ovsConfigCmds, []string{"set", "bridge", bridgeName, fmt.Sprintf("other-config:hwaddr=\"%s\"", ovsLocalMac)})
	}

	if dpid != "" {
		ovsConfigCmds = append(ovsConfigCmds, []string{"set", "bridge", bridgeName, fmt.Sprintf("other-config:datapath-id=%s", dpid)})
	}

	if controller != "" {
		ovsConfigCmds = append(ovsConfigCmds, []string{"set", "bridge", bridgeName, "fail-mode=secure"})
		controllers := append([]string{"set-controller", bridgeName}, strings.Split(controller, ",")...)
		ovsConfigCmds = append(ovsConfigCmds, controllers)
	}

	addPorts := make(map[string]OFPortType)
	ovsdber.parseAddPorts(add_ports, &addPorts, nil)

	for add_port, number := range addPorts {
		if number > 0 {
			ovsConfigCmds = append(ovsConfigCmds, []string{"add-port", bridgeName, add_port, "--", "set", "Interface", add_port, fmt.Sprintf("ofport_request=%d", number)})
		} else {
			ovsConfigCmds = append(ovsConfigCmds, []string{"add-port", bridgeName, add_port})
		}
	}

	for _, cmd := range ovsConfigCmds {
		_, err := VsCtl(cmd...)
		if err != nil {
			// At least one bridge config failed, so delete the bridge.
			log.Errorf("bridge config of %s failed", bridgeName)
			VsCtl("del-br", bridgeName)
			return err
		}
	}

	for add_port := range addPorts {
		_, err := ovsdber.getOfPort(add_port)
		if err != nil {
			// At least one add port failed, so delete the bridge.
			log.Errorf("add port of %s failed", add_port)
			VsCtl("del-br", bridgeName)
			return err
		}
	}

	if controller != "" {
		// Delete default OVS switching flow(s)
		mustOfCtl("del-flows", bridgeName)
	}

	// Bring the bridge up
	err := interfaceUp(bridgeName)
	if err != nil {
		log.Warnf("Error enabling bridge: [ %s ]", err)
		VsCtl("del-br", bridgeName)
	}
	return err
}

// setup bridge, if bridge does not exist create it.
func (d *Driver) initBridge(ns NetworkState, controller string, dpid string, add_ports string, userspace bool, ovsLocalMac string) error {
	bridgeName := ns.BridgeName
	err := d.ovsdber.createBridge(bridgeName, controller, dpid, add_ports, false, userspace, ovsLocalMac)
	if err != nil {
		log.Errorf("Error creating bridge: %s", err)
		return err
	}
	if ns.Mode == modeNAT || ns.Mode == modeRouted {
		gatewayIP := ns.Gateway + "/" + ns.GatewayMask
		if err := setInterfaceIP(bridgeName, gatewayIP); err != nil {
			log.Debugf("Error assigning address: %s on bridge: %s with an error of: %s", gatewayIP, bridgeName, err)
		}

		// Validate that the IPAddress is there!
		_, err := getIfaceAddr(bridgeName)
		if err != nil {
			log.Fatalf("No IP address found on bridge %s", bridgeName)
			return err
		}

		// Add NAT rules for iptables
		if ns.Mode == modeNAT {
			if err = natOut(gatewayIP, "-I"); err != nil {
				log.Fatalf("Could not set NAT rules for bridge %s because %v", bridgeName, err)
				return err
			}
		}
	}
	return nil
}
