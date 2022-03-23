#!/bin/bash
############################################################
# Help                                                     #
############################################################
Help()
{
   # Display Help
   echo "Add description of the script functions here."
   echo
   echo "Syntax: scriptTemplate [-i|h|a]"
   echo "options:"
   echo "i     set physical interface name."
   echo "a     set asn where dhcp server installed."
   echo "h     Print this Help."
   echo
}

############################################################
############################################################
# Main program                                             #
############################################################
############################################################
############################################################
# Process the input options. Add options as needed.        #
############################################################
# Get the options
while getopts ":h:a:i:" option; do
   case $option in
      h) # display Help
         Help
         exit;;
      a) # Enter an ASN
         ASN=$OPTARG;;
      i) # Enter an Physicial interface card name
	 iface=$OPTARG;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done

a=$(ip addr show to 10.$ASN.0.1)

b=$(echo $a | cut -d ':' -f 2)


echo $b
sudo ip link set $iface master $b
echo "hello world!$ASN, $iface"
