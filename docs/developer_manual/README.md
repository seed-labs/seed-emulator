# Developer Manual for the SEED Emulator

- [Creating a new layer](./00-creating-a-new-layer.md)
- [Creating a new service](./01-creating-a-new-service.md)
- [Creating a new component](./02-creating-a-new-component.md)
- [Creating a new rap](./03-createing-a-new-rap.md)
- FAQs
    - [How to get ip address](./99-FAQs.md#Q01-how-to-get-ip-address)
    - [How to make a change on all nodes](./99-FAQs.md#Q02-how-to-make-a-change-on-all-nodes)

## Layer 
Layer classes make changes to the emulation as a whole. The characteristic of base layers is that they provide the basics to support the emulation and higher-level layers.

## Service
Service layers will typically only make changes to individual nodes. 

<!-- ## vnode, vpnode, and pnode -->
<!-- 
Service::install

Service::configure(self, emulator:Emulator)
-> Service::__configureServer(server:Server, node:Node)
-> Service::_doConfigure(self, node:Node, server:Server) : configure server. By default, this does nothing.

Service::render
-> Service::_doInstall(self, node:Node, server:Server) # install the server on node.


when rendering an emulator by calling the Emulator::render() method, the emulator will be rendered after going through confiugration phase internally. -->