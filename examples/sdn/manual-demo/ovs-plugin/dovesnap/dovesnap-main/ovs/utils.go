package ovs

import (
	"encoding/hex"
	"fmt"
	"hash/crc32"
	"math"
	"net"
	"os"
	"strconv"
	"strings"
	"time"

	bc "github.com/kenshaw/baseconv"
	log "github.com/sirupsen/logrus"
	"github.com/vishvananda/netlink"
)

const (
	b62alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)

func ParseUint32(value string) (uint32, error) {
	uintValue, err := strconv.ParseUint(value, 10, 32)
	if err == nil {
		return uint32(uintValue), nil
	}
	return 0, err
}

func base36to16(value string) string {
	converted, _ := bc.Convert(strings.ToLower(value), bc.Digits36, bc.DigitsHex)
	digits := len(converted)
	for digits < 6 {
		converted = "0" + converted
		digits = len(converted)
	}
	return strings.ToUpper(converted)
}

func defaultUint(strValue string, defaultValue uint64) uint64 {
	uintValue, err := strconv.ParseUint(strValue, 10, 64)
	if err == nil {
		return uintValue
	}
	return defaultValue
}

func mustGetUintFromHexStr(dpid string) uint64 {
	strVal, _ := bc.Convert(strings.ToLower(dpid[2:]), bc.DigitsHex, bc.DigitsDec)
	uintVal := defaultUint(strVal, 0)
	if uintVal == 0 {
		panic(fmt.Errorf("unable convert %s to an uint", strVal))
	}
	return uintVal
}

// return int64 as base62.
func b62Encode(n int64) string {
	if n == 0 {
		return "0"
	}

	b := make([]byte, 0, 512)
	base := int64(len(b62alphabet))
	for n > 0 {
		r := math.Mod(float64(n), float64(base))
		n /= base
		b = append([]byte{b62alphabet[int(r)]}, b...)
	}
	return string(b)
}

// Represent link name as a short hash, for use in an interface name.
func patchStr(a string) string {
	return b62Encode(int64(crc32.ChecksumIEEE([]byte(a))))
}

// Return the IPv4 address of a network interface
func getIfaceAddr(name string) (*net.IPNet, error) {
	iface, err := netlink.LinkByName(name)
	if err != nil {
		return nil, err
	}
	addrs, err := netlink.AddrList(iface, netlink.FAMILY_V4)
	if err != nil {
		return nil, err
	}
	if len(addrs) == 0 {
		return nil, fmt.Errorf("interface %s has no IP addresses", name)
	}
	if len(addrs) > 1 {
		log.Infof("Interface [ %v ] has more than 1 IPv4 address. Defaulting to using [ %v ]\n", name, addrs[0].IP)
	}
	return addrs[0].IPNet, nil
}

func mustPrefixMAC(macPrefix string, macAddress string) string {
	prefixBytes, err := hex.DecodeString(strings.ReplaceAll(macPrefix, ":", ""))
	if err != nil {
		panic(fmt.Errorf("invalid MAC prefix: %s", macPrefix))
	}
	if len(prefixBytes) > 5 {
		panic(fmt.Errorf("MAC prefix too long: %s", macPrefix))
	}
	rawMacAddress, parseerr := net.ParseMAC(macAddress)
	if parseerr != nil {
		panic(parseerr)
	}
	for i, b := range prefixBytes {
		rawMacAddress[i] = b
	}
	return rawMacAddress.String()
}

func mustSetInterfaceMac(name string, macAddress string) {
	iface := mustGetLinkByName(name)
	netaddr, err := net.ParseMAC(macAddress)
	if err != nil {
		panic(err)
	}
	err = netlink.LinkSetHardwareAddr(iface, netaddr)
	if err != nil {
		panic(err)
	}
}

