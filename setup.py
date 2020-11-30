import setuptools

with open("README.md", "r") as readme:
    long_description = readme.read()

setuptools.setup(
    name = "seedsim",
    version = "0.0.2",
    author = "Honghao Zeng",
    author_email = "hozeng@syr.edu",
    description = "SEED Internet Simulator",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/seed-labs/seed-simulator",
    packages = setuptools.find_packages(),
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires = [
        'requests'
    ],
    python_requires = '>=3.6'
)