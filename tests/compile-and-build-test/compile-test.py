#!/usr/bin/env python3

import stat
import subprocess
import sys
import os
import shutil
from pathlib import Path

"""
Compiles examples in examples/ and outputs the number of examples that fail to
compile.
"""

examples_dirs = [
    Path("examples/basic"),
    Path("examples/blockchain"),
    Path("examples/internet"),
    Path("examples/scion"),
]


def glob_examples(dir: Path):
    for subdir in (x for x in dir.iterdir() if x.is_dir()):
        for file in (x for x in subdir.iterdir() if x.is_file() and x.match("*.py")):
            if file.stem.startswith("test") or file.stem.endswith("test"):
                continue  # skip local tests in examples/blockchain
            if (file.stat().st_mode & stat.S_IXUSR) != 0:
                yield file


examples = []
for dir in examples_dirs:
    examples.extend(glob_examples(dir))

failed = []

for example in examples:
    print(f"=== Run {example} ===")
    output = example.parent / "output"
    if output.exists():
        shutil.rmtree(output)
    res = subprocess.run(
        [sys.executable, str(example.name)],
        cwd=example.parent,
        env={
            "PYTHONPATH": str(Path(".").absolute()),
            "PATH": ":".join([os.environ.get("PATH"), str(Path("./bin").absolute())]),
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )
    if res.returncode != 0:
        print(res.stdout)
        print(f"FAILED: {example}")
        failed.append(example)
    else:
        print("OK")

if len(failed) > 0:
    print("==============================")
    print(f"{len(failed)} EXAMPLES FAILED")
    for example in failed:
        print(example)
    print("==============================")

print("score: {} of {}".format(len(examples) - len(failed), len(examples)))
exit(len(failed))
