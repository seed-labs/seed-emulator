# Note

## The base container 

Removed the zsh from the `Dockerfile`, as it causes the 
problem in the BOF attack (still haven't figured out why). 
Also change the `FROM` entry to use our customized Ubuntu image.


## Containers for nodes 

Run `z_build.sh` in the generated output folder. It builds `morris-worm-base`,
the intermediate images in `dummies/`, and then the node images.
The intermediate images must be built first because Compose does not infer
build dependencies from Dockerfile `FROM` instructions.

## The server folder

This folder contains the server code (source code). The binary
code is already copied to the `morris-worm-base` folder.
