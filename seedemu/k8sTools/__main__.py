"""Allow ``python -m seedemu.k8sTools`` to run the K8sTools CLI."""

from .k8sTools import K8sTools


if __name__ == "__main__":
    raise SystemExit(K8sTools().runCli())
