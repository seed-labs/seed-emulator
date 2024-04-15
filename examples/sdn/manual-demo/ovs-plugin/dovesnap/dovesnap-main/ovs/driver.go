package ovs

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net"
	"net/http"
	"os"
	"os/exec"
	"reflect"
	"strings"
	"sync"
	"time"

	"github.com/docker/docker/api/types"
	networkplugin "github.com/docker/go-plugins-helpers/network"
	log "github.com/sirupsen/logrus"
)

type OFPortType uint32
type OFVidType uint32

type ContainerState struct {
	Name       string
	Id         string
	OFPort     OFPortType
	MacAddress string
	HostIP     string
	Labels     map[string]string
	IfName     string
}

type ExternalPortState struct {
	Name       string
	OFPort     OFPortType
	MacAddress string
}

type OtherBridgePortState struct {
	Name           string
	PeerName       string
	OFPort         OFPortType
	PeerOFPort     OFPortType
	PeerBridgeName string
}

type DynamicNetworkState struct {
	ShortEngineId    string
	Containers       map[string]ContainerState
	ExternalPorts    map[string]ExternalPortState
	OtherBridgePorts map[string]OtherBridgePortState
}

type NetworkState struct {
	NetworkName          string
	BridgeName           string
	BridgeDpid           string
	BridgeDpidUint       uint64
	BridgeVLAN           uint
	MTU                  uint
	PreAllocatePorts     uint
	Mode                 string
	AddPorts             string
	AddCoproPorts        string
	Gateway              string
	GatewayMask          string
	FlatBindInterface    string
	UseDHCP              bool
	Userspace            bool
	NATAcl               string
	VLANOutAcl           string
	DefaultAcl           string
	OvsLocalMac          string
	Controller           string
	DynamicNetworkStates DynamicNetworkState
}

type DovesnapOpReply struct {
	NewNetworkState    NetworkState
	NewOFPortContainer OFPortContainer
	NetworkStateString string
}

type DovesnapOp struct {
	Operation            string
	NewNetworkState      NetworkState
	NewStackMirrorConfig StackMirrorConfig
	AddPorts             string
	AddCoproPorts        string
	Mode                 string
	NetworkID            string
	EndpointID           string
	Options              map[string]interface{}
	OFPort               OFPortType
	Reply                chan DovesnapOpReply
}

type NotifyMsg struct {
	NetworkState NetworkState
	Type         string
	Operation    string
	Details      map[string]string
}

type NotifyMsgJson struct {
	Version uint
	Time    int64
	Msg     NotifyMsg
}

type StackingPort struct {
	OFPort     OFPortType
	RemoteDP   string
	RemotePort OFPortType
}

type OFPortContainer struct {
	OFPort           OFPortType
	containerInspect types.ContainerJSON
	udhcpcCmd        *exec.Cmd
	Options          map[string]interface{}
}

type Driver struct {
	dockerer
	faucetconfrpcer
	ovsdber
	resourceManagerWG       sync.WaitGroup
	createDeleteNetworkWG   sync.WaitGroup
	stackPriority1          string
	stackingInterfaces      []string
	stackMirrorInterface    []string
	stackDefaultControllers string
	mirrorBridgeIn          string
	mirrorBridgeOut         string
	lastDhcpMtime           time.Time
	shortEngineId           string
	mirrorBridgeName        string
	loopbackBridgeName      string
	stackDpName             string
	networks                map[string]NetworkState
	stackMirrorConfigs      map[string]StackMirrorConfig
	dovesnapOpChan          chan DovesnapOp
	notifyMsgChan           chan NotifyMsg
	authIPs                 []net.IPNet
}

const (
	chanSize = 64
)

func (d *Driver) createLoopbackBridge() error {
	_, err := d.ovsdber.addBridgeExists(d.loopbackBridgeName)
	if err != nil {
		return err
	}
	err = d.ovsdber.makeLoopbackBridge(d.loopbackBridgeName)
	if err != nil {
		return err
	}
	return nil
}

func (d *Driver) createMirrorBridge() {
	_, err := d.ovsdber.bridgeExists(d.mirrorBridgeName)
	if err == nil {
		log.Debugf("mirror bridge already exists")
		return
	}
	log.Debugf("creating mirror bridge with output interface %s", d.mirrorBridgeOut)
	add_ports := d.mirrorBridgeOut
	if len(d.mirrorBridgeIn) > 0 {
		add_ports += "," + d.mirrorBridgeIn
		log.Debugf("adding mirror bridge input from %s", d.mirrorBridgeIn)
	}
	err = d.ovsdber.createBridge(d.mirrorBridgeName, "", "", add_ports, true, false, "")
	if err != nil {
		panic(err)
	}
	d.ovsdber.makeMirrorBridge(d.mirrorBridgeName, d.ovsdber.mustGetOfPort(d.mirrorBridgeOut))
}

func (d *Driver) createStackingBridge() error {
	hostname, dpid, intDpid, dpName := d.mustGetStackBridgeConfig()
	if d.stackDefaultControllers == "" {
		panic(fmt.Errorf("default OF controllers must be defined for stacking"))
	}

	// check if the stacking bridge already exists
	_, err := d.ovsdber.bridgeExists(dpName)
	if err == nil {
		log.Debugf("Stacking bridge already exists for this host")
		return nil
	} else {
		log.Infof("Stacking bridge doesn't exist, creating one now")
	}

	err = d.ovsdber.createBridge(dpName, d.stackDefaultControllers, dpid, "", true, false, "")
	if err != nil {
		log.Errorf("Unable to create stacking bridge because: [ %s ]", err)
	}

	// loop through stacking interfaces
	stackingPorts := []StackingPort{}
	remoteStackingConfig := ""
	for _, stackingInterface := range d.stackingInterfaces {
		remoteDP, remotePort, localInterface := d.mustGetStackingInterface(stackingInterface)

		ofPort, _ := d.mustAddInternalPort(dpName, localInterface, 0)
		stackConfig := ""
		if d.stackPriority1 == remoteDP {
			stackConfig = "stack: {priority: 1},"
		}
		remoteStackingConfig += fmt.Sprintf("%s: {%s interfaces: {%s}},",
			remoteDP, stackConfig, d.faucetconfrpcer.stackInterfaceYaml(remotePort, dpName, ofPort))
		stackingPorts = append(stackingPorts, StackingPort{RemoteDP: remoteDP, RemotePort: remotePort, OFPort: ofPort})
	}

	localStackingConfig := ""
	for _, stackingPort := range stackingPorts {
		localStackingConfig += d.faucetconfrpcer.stackInterfaceYaml(
			stackingPort.OFPort, stackingPort.RemoteDP, stackingPort.RemotePort)
	}
	localStackingConfig = d.faucetconfrpcer.mergeDpInterfacesYaml(
		dpName, intDpid, "Dovesnap Stacking Bridge for "+hostname, localStackingConfig, false)
	stackingConfig := fmt.Sprintf("{dps: {%s %s}}", localStackingConfig, remoteStackingConfig)

	d.faucetconfrpcer.mustSetFaucetConfigFile(stackingConfig)
	return nil
}

