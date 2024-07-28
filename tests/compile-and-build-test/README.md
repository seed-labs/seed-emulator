# compile-and-build-test

The `compile-and-build-test.py` script runs all examples listed in the `test_list` variable and compares the actual outcomes to the expected outcomes. This variable is a dictionary where each entry has the format `{example_path: (list of scripts to run, list of expected outputs)}`. Here are some entries from the `test_list`:

```
cls.test_list = {
            "basic/A00_simple_as":          (["simple_as.py"], ["output"]),
            "basic/A01_transit_as":         (["transit_as.py"], ["output"]),
            "basic/A02_transit_as_mpls":    (["transit_as_mpls.py"], ["output"]), 
            "basic/A03_real_world":         (["real_world.py"], ["output"]),
            "basic/A04_visualization":      (["visualization.py"], ["output", "base_component.bin"]), 
            "basic/A05_components":         (["components.py"], ["output", "base_component.bin"]),
            "basic/A06_merge_emulation":    (["merge_emulation.py"], ["output"]),
            ...
            omitted
            ...
            }
```

The script also executes `docker compose build` if any expected outcome includes emulation files.

## Usage
```python
./compile-and-build-test.py amd|arm
```