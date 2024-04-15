package ovs

import (
	"context"
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"io/ioutil"
	"strconv"
	"time"

	"github.com/iqtlabs/faucetconfrpc/faucetconfserver"
	log "github.com/sirupsen/logrus"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/status"
)

type faucetconfrpcer struct {
	client faucetconfserver.FaucetConfServerClient
}

func (c *faucetconfrpcer) mustGetGRPCClient(flagFaucetconfrpcClientName string, flagFaucetconfrpcServerName string, flagFaucetconfrpcServerPort int, flagFaucetconfrpcKeydir string, flagFaucetconfrpcConnRetries int) {
	crt_file := fmt.Sprintf("%s/%s.crt", flagFaucetconfrpcKeydir, flagFaucetconfrpcClientName)
	key_file := fmt.Sprintf("%s/%s.key", flagFaucetconfrpcKeydir, flagFaucetconfrpcClientName)
	ca_file := flagFaucetconfrpcKeydir + "/" + flagFaucetconfrpcServerName + "-ca.crt"
	certificate, err := tls.LoadX509KeyPair(crt_file, key_file)
	if err != nil {
		panic(err)
	}
	log.Debugf("Certificates loaded")
	certPool := x509.NewCertPool()
	ca, err := ioutil.ReadFile(ca_file)
	if err != nil {
		panic(err)
	}
	if err := certPool.AppendCertsFromPEM(ca); !err {
		panic(err)
	}
	creds := credentials.NewTLS(&tls.Config{
		ServerName:   flagFaucetconfrpcServerName,
		Certificates: []tls.Certificate{certificate},
		RootCAs:      certPool,
		MinVersion:   tls.VersionTLS13,
	})

	// Connect to faucetconfrpc server.
	addr := flagFaucetconfrpcServerName + ":" + strconv.Itoa(flagFaucetconfrpcServerPort)
	log.Debugf("Connecting to RPC server: %v", addr)
	timeout := time.Duration(1)
	for i := 0; i < flagFaucetconfrpcConnRetries; i++ {
		timeout = (timeout + 1) * 2
		conn, err := grpc.Dial(addr, grpc.WithTransportCredentials(creds), grpc.WithBlock(), grpc.WithTimeout(timeout*time.Second))
		if err == nil {
			log.Debugf("Connected to RPC server")
			c.client = faucetconfserver.NewFaucetConfServerClient(conn)
			return
		}
		time.Sleep(timeout * time.Second)
	}
	panic(fmt.Errorf("cannot connect to RPC server"))
}

func (c *faucetconfrpcer) getDpNames() map[string]bool {
	dpNames := make(map[string]bool)
	req := &faucetconfserver.GetDpNamesRequest{}
	resp, err := c.client.GetDpNames(context.Background(), req)
	if err == nil {
		for _, dpName := range resp.DpName {
			dpNames[dpName] = true
		}
	} else {
		// gRPC error (so transport probably is working), but empty config file.
		if grpcerror, ok := status.FromError(err); ok {
			log.Warnf("RPC liveness error %d %s", grpcerror.Code(), grpcerror.Message())
			// Error, and not a gRPC error (e.g. I/O)
		} else {
			panic(err)
		}
	}
	return dpNames
}

func (c *faucetconfrpcer) mustSetFaucetConfigFile(config_yaml string) {
	log.Debugf("setFaucetConfigFile %s", config_yaml)
	req := &faucetconfserver.SetConfigFileRequest{
		ConfigYaml: config_yaml,
		Merge:      true,
	}
	_, err := c.client.SetConfigFile(context.Background(), req)
	if err != nil {
		panic(err)
	}
}

func (c *faucetconfrpcer) mustSetPortAcl(dpName string, portNo OFPortType, acls string) {
	req := &faucetconfserver.SetPortAclRequest{
		DpName: dpName,
		PortNo: uint32(portNo),
		Acls:   acls,
	}
	_, err := c.client.SetPortAcl(context.Background(), req)
	if err != nil {
		panic(err)
	}
}

func (c *faucetconfrpcer) mustSetVlanOutAcl(vlan_name string, acl_out string) {
	req := &faucetconfserver.SetVlanOutAclRequest{
		VlanName: vlan_name,
		AclOut:   acl_out,
	}
	_, err := c.client.SetVlanOutAcl(context.Background(), req)
	if err != nil {
		panic(err)
	}
}

