package ovs

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"

	log "github.com/sirupsen/logrus"
	"github.com/vishvananda/netlink"
)

const (
	dumpPortsRetries = 3
)

func patchName(a string, b string) string {
	name := patchPrefix + patchStr(a) + patchStr(b)
	if len(name) > 15 {
		panic(fmt.Errorf("%s too long for ifName", name))
	}
	return name
}

func parsePortDesc(output string, portDesc *map[OFPortType]string) {
	ofportNumberDump := regexp.MustCompile(`^\s*(\d+)\((\S+)\).+$`)
	for _, line := range strings.Split(string(output), "\n") {
		match := ofportNumberDump.FindAllStringSubmatch(line, -1)
		if len(match) > 0 {
			ofport, _ := ParseUint32(match[0][1])
			(*portDesc)[OFPortType(ofport)] = match[0][2]
		}
	}
}

func mustScrapePortDesc(bridgeName string, portDesc *map[OFPortType]string) {
	// Periodically OVS can falsely return:
	// "FAILED: [dump-ports-desc ovsbr-508ac], ovs-ofctl: ovsbr-508ac is not a bridge or a socket\n"
	// Handle just this call with a backoff/retry.
	var err error = nil
	for i := 0; i <= dumpPortsRetries; i++ {
		err = scrapePortDesc(bridgeName, portDesc)
		if err == nil {
			return
		}
		time.Sleep(time.Second * time.Duration(i+1))
	}
	panic(err)
}

func scrapePortDesc(bridgeName string, portDesc *map[OFPortType]string) error {
	output, err := OfCtl("dump-ports-desc", bridgeName)
	if err != nil {
		return err
	}
	parsePortDesc(output, portDesc)
	return nil
}

func (ovsdber *ovsdber) mustLowestFreePortOnBridge(bridgeName string) OFPortType {
	portDesc := make(map[OFPortType]string)
	mustScrapePortDesc(bridgeName, &portDesc)
	existingOfPorts := []int{}
	for ofport := range portDesc {
		existingOfPorts = append(existingOfPorts, int(ofport))
	}
	sort.Ints(existingOfPorts)
	log.Debugf("existing ports on %s: %+v", bridgeName, existingOfPorts)
	intLowestFreePort := 1
	for _, existingPort := range existingOfPorts {
		if existingPort != intLowestFreePort {
			break
		}
		intLowestFreePort++
	}
	return OFPortType(intLowestFreePort)
}

func (ovsdber *ovsdber) addInternalPort(bridgeName string, portName string, tag uint) (OFPortType, string, error) {
	lowestFreePort := ovsdber.mustLowestFreePortOnBridge(bridgeName)
	if tag != 0 {
		value, err := VsCtl("add-port", bridgeName, portName, fmt.Sprintf("tag=%u", tag), "--", "set", "Interface", portName, fmt.Sprintf("ofport_request=%d", lowestFreePort))
		return lowestFreePort, value, err
	}
	value, err := VsCtl("add-port", bridgeName, portName, "--", "set", "Interface", portName, fmt.Sprintf("ofport_request=%d", lowestFreePort))
	return lowestFreePort, value, err
}

func (ovsdber *ovsdber) mustAddInternalPort(bridgeName string, portName string, tag uint) (OFPortType, string) {
	lowestFreePort, value, err := ovsdber.addInternalPort(bridgeName, portName, tag)
	if err != nil {
		panic(err)
	}
	return lowestFreePort, value
}

func (ovsdber *ovsdber) mustAddPatchPort(bridgeName string, bridgeNamePeer string, port OFPortType, portPeer OFPortType) (OFPortType, OFPortType) {
	if port == 0 {
		port = ovsdber.mustLowestFreePortOnBridge(bridgeName)
	}
	if portPeer == 0 {
		portPeer = ovsdber.mustLowestFreePortOnBridge(bridgeNamePeer)
	}
	portName := patchName(bridgeName, bridgeNamePeer)
	portNamePeer := patchName(bridgeNamePeer, bridgeName)
	vethPair := netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{Name: portName},
		PeerName:  portNamePeer,
	}
	netlink.LinkAdd(&vethPair)
	netlink.LinkSetUp(&vethPair)
	vethPairPeer := netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{Name: portNamePeer},
		PeerName:  portName,
	}
	netlink.LinkSetUp(&vethPairPeer)
	_, _ = VsCtl("add-port", bridgeName, portName, "--", "set", "Interface", portName, fmt.Sprintf("ofport_request=%d", port))
	_, _ = VsCtl("add-port", bridgeNamePeer, portNamePeer, "--", "set", "Interface", portNamePeer, fmt.Sprintf("ofport_request=%d", portPeer))
	//_, err = VsCtl("set", "interface", portName, "type=patch")
	//_, err = VsCtl("set", "interface", portNamePeer, "type=patch")
	//_, err = VsCtl("set", "interface", portName, fmt.Sprintf("options:peer=%s", portNamePeer))
	//_, err = VsCtl("set", "interface", portNamePeer, fmt.Sprintf("options:peer=%s", portName))
	return port, portPeer
}

func (ovsdber *ovsdber) mustDeletePatchPort(bridgeName string, bridgeNamePeer string) {
	portName := patchName(bridgeName, bridgeNamePeer)
	portNamePeer := patchName(bridgeNamePeer, bridgeName)
	ovsdber.mustDeletePort(bridgeName, portName)
	ovsdber.mustDeletePort(bridgeNamePeer, portNamePeer)
	vethPair := netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{Name: portName},
		PeerName:  portNamePeer,
	}
	netlink.LinkDel(&vethPair)
}

func (ovsdber *ovsdber) mustDeletePort(bridgeName string, portName string) {
	log.Debugf("Remove %s from %s", portName, bridgeName)
	mustVsCtl("del-port", bridgeName, portName)
}

func (ovsdber *ovsdber) getOfPort(portName string) (OFPortType, error) {
	ofPort, err := ParseUint32(mustVsCtl("get", "Interface", portName, "ofport"))
	if err != nil {
		return OFPortType(0), err
	}
	return OFPortType(ofPort), nil
}

func (ovsdber *ovsdber) mustGetOfPort(portName string) OFPortType {
	ofPort, err := ovsdber.getOfPort(portName)
	if err != nil {
		panic(err)
	}
	return ofPort
}

func (ovsdber *ovsdber) addVxlanPort(bridgeName string, portName string, peerAddress string) (string, error) {
	// http://docs.openvswitch.org/en/latest/faq/vxlan/
	value, err := VsCtl("add-port", bridgeName, portName, "--", "set", "interface", portName, "type=vxlan", fmt.Sprintf("options:remote_ip=%s", peerAddress))
	return value, err
}
