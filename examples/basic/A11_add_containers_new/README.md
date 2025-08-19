# Add existing containers

In some cases, we already have an existing container image, and we want
some of the containers in the emulator to use this image. There are two
methods to do this. 


## Method 1

In this method, we add existing containers when building the emulator. 
We have implemented this feature in the `Docker` compiler class. The basic idea
is to tell the compiler that we want to attach an existing container to 
a network inside the emulator. The compiler will then generate the corresponding
entry inside the `docker-compose.yml` file.

See [this example](./method1/README.md) for details.


## Method 2

In this method, we add the existing containers after we have built the emulator.
Using this method, we first start the emulator, and then start the additional containers
from the existing images. We attach these containers to the networks created by the emulator.
This way, the new containers becomes part of the emultion.

See [this example](./method2/README.md) for details.
