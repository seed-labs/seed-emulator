# User Manual: Visualization 

- [Include the Internet Map automatically](#include-map)



<a id="include-map"></a>
## Include the Internet Map automatically 

When generating the final docker files, we can ask the emulator
to automatically include the Internet Map container using 
the following flag. The Internet map host will then be added to 
the `docker-compose.yml` file. 

```
docker = Docker(internetMapEnabled=True)
```
