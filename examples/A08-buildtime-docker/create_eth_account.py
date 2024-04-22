#!/usr/bin/env python3
# encoding: utf-8

import os
import shutil
import tempfile
from seedemu.utilities.BuildtimeDocker import BuildtimeDockerFile, BuildtimeDockerImage

current_dir = os.path.dirname(os.path.realpath(__file__))

dockerfile_path = os.path.join(current_dir, "Dockerfile")
print(dockerfile_path)
with open(dockerfile_path, "r") as f:
   dockerfile = BuildtimeDockerFile(f.read())

container = BuildtimeDockerImage("ethaccount").build(dockerfile).container()


tmp_dir = tempfile.mkdtemp(prefix="seedemu-ethaccount-")

container.entrypoint("python").mountVolume(tmp_dir, "/app").run(
   "-c \"from eth_account import Account; f = open('account.txt', 'w'); f.write(Account.create().address); f.close()\""
)

output_dir = os.path.join(current_dir, "output")

shutil.rmtree(output_dir, ignore_errors=True)

shutil.copytree(tmp_dir, output_dir)

shutil.rmtree(tmp_dir, ignore_errors=True)

print("Account address:", end=" ")

with open(os.path.join(output_dir, "account.txt"), "r") as f:
   print(f.read())