func (d *Driver) CreateNetwork(r *networkplugin.CreateNetworkRequest) (err error) {
	log.Debugf("Create network request: %+v", r)
	return d.ReOrCreateNetwork(r, "create")
}

func (d *Driver) InitBridge(ns NetworkState, sc StackMirrorConfig) {
	ports := []string{}
	if ns.AddPorts != "" {
		ports = append(ports, ns.AddPorts)
	}
	if ns.AddCoproPorts != "" {
		ports = append(ports, ns.AddCoproPorts)
	}
	all_added_ports := strings.Join(ports, ",")
	if err := d.initBridge(ns, ns.Controller, ns.BridgeDpid, all_added_ports, ns.Userspace, ns.OvsLocalMac); err != nil {
		panic(err)
	}
	if usingMirrorBridge(d) {
		log.Debugf("configuring mirror bridge port for %s", ns.BridgeName)
		d.mustAddPatchPort(ns.BridgeName, d.mirrorBridgeName, sc.LbPort, 0)
		mirrorPortName := patchName(d.mirrorBridgeName, ns.BridgeName)
		mirrorOfPort := d.ovsdber.mustGetOfPort(mirrorPortName)
		flowStr := fmt.Sprintf("priority=2,in_port=%d,dl_vlan=0xffff,actions=mod_vlan_vid:%d,output:1", mirrorOfPort, ns.BridgeVLAN)
		mustOfCtl("add-flow", d.mirrorBridgeName, flowStr)
	}
	if usingStacking(d) {
		d.mustAddPatchPort(ns.BridgeName, d.stackDpName, 0, 0)
	}
	if usingStackMirroring(d) {
		d.mustAddPatchPort(ns.BridgeName, d.loopbackBridgeName, sc.LbPort, 0)
	}
}

func (d *Driver) ReOrCreateNetwork(r *networkplugin.CreateNetworkRequest, operation string) (err error) {
	err = nil
	defer func() {
		if rerr := recover(); rerr != nil {
			err = fmt.Errorf("cannot create network: %v", rerr)
		}
	}()

	bridgeName := mustGetBridgeName(r)
	mtu := mustGetBridgeMTU(r)
	preAllocatePorts := mustGetPreAllocatePorts(r)
	mode := mustGetBridgeMode(r)
	bindInterface := mustGetBindInterface(r)
	controller := mustGetBridgeController(r)
	if controller == "" {
		controller = d.stackDefaultControllers
	}
	dpid := mustGetBridgeDpid(r)
	vlan := mustGetBridgeVLAN(r)
	add_ports := mustGetBridgeAddPorts(r)
	add_copro_ports := mustGetBridgeAddCoproPorts(r)
	gateway, mask := mustGetGatewayIP(r)
	useDHCP := mustGetUseDHCP(r)
	useUserspace := mustGetUserspace(r)
	natAcl := mustGetNATAcl(r)
	ovsLocalMac := mustGetOvsLocalMac(r)
	vlanOutAcl := mustGetBridgeVLANOutAcl(r)
	defaultAcl := mustGetDefaultAcl(r)

	if useDHCP {
		if mode != "flat" {
			panic(fmt.Errorf("network must be flat when DHCP in use"))
		}
		if gateway != "" {
			panic(fmt.Errorf("network must not have IP config when DHCP in use"))
		}
		if !mustGetInternalOption(r) {
			panic(fmt.Errorf("network must be internal when DHCP in use"))
		}
	}

	// TODO: Frustratingly, when docker creates a network, it doesn't tell us the network's name.
	// We have to look that up with docker inspect. But we can't inspect a network, that
	// hasn't been created yet. If we had a way to get the network's name at creation time
	// that would resolve a lot of error handling cases.
	ns := NetworkState{
		BridgeName:           bridgeName,
		BridgeDpid:           dpid,
		BridgeDpidUint:       mustGetUintFromHexStr(dpid),
		BridgeVLAN:           vlan,
		MTU:                  mtu,
		PreAllocatePorts:     preAllocatePorts,
		Mode:                 mode,
		AddPorts:             add_ports,
		AddCoproPorts:        add_copro_ports,
		Gateway:              gateway,
		GatewayMask:          mask,
		FlatBindInterface:    bindInterface,
		UseDHCP:              useDHCP,
		Userspace:            useUserspace,
		NATAcl:               natAcl,
		VLANOutAcl:           vlanOutAcl,
		DefaultAcl:           defaultAcl,
		OvsLocalMac:          ovsLocalMac,
		Controller:           controller,
		DynamicNetworkStates: makeDynamicNetworkState(d.shortEngineId),
	}

	// Validate add_ports/add_copro_ports if present.
	addPorts := make(map[string]OFPortType)
	addPortsAcls := make(map[OFPortType]string)
	d.ovsdber.parseAddPorts(ns.AddPorts, &addPorts, &addPortsAcls)
	d.ovsdber.parseAddPorts(ns.AddCoproPorts, &addPorts, &addPortsAcls)
	stackMirrorConfig := d.getStackMirrorConfig(r)

	if operation == "create" {
		d.InitBridge(ns, stackMirrorConfig)
	}

	mustSetInterfaceMTU(ns.BridgeName, ns.MTU)

	createMsg := DovesnapOp{
		NewNetworkState:      ns,
		NewStackMirrorConfig: stackMirrorConfig,
		AddPorts:             ns.AddPorts,
		AddCoproPorts:        ns.AddCoproPorts,
		Mode:                 ns.Mode,
		NetworkID:            r.NetworkID,
		EndpointID:           ns.BridgeName,
		Operation:            operation,
	}

	d.createDeleteNetworkWG.Add(1)
	d.dovesnapOpChan <- createMsg
	return err
}

