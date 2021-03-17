seedsim-client
---

This is a work-in-progress prototype of the seedsim client. 

What's working:

- listing nodes in the emulation.
- attaching to nodes in the emulation.
- search nodes with their ASN, node name, or IP address.

What's not working:

- Everything else.

How to use:

1. start the emulation as you normally would. (e.g., `docker-compose up`)
2. do `docker-compose build && docker-compose up` in this folder.
3. visit [http://localhost:8080/](http://localhost:8080/).