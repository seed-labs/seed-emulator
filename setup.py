import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name = "seedemu",
    version = "0.0.7",
    author = "Honghao Zeng",
    author_email = "hozeng@syr.edu",
    description = "SEED Internet Emulator",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/seed-labs/seed-emulator",
    packages = setuptools.find_packages(),
    include_package_data = True,
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL-3.0",
        "Operating System :: OS Independent",
    ],
    install_requires = [
        'requests'
    ],
    python_requires = '>=3.6'
)
