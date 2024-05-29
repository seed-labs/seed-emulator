# User Manual: Visualization 


- [Include the Internet Map automatically](#include-map)
- [Access the Internet Map](#access-map)


<a id="include-map"></a>
## Include the Internet Map automatically 

When generating the final docker files, we can ask the emulator
to automatically include the Internet Map container using 
the following flag. The Internet map host will then be added to 
the `docker-compose.yml` file. The default value for
this flag is `True`. 

```
docker = Docker(internetMapEnabled=True)
```


<a id="access-map"></a>
## Access the Internet Map

The Internet Map can be accessed via the following URL:
`http://127.0.0.1:8080/map.html`.

