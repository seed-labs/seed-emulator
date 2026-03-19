# Creating a Test Suite

SEED Emulator uses Python `unittest` tests under `tests/`.

## Run the existing test suite

From the repo root:

```bash
python3 -m unittest -v
```

To run a specific test file:

```bash
python3 -m unittest -v tests/<test_file>.py
```

More details (including legacy compile-tests and dynamic tests) are documented in:

- `tests/README.md`

## Adding a new test

1. Put your new test under `tests/` and name it `*_test.py`.
2. Use `unittest.TestCase` with fast, deterministic checks.
3. Prefer compile/render level assertions (string/template, generated artifacts) over long-running runtime tests.
4. If you change K3s mainline behavior, ensure `mini_internet` (baseline) is not broken.

