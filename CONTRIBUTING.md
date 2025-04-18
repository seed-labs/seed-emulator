# Contributing to SEEDEmulator Project

Thanks for checking out the SEEDEmulator project! We're excited to hear and
learn from you. We've put together the following guidelines to help you
figure out where you can best be helpful.


## Table of Contents

1. [How to contribute](#how-to-contribute)
1. [Community](#community)

## How to Contribute

- **Adding new elements**. We will be actively developing new elements
  useful for Internet emulation. For example, recently we have added
  DNS, Botnet, Darknet components, and we are currently developing blockchain
  components. It is these components that will make the emulator
  more interesting and more useful.

- **Improving existing elements**: Some of the elements are currently quite rudimentary, and
  rich features need to be added. You can help us propose and implement
  new features to those elements.

- **Building more complicated emulation**: The Internet emulators built by the
  current examples included in the project are quite small. It will be useful if we can build
  more complicated examples, and share them as components, so others
  can use these components to build their emulators. In the future, we can
  create a market place so people can share or trade their emulators.

- **Testing**. We definitely need more people to help test
  the code and provide feedback. You can create issues to tell us
  about the bugs and feedback.

- **Developing lab exercises**. The emulator created from this project is
  intended for being used as a platform for lab exercises, especially in
  the field of cybersecurity and networking. The proposed lab ideas
  can be found in the [labs/](./labs/) folder. You can help develop
  these labs or propose new ideas.

## Running Linters and Code Formatters

- **flake8** checks compliance with the PEP 8 style guide. You can invoke it
  globally by running `flake8` in the root of the repository or pass individual
  files to check. If you are using VS Code, there is also a flake8 plugin
  running the linter continuously in the background.
- **black** formats files or sections of code to comply with its style guideline
  and should fix most formatting errors that flake8 points out. You can invoke
  `black` on the command line with the path to a file to format. There are also
  editor plugins that allow formatting code selections easily.
- **mypy** is a static type checker that makes sure Python type annotations are
  correct. Running `mypy` in the root of the repository checks all modules in
  `seedemu`. See the [mypy documentation][mypy-cli] on how to check individual
  files or modules on the command line.

[mypy-cli]: https://mypy.readthedocs.io/en/stable/command_line.html

## Community

Discussions about the Open Source Guides take place on
this repository's [Issues](https://github.com/seed-labs/SEEDEmulator/issues) and [Pull Requests](https://github.com/seed-labs/SEEDEmulator/pulls) sections. Anybody is welcome to join these conversations.

Wherever possible, do not take these conversations to private channels, including contacting the maintainers directly. Keeping communication public means everybody can benefit and learn from the conversation.
