
1. Run `setup.sh` to disable the address randomization
2. Run `first_attack.py` to attack the first node `10.151.0.71`.
   The actual worm is in `worm.py`, which will be copied to the compromised nodes 
3. We can use `control_worm.py` to control the behaviors of the worm.
   It takes the following arguments
   - `stop`: all the worms will exit
   - `pause`: all the worms will stop attacking others
   - `run`: all the worms will continue running
   - `show`: display the infected nodes on the the internet map
   - `off`: do not display the infected nodes on the internet map

- Note 1: the visualization uses a script called `submit_event.sh`. We need to 
install this script on all the nodes. This is a plug-in in the internet map.
We can install this plug-in from the internet map. 

- Note 2: the visualization seems to have some small issues. Some nodes keep
flashing and won't turn off, even if we send a restore command to the map.
Refreshing the map will solve the problem. Need to figure out the reason, as
it might be a bug in the map.