func (d *Driver) DeleteNetwork(r *networkplugin.DeleteNetworkRequest) error {
	log.Debugf("Delete network request: %+v", r)
	deleteMsg := DovesnapOp{
		NetworkID: r.NetworkID,
		Operation: "delete",
		Reply:     make(chan DovesnapOpReply, 2),
	}

	d.createDeleteNetworkWG.Add(1)
	d.dovesnapOpChan <- deleteMsg
	<-deleteMsg.Reply
	return nil
}

func (d *Driver) CreateEndpoint(r *networkplugin.CreateEndpointRequest) (*networkplugin.CreateEndpointResponse, error) {
	log.Debugf("Create endpoint request: %+v", r)
	localVethPair := vethPair(truncateID(r.EndpointID))
	addVethPair(localVethPair)
	vethName := localVethPair.PeerName
	macAddress := r.Interface.MacAddress
	if macAddress == "" {
		// No MAC address requested, we provide our own.
		macAddress = getMacAddr(vethName)
	} else {
		mustSetInterfaceMac(vethName, macAddress)
		// We accept Docker's request.
		macAddress = ""
	}
	reservePortMsg := DovesnapOp{
		NetworkID:  r.NetworkID,
		EndpointID: r.EndpointID,
		Operation:  "reserveport",
		Reply:      make(chan DovesnapOpReply, 2),
	}
	d.dovesnapOpChan <- reservePortMsg
	res := &networkplugin.CreateEndpointResponse{
		Interface: &networkplugin.EndpointInterface{MacAddress: macAddress},
	}
	log.Debugf("Create endpoint response: %+v", res)
	return res, nil
}

func (d *Driver) GetCapabilities() (*networkplugin.CapabilitiesResponse, error) {
	log.Debugf("Get capabilities request")
	res := &networkplugin.CapabilitiesResponse{
		Scope: "local",
	}
	return res, nil
}

func (d *Driver) ProgramExternalConnectivity(r *networkplugin.ProgramExternalConnectivityRequest) error {
	log.Debugf("Program external connectivity request: %+v", r)
	return nil
}

func (d *Driver) RevokeExternalConnectivity(r *networkplugin.RevokeExternalConnectivityRequest) error {
	log.Debugf("Revoke external connectivity request: %+v", r)
	return nil
}

func (d *Driver) FreeNetwork(r *networkplugin.FreeNetworkRequest) error {
	log.Debugf("Free network request: %+v", r)
	return nil
}

func (d *Driver) DiscoverNew(r *networkplugin.DiscoveryNotification) error {
	log.Debugf("Discover new request: %+v", r)
	return nil
}

func (d *Driver) DiscoverDelete(r *networkplugin.DiscoveryNotification) error {
	log.Debugf("Discover delete request: %+v", r)
	return nil
}

func (d *Driver) DeleteEndpoint(r *networkplugin.DeleteEndpointRequest) error {
	log.Debugf("Delete endpoint request: %+v", r)
	return nil
}

func (d *Driver) AllocateNetwork(r *networkplugin.AllocateNetworkRequest) (*networkplugin.AllocateNetworkResponse, error) {
	log.Debugf("Allocate network request: %+v", r)
	res := &networkplugin.AllocateNetworkResponse{
		Options: make(map[string]string),
	}
	return res, nil
}

func (d *Driver) EndpointInfo(r *networkplugin.InfoRequest) (*networkplugin.InfoResponse, error) {
	res := &networkplugin.InfoResponse{
		Value: make(map[string]string),
	}
	return res, nil
}

func (d *Driver) Join(r *networkplugin.JoinRequest) (*networkplugin.JoinResponse, error) {
	log.Debugf("Join endpoint request %+v", r)
	d.createDeleteNetworkWG.Wait()
	ns := d.networks[r.NetworkID]
	localVethPair := vethPair(truncateID(r.EndpointID))
	joinMsg := DovesnapOp{
		NetworkID:  r.NetworkID,
		EndpointID: r.EndpointID,
		Options:    r.Options,
		Operation:  "join",
	}
	d.dovesnapOpChan <- joinMsg
	res := &networkplugin.JoinResponse{
		InterfaceName: networkplugin.InterfaceName{
			// SrcName gets renamed to DstPrefix + ID on the container iface
			SrcName:   localVethPair.PeerName,
			DstPrefix: containerEthName,
		},
		Gateway: ns.Gateway,
	}
	log.Debugf("Join endpoint response %+v", r)
	return res, nil
}

func (d *Driver) Leave(r *networkplugin.LeaveRequest) error {
	log.Debugf("Leave request: %+v", r)
	leaveMsg := DovesnapOp{
		NetworkID:  r.NetworkID,
		EndpointID: r.EndpointID,
		Operation:  "leave",
		Reply:      make(chan DovesnapOpReply, 2),
	}
	d.dovesnapOpChan <- leaveMsg
	<-leaveMsg.Reply
	return nil
}

func (d *Driver) mustDeleteBridgeAndPorts(bridgeName string) {
	if usingMirrorBridge(d) {
		d.mustDeletePatchPort(bridgeName, d.mirrorBridgeName)
	}

	if usingStacking(d) {
		d.mustDeletePatchPort(bridgeName, d.stackDpName)
		if usingStackMirroring(d) {
			d.mustDeletePatchPort(bridgeName, d.loopbackBridgeName)
		}
	}

	d.mustDeleteBridge(bridgeName)
}

func mustHandleDeleteNetwork(d *Driver, opMsg DovesnapOp) {
	defer func() {
		if rerr := recover(); rerr != nil {
			log.Errorf("mustHandleDeleteNetwork failed: %v", rerr)
		}
		d.createDeleteNetworkWG.Done()
	}()

	// remove the bridge from the faucet config if it exists
	ns := d.networks[opMsg.NetworkID]
	log.Infof("Deleting network ID %s bridge %s", opMsg.NetworkID, ns.BridgeName)

	d.faucetconfrpcer.mustDeleteDp(ns.NetworkName)

	if ns.Mode == modeNAT {
		gatewayIP := ns.Gateway + "/" + ns.GatewayMask
		if err := natOut(gatewayIP, "-D"); err != nil {
			log.Fatalf("Could not delete NAT rules for bridge %s because %v", ns.BridgeName, err)
			panic(err)
		}
	}

	d.mustDeleteBridgeAndPorts(ns.BridgeName)

	delete(d.networks, opMsg.NetworkID)
	delete(d.stackMirrorConfigs, opMsg.NetworkID)

	opMsg.Reply <- DovesnapOpReply{}

	d.notifyMsgChan <- NotifyMsg{
		Type:         "NETWORK",
		Operation:    "DELETE",
		NetworkState: ns,
	}
}

