## uploadMap

Similar to the map page in function.

However, the data source is the uploaded `docker-compose.yml` file, which only displays the network topology diagram. In fact, no corresponding nodes are running on the host machine. 

Therefore, functions such as the `Terminal` and `Filter` that require background nodes cannot be used.

1. Select the yml file (the docker-compose.yml file in the output path of the simulator code), which can be selected either by dragging the file or by choosing from a folder.
2. Click `Parse file`
3. After the file is parsed successfully, wait for the rendering.
4. Please select the options to be displayed in the "Settings -> Categories -> IX / Transit" section.

![uploadMap.png](assets/uploadMap.png)