func (c *faucetconfrpcer) mustDeleteDpInterface(dpName string, ofport OFPortType) {
	interfaces := &faucetconfserver.InterfaceInfo{
		PortNo: uint32(ofport),
	}
	interfacesConf := []*faucetconfserver.DpInfo{
		{
			Name:       dpName,
			Interfaces: []*faucetconfserver.InterfaceInfo{interfaces},
		},
	}

	req := &faucetconfserver.DelDpInterfacesRequest{
		InterfacesConfig: interfacesConf,
		DeleteEmptyDp:    true,
	}

	_, err := c.client.DelDpInterfaces(context.Background(), req)
	if err != nil {
		panic(err)
	}
}

func (c *faucetconfrpcer) mustDeleteDp(dpName string) {
	dp := []*faucetconfserver.DpInfo{
		{
			Name: dpName,
		},
	}
	dReq := &faucetconfserver.DelDpsRequest{
		InterfacesConfig: dp,
	}

	_, err := c.client.DelDps(context.Background(), dReq)
	if err != nil {
		panic(err)
	}
}

func (c *faucetconfrpcer) mustAddPortMirror(dpName string, ofport OFPortType, mirrorofport OFPortType) {
	req := &faucetconfserver.AddPortMirrorRequest{
		DpName:       dpName,
		PortNo:       uint32(ofport),
		MirrorPortNo: uint32(mirrorofport),
	}
	_, err := c.client.AddPortMirror(context.Background(), req)
	if err != nil {
		panic(err)
	}
}

func (c *faucetconfrpcer) mustSetRemoteMirrorPort(dpName string, ofport OFPortType, vid OFVidType, remoteDpName string, remoteofport OFPortType) {
	req := &faucetconfserver.SetRemoteMirrorPortRequest{
		DpName:       dpName,
		PortNo:       uint32(ofport),
		TunnelVid:    uint32(vid),
		RemoteDpName: remoteDpName,
		RemotePortNo: uint32(remoteofport),
	}
	_, err := c.client.SetRemoteMirrorPort(context.Background(), req)
	if err != nil {
		panic(err)
	}
}

func (c *faucetconfrpcer) coproInterfaceYaml(ofport OFPortType, description string, strategy string) string {
	return fmt.Sprintf("%d: {description: %s, coprocessor: {strategy: %s}},", ofport, description, strategy)
}

func (c *faucetconfrpcer) vlanInterfaceYaml(ofport OFPortType, description string, vlan uint, acls_in string) string {
	return fmt.Sprintf("%d: {description: %s, native_vlan: %d, acls_in: [%s]},", ofport, description, vlan, acls_in)
}

func (c *faucetconfrpcer) localVlanInterfaceYaml(ofport OFPortType, description string, vlan uint, acls_in string) string {
	return fmt.Sprintf("%d: {opstatus_reconf: False, description: %s, native_vlan: %d, acls_in: [%s]},", ofport, description, vlan, acls_in)
}

func (c *faucetconfrpcer) stackInterfaceYaml(ofport OFPortType, remoteDpName string, remoteOfport OFPortType) string {
	return fmt.Sprintf("%d: {description: stack link to %s, stack: {dp: %s, port: %d}},", ofport, remoteDpName, remoteDpName, remoteOfport)
}

func (c *faucetconfrpcer) mergeDpInterfacesMinimalYaml(dpName string, addInterfaces string) string {
	return fmt.Sprintf("%s: {interfaces: {%s}},", dpName, addInterfaces)
}

func (c *faucetconfrpcer) mergeDpInterfacesYaml(dpName string, uintDpid uint64, description string, addInterfaces string, egressPipeline bool) string {
	egressPipelineStr := "false"
	if egressPipeline {
		egressPipelineStr = "true"
	}
	return fmt.Sprintf("%s: {dp_id: %d, description: %s, hardware: %s, egress_pipeline: %s, interfaces: {%s}},",
		dpName, uintDpid, description, "Open vSwitch", egressPipelineStr, addInterfaces)
}

func (c *faucetconfrpcer) mergeSingleDpMinimalYaml(dpName string, addInterfaces string) string {
	return fmt.Sprintf("{dps: {%s}}", c.mergeDpInterfacesMinimalYaml(dpName, addInterfaces))
}

func (c *faucetconfrpcer) mergeSingleDpYaml(dpName string, uintDpid uint64, description string, addInterfaces string, egressPipeline bool) string {
	return fmt.Sprintf("{dps: {%s}}", c.mergeDpInterfacesYaml(dpName, uintDpid, description, addInterfaces, egressPipeline))
}
