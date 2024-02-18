# User Manual: Docker Image

- [Generate the docker images for different platforms](#platform)
- [Use pre-built image on selected nodes](#prebuilt-image)



<a id="platform"></a>
## Generate the docker images for different platforms

Most of the docker images were built using the multi-arch build approach,
i.e., the same docker image name is used for multiple platforms. 
However, we have not been able to build our Ethereum docker image
using the multi-arch approach (we have not got time to figure out why),
so for this image, the names for different platforms are different. 
Users still have to specify the platform using the `platform` 
argument when creating the `Docker` object. See the following 
example

```python
# For AMD64 machines (default)
docker = Docker(platform=Platform.AMD64)

# For Apple Silicon machines (M1/M2 chips)
docker = Docker(platform=Platform.ARM64)
```


<a id="custom-image"></a>
## Use custom image on selected nodes

Sometimes, we would like some of the nodes in the emulator to use
a custom docker image, instead of using the default ones from the emulator. 
The following example shows how to do this. 

 - First, we create a `DockerImage` object, where the container files 
   for this docker image are provided in the `my_image` folder. 
 - Then, we use the `setImageOverride` API to set this image for the specified node. 
 - After generating the final output, we need to copy the docker image folder 
   to the output folder. 


```python
# Create a new node (we will use the pre-built docker image for this node)
newhost = emu.getLayer('Base').getAutonomousSystem(150).createHost('new_host')
newhost.joinNetwork('net0')

# Create a Docker object
docker = Docker(internetMapEnabled=True, platform=Platform.AMD64)

# Create an DockerImage object using the pre-built image 
image  = DockerImage(name='my_image', dirName='./my_image', local=True, software=[])
docker.addImage(image)
docker.setImageOverride(newhost, 'my_image')

# Generate the docker files
emu.render()
emu.compile(docker, 'ouput/', override = True)

# Copy the image folder to the output folder
os.system('cp -r my_image/ ' + 'output/')
```

The example shown above uses a local image. We can also use a image from 
an image from the Docker Hub. Here is an example. 

```python
imageName = 'handsonsecurity/seedemu-ethereum'
image  = DockerImage(name=imageName, local=False, software=[])
docker.addImage(image)
docker.setImageOverride(newhost, imageName)
```

