# Dev Container

Offical website: https://containers.dev/

## What are Development Containers?

A development container (or dev container for short) allows you to use a container as a full-featured development environment. It can be used to run an application, to separate tools, libraries, or runtimes needed for working with a codebase, and to aid in continuous integration and testing. Dev containers can be run locally or remotely, in a private or public cloud, in a variety of supporting tools and editors.

## Build & Deploy

A development container defines an environment in which you develop your application before you are ready to deploy. While deployment and development containers may resemble one another, you may not want to include tools in a deployment image that you use during development.

![](https://containers.dev/img/dev-container-stages.png)

In our case, seed-emulator program will be run inside a dev container. The generated files under the output folder will be used to build a production container to run the emulation.

## CI

Beyond repeatable setup, these same development containers provide consistency to avoid environment specific problems across developers and centralized build and test automation services. The open-source CLI reference implementation can either be used directly or integrated into product experience to use the structured metadata to deliver these benefits. It currently supports integrating with Docker Compose and a simplified, un-orchestrated single container option – so that they can be used as coding environments or for continuous integration and testing.

A GitHub Action is available in [devcontainers/ci](https://github.com/devcontainers/ci) for running a repository’s dev container in continuous integration (CI) builds. This allows you to reuse the same setup that you are using for local development to also build and test your code in CI.

## Supported Tools

Click on the link to view respective documentation.
Go to https://containers.dev/supporting.html for more information.

### Editors

- [Visual Studio Code](https://code.visualstudio.com/docs/devcontainers/containers)
- [PyCharm](https://www.jetbrains.com/help/pycharm/connect-to-devcontainer.html)

### Tools

- [Dev Container CLI](https://containers.dev/supporting#devcontainer-cli)
- [VS Code extension CLI](https://containers.dev/supporting#dev-containers-cli)
- [Cachix devenv](https://containers.dev/supporting#cachix-devenv)
- [Jetpack.io Devbox](https://containers.dev/supporting#jetpack-io-devbox)
- [VS Code Dev Containers extension](https://containers.dev/supporting#dev-containers)

### Services

- [GitHub Codespaces](https://containers.dev/supporting.html#github-codespaces)
- [CodeSandbox](https://containers.dev/supporting.html#codesandbox)
- [DevPod](https://containers.dev/supporting.html#devpod)

## Quick Start using VS Code

Clone the repository and open it in VS Code.

Click on [Install the Dev Containers extension](vscode:extension/ms-vscode-remote.remote-containers)

Press `Ctrl/Cmd + Shift + P` to open the command palette.

Type `Remote-Containers: Reopen in Container` and click on it.

## Quick Start using Github Codespaces

https://docs.github.com/en/codespaces/developing-in-a-codespace/creating-a-codespace-for-a-repository
