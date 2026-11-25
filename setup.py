from pathlib import Path

import setuptools

with open(Path(__file__).parent / "README.md", "r", encoding="utf-8") as readme:
    long_description = readme.read()

setuptools.setup(
    name = "seedemu",
    version = "2.0.0",
    author = "Wenliang Du",
    author_email = "wenliangdu@zju.edu.cn",
    description = "SEED Internet Emulator",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/seed-labs/seed-emulator",
    packages = setuptools.find_namespace_packages(
        include=["seedemu", "seedemu.*"],
        exclude=["*.__pycache__", "*.__pycache__.*"],
    ),
    include_package_data = True,
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    install_requires = [
        'geopy',
        'requests',
        'PyYAML',
    ],
    python_requires = '>=3.10'
)
