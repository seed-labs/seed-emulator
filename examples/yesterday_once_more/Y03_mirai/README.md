# Replaying Mirai Attack

We have provided demos for this attack in the following folders using different displaying methods:

1. `demo` folder: Displaying victim's screen in your machine's browser (localhost,port 8888) or on the victim's screen in your own VM.

2. `demo_with_proxmox_vm` folder: Displaying victim's screen in our Proxmox VM System. If you don't have access to the Proxmox VM System, please choose the `demo` folder.

Details of replaying is in mirai.ipynb, please read the provided jupyter notebook.

When either demo compiles the environment, it registers the InternetMap bundle
explicitly. Port `8081` is the traffic observer control endpoint, `8082` is
the topology UI, and `8083` is the geographic UI. The victim display remains
on port `8888` in the local demo.