func getExternalPortState(ifName string, ofPort OFPortType) ExternalPortState {
	return ExternalPortState{Name: ifName, OFPort: ofPort, MacAddress: getMacAddr(ifName)}
}

func mustHandleCreateNetwork(d *Driver, opMsg DovesnapOp) {
	defer func() {
		if rerr := recover(); rerr != nil {
			log.Errorf("mustHandleCreateNetwork failed: %v", rerr)
		}
		d.createDeleteNetworkWG.Done()
	}()

	log.Debugf("network ID: %s", opMsg.NetworkID)
	netInspect := d.dockerer.mustGetNetworkInspectFromID(opMsg.NetworkID)
	inspectNs, err := getNetworkStateFromResource(&netInspect, d.shortEngineId)
	if err != nil {
		panic(err)
	}

	ns := opMsg.NewNetworkState
	d.stackMirrorConfigs[opMsg.NetworkID] = opMsg.NewStackMirrorConfig
	ns.NetworkName = inspectNs.NetworkName
	d.networks[opMsg.NetworkID] = ns
	egressPipeline := false
	if ns.VLANOutAcl != "" {
		egressPipeline = true
	}

	add_ports := opMsg.AddPorts
	add_interfaces := ""
	addPortsAcls := make(map[OFPortType]string)
	if add_ports != "" {
		addPorts := make(map[string]OFPortType)
		d.ovsdber.parseAddPorts(add_ports, &addPorts, &addPortsAcls)
		for add_port := range addPorts {
			ofPort := d.ovsdber.mustGetOfPort(add_port)
			add_interfaces += d.faucetconfrpcer.vlanInterfaceYaml(ofPort, "Physical interface "+add_port, ns.BridgeVLAN, "")
			ns.DynamicNetworkStates.ExternalPorts[add_port] = getExternalPortState(add_port, ofPort)
		}
	}
	add_copro_ports := opMsg.AddCoproPorts
	if add_copro_ports != "" {
		addPorts := make(map[string]OFPortType)
		d.ovsdber.parseAddPorts(add_copro_ports, &addPorts, &addPortsAcls)
		for add_port := range addPorts {
			ofPort := d.ovsdber.mustGetOfPort(add_port)
			add_interfaces += d.faucetconfrpcer.coproInterfaceYaml(ofPort, "Physical interface "+add_port, "vlan_vid")
			ns.DynamicNetworkStates.ExternalPorts[add_port] = getExternalPortState(add_port, ofPort)
		}
	}
	nextPrePort := d.ovsdber.mustLowestFreePortOnBridge(ns.BridgeName)
	defaultAcl := ""
	if len(ns.DefaultAcl) > 0 {
		defaultAcl = getStrForNetwork(ns.DefaultAcl, ns.NetworkName)
	}
	for prePort := uint(0); prePort < ns.PreAllocatePorts; prePort++ {
		log.Debugf("preallocating port %d on %s", nextPrePort, ns.NetworkName)
		add_interfaces += d.faucetconfrpcer.vlanInterfaceYaml(nextPrePort, "preallocated port", ns.BridgeVLAN, defaultAcl)
		nextPrePort += 1
	}
	mode := opMsg.Mode
	if mode == "nat" || mode == "routed" {
		netAcl := getStrForNetwork(ns.NATAcl, ns.NetworkName)
		// TODO: consider the bridge port to be always up - determine why OVS doesn't always update us with port status.
		add_interfaces += d.faucetconfrpcer.localVlanInterfaceYaml(ofPortLocal, "OVS Port default gateway", ns.BridgeVLAN, netAcl)
		ns.DynamicNetworkStates.ExternalPorts[inspectNs.BridgeName] = getExternalPortState(inspectNs.BridgeName, ofPortLocal)
	}
	if usingMirrorBridge(d) {
		log.Debugf("configuring mirror bridge port for %s", ns.BridgeName)
		stackMirrorConfig := d.stackMirrorConfigs[opMsg.NetworkID]
		mirrorPortName := patchName(ns.BridgeName, d.mirrorBridgeName)
		peerMirrorPortName := patchName(d.mirrorBridgeName, ns.BridgeName)
		ofPort := stackMirrorConfig.LbPort
		peerOfPort := d.mustGetOfPort(peerMirrorPortName)
		add_interfaces += fmt.Sprintf("%d: {description: mirror, output_only: true},", ofPort)
		ns.DynamicNetworkStates.OtherBridgePorts[mirrorPortName] = OtherBridgePortState{
			Name: mirrorPortName, PeerName: peerMirrorPortName, OFPort: ofPort, PeerOFPort: peerOfPort, PeerBridgeName: d.mirrorBridgeName}
	}
	configYaml := d.faucetconfrpcer.mergeSingleDpYaml(
		ns.NetworkName, ns.BridgeDpidUint, "OVS Bridge "+ns.BridgeName, add_interfaces, egressPipeline)
	if usingStacking(d) {
		ofPortName := patchName(ns.BridgeName, d.stackDpName)
		peerOfPortName := patchName(d.stackDpName, ns.BridgeName)
		ofPort := d.mustGetOfPort(ofPortName)
		peerOfPort := d.mustGetOfPort(peerOfPortName)
		ns.DynamicNetworkStates.OtherBridgePorts[ofPortName] = OtherBridgePortState{
			Name: ofPortName, PeerName: peerOfPortName, OFPort: ofPort, PeerOFPort: peerOfPort, PeerBridgeName: d.stackDpName}
		localDpYaml := d.faucetconfrpcer.mergeDpInterfacesYaml(ns.NetworkName, ns.BridgeDpidUint, "OVS Bridge "+ns.BridgeName,
			add_interfaces+d.faucetconfrpcer.stackInterfaceYaml(ofPort, d.stackDpName, peerOfPort), egressPipeline)
		remoteDpYaml := fmt.Sprintf("%s: {interfaces: {%s}}",
			d.stackDpName,
			d.faucetconfrpcer.stackInterfaceYaml(peerOfPort, ns.NetworkName, ofPort))
		configYaml = fmt.Sprintf("{dps: {%s %s}}", localDpYaml, remoteDpYaml)
	}
	d.faucetconfrpcer.mustSetFaucetConfigFile(configYaml)
	vlanOutAcl := getStrForNetwork(ns.VLANOutAcl, ns.NetworkName)
	if vlanOutAcl != "" {
		d.faucetconfrpcer.mustSetVlanOutAcl(fmt.Sprintf("%d", ns.BridgeVLAN), vlanOutAcl)
	}
	if usingStackMirroring(d) {
		stackMirrorConfig := d.stackMirrorConfigs[opMsg.NetworkID]
		d.faucetconfrpcer.mustSetRemoteMirrorPort(
			ns.NetworkName,
			stackMirrorConfig.LbPort,
			stackMirrorConfig.TunnelVid,
			stackMirrorConfig.RemoteDpName,
			stackMirrorConfig.RemoteMirrorPort,
		)
	}
	for port_no, acls := range addPortsAcls {
		networkAcls := getStrForNetwork(acls, ns.NetworkName)
		if networkAcls != "" {
			d.faucetconfrpcer.mustSetPortAcl(ns.NetworkName, port_no, networkAcls)
		}
	}
	d.notifyMsgChan <- NotifyMsg{
		Type:         "NETWORK",
		Operation:    "CREATE",
		NetworkState: ns,
	}
}

