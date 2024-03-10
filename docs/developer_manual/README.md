# Developer Manual for the SEED Emulator

- [Creating a new layer](./00-creating-a-new-layer.md)
- [Creating a new service](./01-creating-a-new-service.md)
- [Creating a new component](./02-creating-a-new-component.md)
- [Creating a new rap](./03-createing-a-new-rap.md)
- [Creating a test suite](./04-create-test-suites.md)
- FAQs
    - [How to get ip address](./99-FAQs.md#Q01-how-to-get-ip-address)
    - [How to make a change on all nodes](./99-FAQs.md#Q02-how-to-make-a-change-on-all-nodes)

---

# Contributing to SEED Emulator

Thank you for considering contributing to SEED Emulator! We appreciate your interest in making our open-source project better.

## How Can You Contribute?

There are several ways you can contribute to SEED emulator:

1. **Code Contributions**: You can contribute code to improve the functionality of the package, fix bugs, or add new features. 
2. **Documentation Improvements**: Help us improve the documentation by fixing typos, clarifying explanations, or adding examples.
3. **Issue Reporting**: If you encounter a bug or have a suggestion for improvement, please open an issue on our GitHub repository.
4. **Feature Requests**: If you have an idea for a new feature or enhancement, feel free to open a feature request issue.
5. **Testing**: Assist us by testing the package, reporting bugs, or suggesting improvements.

## Getting Started

1. **Fork the Repository**: Fork the `seed-emulator` repository on GitHub by clicking the "Fork" button.
2. **Clone the Repository**: Clone your fork of the repository to your local machine using `git clone`.
3. **Switch to the Development Branch**: Checkout the development branch of the repository using `git checkout development`.
4. **Create a Branch**: Create a new branch for your contribution using `git checkout -b branch-name`.
5. **Make Changes**: Make changes to the codebase, documentation, or any other relevant files.
6. **Write Tests**: Write test code to verify the functionality of your changes thoroughly. ([details](./04-create-test-suites.md))
7. **Run Tests**: Execute the test suite to ensure that your changes pass all existing tests. ([how to run existing tests](../../test/README.md))
8. **Update Documentation**: Update the documentation to reflect any changes or additions.
9. **Commit Changes**: Commit your changes with descriptive commit messages using `git commit`.
10. **Push Changes**: Push your changes to your fork on GitHub with `git push`.
11. **Open a Pull Request**: Go to the GitHub page of your fork and open a pull request to the development branch of the main repository.
12. **Provide Test Code and Results**: Include the test code you've written and the results of running the test suite in your pull request description.
13. **Discuss and Review**: Engage in discussion and iterate on your changes through comments and feedback from maintainers and other contributors.
14. **Merge Changes**: Once your pull request is approved and passes all tests, it will be merged into the development branch of the main repository.

## Code Style and Guidelines

Please follow these guidelines when contributing code to `seed-emulator`:

- **Docstrings**: Document your code using clear and concise docstrings following the numpydoc format.
- **Testing**: Write comprehensive unit tests for your code using the `unittest` framework.
- **Modularity**: Keep your changes modular and avoid unnecessary dependencies.
- **Compatibility**: Ensure your code is compatible with the supported Python versions.


## Licensing

By contributing to `SEED Emulator`, you agree that your contributions will be licensed under the [LICENSE](../../LICENSE.txt) of the project.


<!-- ## Layer 
Layer classes make changes to the emulation as a whole. The characteristic of base layers is that they provide the basics to support the emulation and higher-level layers.

## Service
Service layers will typically only make changes to individual nodes.  -->


<!-- ## vnode, vpnode, and pnode -->
<!-- 
Service::install

Service::configure(self, emulator:Emulator)
-> Service::__configureServer(server:Server, node:Node)
-> Service::_doConfigure(self, node:Node, server:Server) : configure server. By default, this does nothing.

Service::render
-> Service::_doInstall(self, node:Node, server:Server) # install the server on node.


when rendering an emulator by calling the Emulator::render() method, the emulator will be rendered after going through confiugration phase internally. -->
