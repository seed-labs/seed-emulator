package main

import (
	"flag"
	"os"
	"os/signal"
	"syscall"

	ovs "dovesnap/ovs"
	"github.com/docker/go-plugins-helpers/network"
	log "github.com/sirupsen/logrus"
)

const (
	version = "1.1.22.dev"
)

func main() {
	flagTrace := flag.Bool("trace", false, "enable trace level debugging")
	flagDebug := flag.Bool("debug", false, "enable debugging")
	flagFaucetconfrpcClientName := flag.String(
		"faucetconfrpc_client", "faucetconfrpc", "basename name of faucetconfrpc client certificate")
	flagFaucetconfrpcServerName := flag.String(
		"faucetconfrpc_addr", "localhost", "address of faucetconfrpc server")
	flagFaucetconfrpcServerPort := flag.Int(
		"faucetconfrpc_port", 59999, "port for faucetconfrpc server")
	flagFaucetconfrpcKeydir := flag.String(
		"faucetconfrpc_keydir", "/faucetconfrpc", "directory with keys for faucetconfrpc server")
	flagFaucetconfrpcConnRetries := flag.Int(
		"faucetconfrpc_connretries", 5, "number of retries to connect to faucetconfrpc server")
	flagStackingInterfaces := flag.String(
		"stacking_interfaces", "", "comma separated list of [dpname:port:interface_name] to use for stacking")
	flagStackPriority1 := flag.String(
		"stack_priority1", "", "dp name of switch to give stacking priority 1")
	flagStackMirrorInterface := flag.String(
		"stack_mirror_interface", "", "stack tunnel mirroring configuration [mirrordpname:mirrorport]")
	flagDefaultControllers := flag.String(
		"default_ofcontrollers", "", "default OF controllers to use (must be defined if stacking is used)")
	flagMirrorBridgeIn := flag.String(
		"mirror_bridge_in", "", "optional input interface from another mirror bridge")
	flagMirrorBridgeOut := flag.String(
		"mirror_bridge_out", "", "output interface from mirror bridge")
	flagStatusServerPort := flag.Int(
		"status_port", 9401, "port for status server")
	flagStatusAuthIPs := flag.String(
		"status_auth_ips", "127.0.0.0/8,::1/128", "list of authorized IPs for status server")
	flag.Parse()
	if *flagTrace {
		log.SetLevel(log.TraceLevel)
	} else if *flagDebug {
		log.SetLevel(log.DebugLevel)
	}
	flag.VisitAll(func(f *flag.Flag) {
		log.Infof("flag: %s: %s", f.Name, f.Value)
	})
	d := ovs.NewDriver(
		*flagFaucetconfrpcClientName,
		*flagFaucetconfrpcServerName,
		*flagFaucetconfrpcServerPort,
		*flagFaucetconfrpcKeydir,
		*flagFaucetconfrpcConnRetries,
		*flagStackPriority1,
		*flagStackingInterfaces,
		*flagStackMirrorInterface,
		*flagDefaultControllers,
		*flagMirrorBridgeIn,
		*flagMirrorBridgeOut,
		*flagStatusServerPort,
		*flagStatusAuthIPs)
	log.Infof("New Docker driver created")
	h := network.NewHandler(d)
	log.Infof("Getting ready to serve new Docker driver")
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGTERM)
	go func() {
		h.ServeUnix(ovs.DriverName, 0)
		log.Errorf("Unexpected server exit")
		os.Exit(1)
	}()
	sig := <-sigChan
	log.Infof("Caught signal %v", sig)
	d.Quit()
	os.Exit(0)
}
