# Instructions

1. Run `01_bgp_setup.sh` to set up the BGP attack demo. It does the followings:
   - For each target IP prefix described in the `TARGET` file, generate the corresponding 
     BGP files, and save the files in `BGP_CONF_DIR` folder (these files will be used
     by the BIRD routing program). These files will later be used by the demo system
     to launch the BGP prefix hijacking attack. 

   - Change `target_prefix` if you want to change the targets. 

   - Change this line `BGP_CONF_DIR="../01_bgp_prefix_hijacking/files/as199_include`
     if needed. 

2. Run `02_morris_setup.sh` to set up the Morris worm demo
   - Save the configuration to `/etc/seedemu/seedemu.conf`. This line might need to change:
     `conda_env='emu'`. 