func mustGetPortMap(portMapRaw interface{}) (string, string, string) {
	portMap := portMapRaw.(map[string]interface{})
	hostPort := fmt.Sprintf("%d", int(portMap["HostPort"].(float64)))
	port := fmt.Sprintf("%d", int(portMap["Port"].(float64)))
	ipProtoName := "tcp"
	ipProto := int(portMap["Proto"].(float64))
	if ipProto == 17 {
		ipProtoName = "udp"
	}
	return hostPort, port, ipProtoName
}

func mustHandleGetNetwork(d *Driver, opMsg DovesnapOp) {
	reply := DovesnapOpReply{}

	defer func() {
		if rerr := recover(); rerr != nil {
			log.Errorf("mustHandleGetNetwork failed: %v", rerr)
		}
		opMsg.Reply <- reply
	}()
	ns := d.networks[opMsg.NetworkID]
	reply = DovesnapOpReply{
		NewNetworkState: ns,
	}
}

func mustHandleReservePort(d *Driver, opMsg DovesnapOp, OFPorts *map[string]OFPortContainer) {
	defer func() {
		if rerr := recover(); rerr != nil {
			log.Errorf("mustHandleReservePort failed: %v", rerr)
		}
	}()
	ns := d.networks[opMsg.NetworkID]
	localVethPair := vethPair(truncateID(opMsg.EndpointID))
	vethName := localVethPair.Name
	ofPort, _ := d.mustAddInternalPort(ns.BridgeName, vethName, 0)
	(*OFPorts)[opMsg.EndpointID] = OFPortContainer{OFPort: ofPort}
}

func mustHandleJoinContainer(d *Driver, opMsg DovesnapOp, OFPorts *map[string]OFPortContainer) {
	defer func() {
		if rerr := recover(); rerr != nil {
			log.Errorf("mustHandleJoinContainer failed: %v", rerr)
		}
	}()

	ofPort := (*OFPorts)[opMsg.EndpointID].OFPort
	ns := d.networks[opMsg.NetworkID]

	log.Debugf("about to inspect %+v on %+v", opMsg.EndpointID, ns)
	containerInspect, err := d.dockerer.getContainerFromEndpoint(opMsg.NetworkID, opMsg.EndpointID)
	if err != nil {
		panic(err)
	}
	pid := containerInspect.State.Pid
	containerNetSettings := containerInspect.NetworkSettings.Networks[ns.NetworkName]
	macAddress := containerNetSettings.MacAddress

	createNsLink(pid, containerInspect.ID)
	defaultInterface := "eth0"

	macPrefix, mok := containerInspect.Config.Labels["dovesnap.faucet.mac_prefix"]
	if mok && len(macPrefix) > 0 {
		oldMacAddress := macAddress
		macAddress := mustPrefixMAC(macPrefix, macAddress)
		log.Infof("mapping MAC from %s to %s using prefix %s", oldMacAddress, macAddress, macPrefix)
		output, err := exec.Command("ip", "netns", "exec", containerInspect.ID, "ip", "link", "set", defaultInterface, "address", macAddress).CombinedOutput()
		log.Debugf("%s", output)
		if err != nil {
			panic(err)
		}
	}
	if ns.Userspace {
		output, err := exec.Command("ip", "netns", "exec", containerInspect.ID, "/sbin/ethtool", "-K", defaultInterface, "tx", "off").CombinedOutput()
		log.Debugf("%s", output)
		if err != nil {
			panic(err)
		}
	}

	log.Infof("Adding %s (pid %d) MAC %s on %s DPID %d OFPort %d to Faucet",
		containerInspect.Name, pid, macAddress, ns.BridgeName, ns.BridgeDpidUint, ofPort)
	log.Debugf("container network settings: %+v", containerNetSettings)

	log.Debugf("%+v", opMsg.Options[portMapOption])
	hostIP := containerNetSettings.IPAddress
	gatewayIP := containerNetSettings.Gateway

	// Regular docker uses docker proxy, to listen on the configured port and proxy them into the container.
	// dovesnap doesn't get to use docker proxy, so we listen on the configured port on the network's gateway instead.
	for _, portMapRaw := range opMsg.Options[portMapOption].([]interface{}) {
		log.Debugf("adding portmap %+v", portMapRaw)
		hostPort, port, ipProto := mustGetPortMap(portMapRaw)
		mustAddGatewayPortMap(ns.BridgeName, ipProto, gatewayIP, hostIP, hostPort, port)
	}

	portAcl := ""
	portAcl, ok := containerInspect.Config.Labels["dovesnap.faucet.portacl"]
	defaultAcl := ns.DefaultAcl
	if ok && len(portAcl) > 0 {
		portAcl = getStrForNetwork(portAcl, ns.NetworkName)
		if portAcl != "" {
			log.Infof("Set portacl %s on %s", portAcl, containerInspect.Name)
		}
	} else if len(defaultAcl) > 0 {
		portAcl = getStrForNetwork(defaultAcl, ns.NetworkName)
		if defaultAcl != "" {
			log.Infof("set default portacl %s on %s", portAcl, containerInspect.Name)
		}
	}
	add_interfaces := d.faucetconfrpcer.vlanInterfaceYaml(
		ofPort, fmt.Sprintf("%s %s", containerInspect.Name, truncateID(containerInspect.ID)), ns.BridgeVLAN, portAcl)

	d.faucetconfrpcer.mustSetFaucetConfigFile(d.faucetconfrpcer.mergeSingleDpMinimalYaml(
		ns.NetworkName, add_interfaces))

	mirror, ok := containerInspect.Config.Labels["dovesnap.faucet.mirror"]
	if ok && parseBool(getStrForNetwork(mirror, ns.NetworkName)) {
		log.Infof("Mirroring container %s", containerInspect.Name)
		stackMirrorConfig := d.stackMirrorConfigs[opMsg.NetworkID]
		if usingStackMirroring(d) || usingMirrorBridge(d) {
			d.faucetconfrpcer.mustAddPortMirror(ns.NetworkName, ofPort, stackMirrorConfig.LbPort)
		}
	}

	udhcpcCmd := exec.Command("ip", "netns", "exec", containerInspect.ID, "/sbin/udhcpc", "-f", "-R", "-i", defaultInterface, "-s", "/udhcpclog.sh")
	udhcpcCmd.Env = os.Environ()
	udhcpcCmd.Env = append(udhcpcCmd.Env, fmt.Sprintf("CONTAINER_ID=%s", containerInspect.ID))
	if ns.UseDHCP {
		err = udhcpcCmd.Start()
		if err != nil {
			panic(err)
		}
		log.Infof("started udhcpc for %s", containerInspect.ID)
	} else {
		udhcpcCmd = nil
	}
	containerMap := OFPortContainer{
		OFPort:           ofPort,
		containerInspect: containerInspect,
		udhcpcCmd:        udhcpcCmd,
		Options:          opMsg.Options,
	}
	(*OFPorts)[opMsg.EndpointID] = containerMap
	ns.DynamicNetworkStates.Containers[opMsg.EndpointID] = ContainerState{
		Name:       containerInspect.Name,
		Id:         containerInspect.ID,
		OFPort:     ofPort,
		HostIP:     hostIP,
		MacAddress: macAddress,
		Labels:     containerInspect.Config.Labels,
		IfName:     defaultInterface,
	}

	d.notifyMsgChan <- NotifyMsg{
		Type:         "CONTAINER",
		Operation:    "JOIN",
		NetworkState: ns,
		Details: map[string]string{
			"name": containerInspect.Name,
			"id":   containerInspect.ID,
			"port": fmt.Sprintf("%d", ofPort),
			"mac":  macAddress,
			"ip":   hostIP,
		},
	}
}

