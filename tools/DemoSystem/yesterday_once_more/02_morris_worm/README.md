# README

- Put the correct information in the `seedemu.conf` file,
  and copy it to `/etc/seedemu/seedemu.conf`

```yaml
demoSystem:
  hostProjectPath: /home/cy/projects/debug/seed-emulator/tools/DemoSystem  # DemoSystem's root folder 
```

- Go to the `emulator` folder, run `large-internet.py` to generate the emulator files

- Go to the `demo_output` folder, run `dcbuild` to build the container. 
  Note, `dcbuild` is the alias for `DOCKER_BUILDKIT=0 docker compose build`

After this step, the setup is complete, we are ready to run the demo system. 

After the shooting range is successfully activated, select to enter the Map page and then proceed with the subsequent operations.