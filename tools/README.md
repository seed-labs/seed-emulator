# Tools

This folder contains the tools developed for the emulator.

## Traffic Visualizer

[`TrafficVisualizer`](TrafficVisualizer) is a source-tree tool that examples can
copy into victim containers to count and display packets observed by `tcpdump`.
Each example provides its own capture filter and web-port configuration.

## Example Test Helper

`run-example-test.sh` resolves short example codes to `example.yaml` manifests
and runs the standardized test runner:

```sh
tools/run-example-test.sh A01
tools/run-example-test.sh A02a probe
tools/run-example-test.sh B02 all
```

## BotnetLab

`BotnetLab` is a small controller/agent toolkit for dependency-free,
allowlisted botnet demonstrations in SEED examples.