func mustHandleLeaveContainer(d *Driver, opMsg DovesnapOp, OFPorts *map[string]OFPortContainer) {
	defer func() {
		if rerr := recover(); rerr != nil {
			log.Errorf("mustHandleLeaveContainer failed: %v", rerr)
		}
		opMsg.Reply <- DovesnapOpReply{}
	}()

	containerMap, ok := (*OFPorts)[opMsg.EndpointID]
	if !ok {
		panic(fmt.Errorf("endpoint %s was not Join()d", opMsg.EndpointID))
	}

	udhcpcCmd := containerMap.udhcpcCmd
	if udhcpcCmd != nil {
		log.Infof("Shutting down udhcpc")
		udhcpcCmd.Process.Kill()
		udhcpcCmd.Wait()
	}

	portID := fmt.Sprintf(ovsPortPrefix + truncateID(opMsg.EndpointID))
	ofPort := d.ovsdber.mustGetOfPort(portID)
	// Must delete veth for the endpoint here - DeleteEndpoint happens before leave container,
	// so we must the delete here to be able to remove the port sucessfully.
	localVethPair := vethPair(truncateID(opMsg.EndpointID))
	delVethPair(localVethPair)

	ns := d.networks[opMsg.NetworkID]
	d.ovsdber.mustDeletePort(ns.BridgeName, portID)
	d.faucetconfrpcer.mustDeleteDpInterface(ns.NetworkName, ofPort)

	containerNetSettings := containerMap.containerInspect.NetworkSettings.Networks[ns.NetworkName]
	hostIP := containerNetSettings.IPAddress
	gatewayIP := containerNetSettings.Gateway
	for _, portMapRaw := range containerMap.Options[portMapOption].([]interface{}) {
		hostPort, port, ipProto := mustGetPortMap(portMapRaw)
		mustDeleteGatewayPortMap(ns.BridgeName, ipProto, gatewayIP, hostIP, hostPort, port)
	}

	delete(*OFPorts, opMsg.EndpointID)
	delete(ns.DynamicNetworkStates.Containers, opMsg.EndpointID)
	deleteNsLink(containerMap.containerInspect.ID)

	d.notifyMsgChan <- NotifyMsg{
		Type:         "CONTAINER",
		Operation:    "LEAVE",
		NetworkState: ns,
		Details: map[string]string{
			"name": containerMap.containerInspect.Name,
			"id":   containerMap.containerInspect.ID,
			"port": fmt.Sprintf("%d", ofPort),
		},
	}
}

func reconcileDhcpIp(d *Driver) {
	stat, err := os.Stat(fmt.Sprintf("%s/udhcpc.updated", dhcpStatePath))
	if err != nil {
		return
	}
	mtime := stat.ModTime()
	if mtime == d.lastDhcpMtime {
		return
	}
	d.lastDhcpMtime = mtime
	for _, ns := range d.networks {
		if !ns.UseDHCP {
			continue
		}
		for containerid, container := range ns.DynamicNetworkStates.Containers {
			ipFile := fmt.Sprintf("%s/%s-ipv4.txt", dhcpStatePath, container.Id)
			content, err := ioutil.ReadFile(ipFile)
			if err != nil {
				continue
			}
			container.HostIP = strings.Trim(string(content), " \n")
			ns.DynamicNetworkStates.Containers[containerid] = container
			log.Infof("HostIP for %s updated: %s", container.Id, container.HostIP)
		}
	}
}

