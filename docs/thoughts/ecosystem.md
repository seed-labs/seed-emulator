# Building the Ecosystem 

Building a realistic emulation takes time. It will be great if people
can share what they build. For example, if somebody painstakingly builds
a emulation for a small regional network, and is willing to share, we should
make it easy for people to do that. We do need to think about how to 
build such an ecosystem, where people can build, share, and adopt emulations.
We will use this document to record our thinkings. We should learn from
the other successful ecosystems, such as Android, browser extensions, 
the SimCity game, etc. 

- **The method of sharing**: There are different ways to share emulations:
  - Sharing the Python code: this method is problematic. One of the issues 
    is the code isolation: we need to make sure that the imported module 
    is isolated and won't interfere with the other modules. This can lead 
    to a signficant change in our current design. 

  - Sharing the docker files (i.e. output of the code): this method is not 
    easy to customize the imported emulation. If we want to change something 
    in it, it is not easy. Customization will be inevitably needed. 

  - Sharing the intermediate data. We can render the emulation into 
    an intermediate file (e.g. Json file). Others can import this file, and
    use the file to recreate the emulation inside Python. This may be the
    better solution. 
    

- **Duplicate AS**: Inevitably, when we import other people's emulators, we
will get into a situation where some ASes are duplicate. How to handle this?
Sometimes, the duplication is part of the reality, and sometimes, it is 
a mistake. Our layer design may be able to help here. Here are some thoughts:
    - ASes in the upper layer may be able to hide the ASes in the lower layer. 
      We need to make sure this does not create issues. 
    - Another choice is to add a `deleteAS` API, so we can delete a particular 
      AS from the imported emulator.
    - We can implement some mechanism like layer mask, which can mask certain
      elements on a particular layer. 
    - When we import other a emulator, we will recreate all its objects. We can
      just go to an imported object, and make change to it directly, including
      change its ASN, IP prefix, etc. This may be the best way to do it.


- **Manifest file**: Just like Android apps, we may want to include a manifest
file for each emulator. It publishes some of the essential information, such
as the ASes, IP prefixes, IXes, etc. This file can make the management easier.

- **Isolation**: We also need to enforce isolation to make sure an imported
    emulation does not modify the rest of the system. 
    For example, we don't want an imported emulation to install a web server 
    on a host that is not part of the imported emulation. Obviously, when the 
    emulation runs, it will interfere with the rest of the system, but that
    is fine.  Maybe we can introduce `namespace`.
