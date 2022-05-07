#!/bin/bash
############################################################
# Help                                                     #
############################################################
Help()
{
   # Display Help
   echo "Add description of the script functions here."
   echo
   echo "Syntax: bridge.sh [-i|h|a]"
   echo "example: bridge.sh -i eth0 -a 150"
   echo "options:"
   echo "i     set physical interface name."
   echo "a     set asn where dhcp server installed."
   echo "h     Print this Help."
   echo ""
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

if [ -z "$ASN" ]
then 
   echo "Error: option(-a) ASN needed"
   exit
fi

if [ -z "$iface" ]
then
   echo "Error: option(-i) iface name needed"
   exit
fi

br=$(echo $(ip addr show to 10.$ASN.0.1) | cut -d ':' -f 2 )

if [ -z "$br" ]
then
   echo "Error: Invalid ASN"
fi

error=$(sudo ip link set $iface master $br 2>&1)

if [ -z "$error" ]
then
   echo "$iface is bridged to $br successfully"
else
   echo $error
fi

