Internet Emulator
---

The objective of the SEED-Emulator project is to help create emulators of 
the Internet. These emulators are for educational uses, and they can be
used as the platform for designing hands-on lab exercises for various subjects,
including cybersecurity, networking, etc.

The project provides essential elements of the Internet (as Python classes), including 
Internet exchanges, autonomous systems, BGP routers, DNS infrastructure, 
a variety of services. Users can use these elements as the building blocks
to build their emulation programmatically. The output of the program 
is a set of docker container folders/files. When these containers are built and 
started, they form a small-size Internet. New building blocks are being added,
including Blockchain, Botnet, and many other useful elements of the Internet. 

![The Web UI](./docs/assets/web-ui.png)

## Table of Contents

-  [Getting Started](#getting-started)
-  [User Manuals](#user-manuals)
-  [Contributing](#contributing)
-  [License](#license)


## Getting Started

### Install the necessary software

To run the emulator, you need to install `docker`, `docker-compose`, 
and `python3`.


### Set up the project

To run the emulator code, we can do one of the followings:

- Run `pip install -e file:.` inside the project's root directory. It will install the project ( file:. current path ) in editable mode. It creates a symlink of current folder to python's default search path.

- Add this folder to the `PYTHONPATH` environment variable. This can be done by running `source development.env` 
inside the project's root directory.

### Set up the proxy (not needed if you don't have an issue)

The emulator needs to fetch docker images from the Docker Hub. 
If you are in Mainland China, you may not be able to directly get the 
docker images. However, there are many docker hub proxies that 
you can use. Please follow [these instructions](./docs/user_manual/dockerhub_proxy.md)
to set up the docker hub proxies. If you do not have such an issue,
please skip this step. 


### Run Examples

We have provided many examples in the [examples/](./examples/) folder. 
Detailed explanations are provided the README file in each example folder.
To run an example, do the following:

1. Pick an example, for example, `A00-simple-as`. 

2. Build the emulation. For this example, go to `examples/A00-simple-as/`, and
   run `python3 ./simple-as.py`. The container files will be created inside the
  `output/` folder. For some examples, such as `B02-mini-internet-with-dns`,
   they depend on other examples, so you need to run those examples first. 

3. Build and run the generated containers. First `cd output/`, then do `docker-compose
   build && docker-compose up`. The emulator will start running. Give it a
   minute or two (or longer if your emulator is large) to let the routers do
   their jobs.

4. Some examples already include the visualization container (called Internet
   Map).  Point your browser to `http://127.0.0.1:8080/map.html`, and you will
   see the visualization. More instructions on how to use the visualization app
   is given in [this manual](./docs/user_manual/internet_map.md).  If the map
   is not included, you can open a new terminal window, navigate to the project
   root directory, cd to `client/`, and run `docker-compose build &&
   docker-compose up`. This will bring up the Internet Map container. 


## User Manuals

User manuals are provided inside the [docs/user_manual/](./docs/user_manual) folder.

## Contributing

Contributions to SEED-Emulator are always welcome. For contribution guidelines, please see [CONTRIBUTING](./CONTRIBUTING.md).

## License

The software is licensed under the GNU General Public License v3.0 license, with copyright by The SEED-Emulator Developers (see [LICENSE](./LICENSE.txt)).
