package ovs

import (
	"fmt"
	"os/exec"
	"strings"

	log "github.com/sirupsen/logrus"
)

const (
	ovsofctlPath   = "/usr/bin/ovs-ofctl"
	ovsvsctlPath   = "/usr/bin/ovs-vsctl"
	ovsvsctlDBPath = "unix:/var/run/openvswitch/db.sock"
)

func RunCmd(cmd string, args ...string) (string, error) {
	output, err := exec.Command(cmd, args...).CombinedOutput()
	if err != nil {
		log.Debugf("FAILED: %v, %s", args, output)
	} else {
		log.Tracef("OK: %v", args)
	}
	return strings.TrimSuffix(string(output), "\n"), err
}

func VsCtl(args ...string) (string, error) {
	all := append([]string{fmt.Sprintf("--db=%s", ovsvsctlDBPath)}, args...)
	output, err := RunCmd(ovsvsctlPath, all...)
	return output, err
}

func mustVsCtl(args ...string) string {
	output, err := VsCtl(args...)
	if err != nil {
		panic(err)
	}
	return output
}

func OfCtl(args ...string) (string, error) {
	output, err := RunCmd(ovsofctlPath, args...)
	return output, err
}

func mustOfCtl(args ...string) string {
	output, err := OfCtl(args...)
	if err != nil {
		panic(err)
	}
	return output
}

type ovsdber struct {
}