func reconcileOvs(d *Driver, allPortDesc *map[string]map[OFPortType]string) {
	for id, ns := range d.networks {
		stackMirrorConfig := d.stackMirrorConfigs[id]
		newPortDesc := make(map[OFPortType]string)
		err := scrapePortDesc(ns.BridgeName, &newPortDesc)
		if err != nil {
			log.Warnf("scrape of port-desc for %s failed, will retry", ns.BridgeName)
			continue
		}
		addPorts := make(map[string]OFPortType)
		d.ovsdber.parseAddPorts(ns.AddPorts, &addPorts, nil)
		d.ovsdber.parseAddPorts(ns.AddCoproPorts, &addPorts, nil)

		portDesc, have_port_desc := (*allPortDesc)[id]
		if have_port_desc {
			if reflect.DeepEqual(newPortDesc, portDesc) {
				continue
			}
			log.Debugf("portDesc for %s updated", ns.BridgeName)

			for ofPort, desc := range portDesc {
				_, have_new_port_desc := newPortDesc[ofPort]
				if have_new_port_desc {
					continue
				}
				// Ignore container ports
				if strings.HasPrefix(desc, ovsPortPrefix) {
					continue
				}
				log.Infof("removing non dovesnap port: %s %s %d %s", id, ns.BridgeName, ofPort, desc)
				d.faucetconfrpcer.mustDeleteDpInterface(ns.NetworkName, OFPortType(ofPort))
				delete(ns.DynamicNetworkStates.ExternalPorts, desc)
			}
		} else {
			log.Debugf("new portDesc for %s", ns.BridgeName)
		}

		add_interfaces := ""

		for ofPort, desc := range newPortDesc {
			// Ignore NAT and mirror port
			if ofPort == ofPortLocal || ofPort == stackMirrorConfig.LbPort {
				continue
			}
			// Ignore container and patch ports.
			if strings.HasPrefix(desc, ovsPortPrefix) || strings.HasPrefix(desc, patchPrefix) {
				continue
			}
			// Skip ports that were added at creation time.
			_, have_add_port := addPorts[desc]
			if have_add_port {
				continue
			}
			log.Infof("adding non dovesnap port: %s %s %d %s", id, ns.BridgeName, ofPort, desc)
			add_interfaces += d.faucetconfrpcer.vlanInterfaceYaml(ofPort, "Physical interface "+desc, ns.BridgeVLAN, "")
			ns.DynamicNetworkStates.ExternalPorts[desc] = getExternalPortState(desc, ofPort)
		}

		if add_interfaces != "" {
			configYaml := d.faucetconfrpcer.mergeSingleDpMinimalYaml(
				ns.NetworkName, add_interfaces)
			d.faucetconfrpcer.mustSetFaucetConfigFile(configYaml)
		}

		(*allPortDesc)[id] = newPortDesc
	}
}

func getRemoteIp(r *http.Request) net.IP {
	var possibleIPs = []string{r.Header.Get("X-REAL-IP"), r.Header.Get("X-FORWARDED-FOR"), r.RemoteAddr}
	for _, possibleIP := range possibleIPs {
		for _, hostPort := range strings.Split(possibleIP, ",") {
			ip, _, err := net.SplitHostPort(hostPort)
			if err != nil {
				continue
			}
			netIP := net.ParseIP(ip)
			if netIP != nil {
				return netIP
			}
		}
	}
	return nil
}

func isAuthIP(requestIP net.IP, authIPs []net.IPNet) bool {
	for _, authIP := range authIPs {
		if authIP.Contains(requestIP) {
			return true
		}
	}
	return false
}

func mustHandleNetworks(d *Driver, opMsg DovesnapOp) {
	encodedMsg, err := json.Marshal(d.networks)
	if err != nil {
		panic(err)
	}
	opMsg.Reply <- DovesnapOpReply{NetworkStateString: fmt.Sprintf("%s", encodedMsg)}
}

func (d *Driver) resourceManager() {
	defer d.resourceManagerWG.Done()

	// TODO: make all the mustHandle() hooks, be able to cleanly retry on a failure at any point
	// E.g. a transient OVS DB or faucetconfrpc error.
	OFPorts := make(map[string]OFPortContainer)
	AllPortDesc := make(map[string]map[OFPortType]string)
	serial := uint64(0)

	for {
		select {
		case opMsg := <-d.dovesnapOpChan:
			serial += 1
			log.Debugf("resourceManager() pending %d, received serial %d, %+v", len(d.dovesnapOpChan), serial, opMsg)
			switch opMsg.Operation {
			case "recreatebadbridge":
				d.mustDeleteBridgeAndPorts(opMsg.EndpointID)
				d.InitBridge(opMsg.NewNetworkState, opMsg.NewStackMirrorConfig)
				mustHandleCreateNetwork(d, opMsg)
			case "recreatedownbridge":
				mustHandleDeleteNetwork(d, opMsg)
				d.InitBridge(opMsg.NewNetworkState, opMsg.NewStackMirrorConfig)
				mustHandleCreateNetwork(d, opMsg)
			case "create":
				mustHandleCreateNetwork(d, opMsg)
			case "delete":
				mustHandleDeleteNetwork(d, opMsg)
			case "join":
				mustHandleJoinContainer(d, opMsg, &OFPorts)
			case "leave":
				mustHandleLeaveContainer(d, opMsg, &OFPorts)
			case "reserveport":
				mustHandleReservePort(d, opMsg, &OFPorts)
			case "getnetwork":
				mustHandleGetNetwork(d, opMsg)
			case "networks":
				reconcileOvs(d, &AllPortDesc)
				reconcileDhcpIp(d)
				mustHandleNetworks(d, opMsg)
			case "quit":
				log.Infof("processed quit")
				return
			default:
				log.Errorf("Unknown resource manager message: %s", opMsg)
			}
			log.Debugf("resourceManager() completed serial %d, %+v", serial, opMsg)
		case <-time.After(time.Second * 3):
			reconcileOvs(d, &AllPortDesc)
			reconcileDhcpIp(d)
		}
	}
}

func usingMirrorBridge(d *Driver) bool {
	return len(d.mirrorBridgeOut) != 0
}

func usingStacking(d *Driver) bool {
	return !usingMirrorBridge(d) && len(d.stackingInterfaces[0]) != 0
}

func usingStackMirroring(d *Driver) bool {
	return usingStacking(d) && len(d.stackMirrorInterface) > 1
}

func (d *Driver) notifier() {
	for {
		select {
		case notifyMsg := <-d.notifyMsgChan:
			log.Debugf("%+v", notifyMsg)
			encodedMsg, err := json.Marshal(NotifyMsgJson{
				Version: 1,
				Time:    time.Now().Unix(),
				Msg:     notifyMsg,
			})
			if err != nil {
				panic(err)
			}
			// TODO: emit to UDS
			log.Infof(fmt.Sprintf("%s", encodedMsg))
		}
	}
}