func mustSetInterfaceMTU(name string, mtu uint) {
	iface := mustGetLinkByName(name)
	err := netlink.LinkSetMTU(iface, int(mtu))
	if err != nil {
		panic(err)
	}
}

// Set the IP addr of a netlink interface
func setInterfaceIP(name string, rawIP string) error {
	retries := 2
	var iface netlink.Link
	var err error
	for i := 0; i < retries; i++ {
		iface, err = netlink.LinkByName(name)
		if err == nil {
			break
		}
		log.Debugf("error retrieving new OVS bridge netlink link [ %s ]... retrying", name)
		time.Sleep(2 * time.Second)
	}
	if err != nil {
		log.Fatalf("Abandoning retrieving the new OVS bridge link from netlink, Run [ ip link ] to troubleshoot the error: %s", err)
		return err
	}
	addr, err := netlink.ParseAddr(rawIP)
	if err != nil {
		return err
	}
	return netlink.AddrAdd(iface, addr)
}

// Increment an IP in a subnet
func ipIncrement(networkAddr net.IP) net.IP {
	for i := 15; i >= 0; i-- {
		b := networkAddr[i]
		if b < 255 {
			networkAddr[i] = b + 1
			for xi := i + 1; xi <= 15; xi++ {
				networkAddr[xi] = 0
			}
			break
		}
	}
	return networkAddr
}

// Check if a netlink interface exists in the default namespace
func validateIface(ifaceStr string) bool {
	_, err := net.InterfaceByName(ifaceStr)
	if err != nil {
		log.Debugf("The requested interface [ %s ] was not found on the host: %s", ifaceStr, err)
		return false
	}
	return true
}

func ensureDirExists(dir string) {
	_, err := os.Stat(dir)
	if os.IsNotExist(err) {
		err = os.MkdirAll(dir, 0755)
		if err != nil {
			panic(err)
		}
	}
}

func createNsLink(pid int, id string) {
	procPath := fmt.Sprintf("/proc/%d/ns/net", pid)
	procNetNsPath := fmt.Sprintf("%s/%s", netNsPath, id)

	_, err := os.Lstat(procNetNsPath)
	if err == nil {
		log.Debugf("Remove existing %s", procNetNsPath)
		err = os.Remove(procNetNsPath)
		if err != nil {
			panic(err)
		}
	}

	err = os.Symlink(procPath, procNetNsPath)
	if err != nil {
		panic(err)
	}
}

func deleteNsLink(id string) {
	procNetNsPath := fmt.Sprintf("%s/%s", netNsPath, id)
	os.Remove(procNetNsPath)
}

// Create veth pair. Peername is renamed to eth0 in the container
func vethPair(suffix string) *netlink.Veth {
	return &netlink.Veth{
		LinkAttrs: netlink.LinkAttrs{Name: ovsPortPrefix + suffix},
		PeerName:  peerOvsPortPrefix + suffix,
	}
}

func mustGetLinkByName(name string) netlink.Link {
	iface, err := netlink.LinkByName(name)
	if err != nil {
		panic(err)
	}
	return iface
}

func getMacAddr(name string) string {
	iface := mustGetLinkByName(name)
	return iface.Attrs().HardwareAddr.String()
}

// Enable a netlink interface
func interfaceUp(name string) error {
	iface, err := netlink.LinkByName(name)
	if err != nil {
		log.Debugf("Error retrieving a link named [ %s ]", iface.Attrs().Name)
		return err
	}
	return netlink.LinkSetUp(iface)
}

// Delete veth pair.
func delVethPair(localVethPair *netlink.Veth) {
	err := netlink.LinkDel(localVethPair)
	if err != nil {
		panic(err)
	}
}

// Add and activate veth pair
func addVethPair(localVethPair *netlink.Veth) {
	err := netlink.LinkAdd(localVethPair)
	if err != nil {
		panic(err)
	}
	err = netlink.LinkSetUp(localVethPair)
	if err != nil {
		panic(err)
	}
}
