# README

- Go to the `emulator` folder, run `large-internet.py` to generate the emulator files.

- Go to the `demo_output` folder, run `bash ./z_build.sh` to build the containers.

- Run `bash ./z_start.sh` to start the emulator. Open the topology UI at
  <http://localhost:8079/> or the geographic UI at
  <http://localhost:8080/>. Port `8078` is used by the traffic observer.

- Follow the instructions in [worm/README.md](worm/README.md) to run and control
  the experiment from the command line.

- Run `docker compose down` in `demo_output` to stop and remove the containers.