func (d *Driver) restoreNetworks() {
	netlist := d.dockerer.mustGetNetworkList()
	for id := range netlist {
		netInspect := d.dockerer.mustGetNetworkInspectFromID(id)
		ns, err := getNetworkStateFromResource(&netInspect, d.shortEngineId)
		if err != nil {
			panic(err)
		}
		// TODO: verify dovesnap was restarted with the same arguments when restoring existing networks.
		sc := d.getStackMirrorConfigFromResource(&netInspect)
		d.stackMirrorConfigs[id] = sc
		log.Infof("restoring network %+v, %+v %+v", ns, sc, netInspect)
		if ns.Controller == "" {
			ns.Controller = d.stackDefaultControllers
		}
		createMsg := DovesnapOp{
			NewNetworkState:      ns,
			NewStackMirrorConfig: sc,
			AddPorts:             ns.AddPorts,
			Mode:                 ns.Mode,
			NetworkID:            id,
			EndpointID:           ns.BridgeName,
			Operation:            "create",
		}
		// We need to recover from two different scenarios where OVS may be in a bad state.
		if d.ovsdber.ifUp(ns.BridgeName) {
			_, err := getIfaceAddr(ns.BridgeName)
			/// OVS config seems to be in place, bridge is up, but it is missing its IP config.
			if err != nil {
				log.Errorf("Bridge interface %s exists but IP address is missing, recreating network", ns.BridgeName)
				createMsg.Operation = "recreatebadbridge"
			}
		} else {
			// OVS config seems to be in place, but the bridge interface is down.
			log.Errorf("Bridge interface %s exists but is down, recreating network", ns.BridgeName)
			createMsg.Operation = "recreatedownbridge"
		}
		d.createDeleteNetworkWG.Add(1)
		d.dovesnapOpChan <- createMsg
	}
	d.createDeleteNetworkWG.Wait()
}

func (d *Driver) getWebResponse(w http.ResponseWriter, operation string) {
	requestMsg := DovesnapOp{
		Operation: operation,
		Reply:     make(chan DovesnapOpReply, 2),
	}
	d.dovesnapOpChan <- requestMsg
	reply := <-requestMsg.Reply
	fmt.Fprintf(w, reply.NetworkStateString)
}

func (d *Driver) handleNetworksWeb(w http.ResponseWriter, r *http.Request) {
	remoteIP := getRemoteIp(r)
	authIP := isAuthIP(remoteIP, d.authIPs)
	log.Debugf(fmt.Sprintf("web request from %s, authorized %v", remoteIP, authIP))
	if authIP {
		d.getWebResponse(w, "networks")
	} else {
		fmt.Fprintf(w, "not authorized")
	}
}

func (d *Driver) runWeb(port int) {
	http.HandleFunc("/networks", d.handleNetworksWeb)

	if err := http.ListenAndServe(fmt.Sprintf(":%d", port), nil); err != nil {
		panic(err)
	}
}

func (d *Driver) Quit() {
	quitMsg := DovesnapOp{
		Operation: "quit",
	}
	d.dovesnapOpChan <- quitMsg
	d.resourceManagerWG.Wait()
}

func NewDriver(flagFaucetconfrpcClientName string, flagFaucetconfrpcServerName string, flagFaucetconfrpcServerPort int, flagFaucetconfrpcKeydir string, flagFaucetconfrpcConnRetries int, flagStackPriority1 string, flagStackingInterfaces string, flagStackMirrorInterface string, flagDefaultControllers string, flagMirrorBridgeIn string, flagMirrorBridgeOut string, flagStatusServerPort int, flagStatusAuthIPs string) *Driver {
	log.Infof("Initializing dovesnap")
	ensureDirExists(netNsPath)

	stack_mirror_interface := strings.Split(flagStackMirrorInterface, ":")
	if len(flagStackMirrorInterface) > 0 && len(stack_mirror_interface) != 2 {
		panic(fmt.Errorf("invalid stack mirror interface config: %s", flagStackMirrorInterface))
	}
	stacking_interfaces := strings.Split(flagStackingInterfaces, ",")
	log.Debugf("Stacking interfaces: %v", stacking_interfaces)

	d := &Driver{
		dockerer:                dockerer{},
		ovsdber:                 ovsdber{},
		faucetconfrpcer:         faucetconfrpcer{},
		stackPriority1:          flagStackPriority1,
		stackingInterfaces:      stacking_interfaces,
		stackMirrorInterface:    stack_mirror_interface,
		stackDefaultControllers: flagDefaultControllers,
		mirrorBridgeIn:          flagMirrorBridgeIn,
		mirrorBridgeOut:         flagMirrorBridgeOut,
		lastDhcpMtime:           time.Unix(0, 0),
		networks:                make(map[string]NetworkState),
		stackMirrorConfigs:      make(map[string]StackMirrorConfig),
		dovesnapOpChan:          make(chan DovesnapOp, chanSize),
		notifyMsgChan:           make(chan NotifyMsg, chanSize),
	}

	for _, authIP := range strings.Split(flagStatusAuthIPs, ",") {
		_, ipnet, err := net.ParseCIDR(authIP)
		if err != nil {
			panic(err)
		}
		d.authIPs = append(d.authIPs, *ipnet)
	}

	d.dockerer.mustGetDockerClient()
	d.shortEngineId = d.dockerer.mustGetShortEngineID()
	d.mirrorBridgeName = d.mustGetMirrorBrName()
	d.loopbackBridgeName = d.mustGetLoopbackBrName()
	d.stackDpName = d.mustGetStackDPName()
	d.faucetconfrpcer.mustGetGRPCClient(
		flagFaucetconfrpcClientName,
		flagFaucetconfrpcServerName,
		flagFaucetconfrpcServerPort,
		flagFaucetconfrpcKeydir,
		flagFaucetconfrpcConnRetries)

	d.ovsdber.waitForOvs()

	go d.notifier()

	if usingMirrorBridge(d) {
		d.createMirrorBridge()
	}

	if usingStacking(d) {
		stackerr := d.createStackingBridge()
		if stackerr != nil {
			panic(stackerr)
		}
		if usingStackMirroring(d) {
			lberr := d.createLoopbackBridge()
			if lberr != nil {
				panic(lberr)
			}
		}
	} else {
		log.Warnf("No stacking interface defined, not stacking DPs or creating a stacking bridge")
	}

	d.resourceManagerWG.Add(1)
	go d.resourceManager()

	d.restoreNetworks()

	go d.runWeb(flagStatusServerPort)

	return d
}
