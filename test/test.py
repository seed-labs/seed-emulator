import subprocess

result = subprocess.run(["ping", "-c", "3", "8.8.8.8"])
print(result.returncode)