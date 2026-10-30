from __future__ import annotations

import argparse
from pathlib import Path

from .runner import buildCluster, cleanWorkload, deployWorkload, destroyCluster


class K8sTools:
    """User-facing CLI/API for SeedEMU Kubernetes workflows.

    The first-phase implementation intentionally keeps user directories clean:
    setup/running resources are expanded into temporary directories during each
    command and removed afterwards unless --keep-temp is used. Persistent user
    outputs are limited to the requested configK3s.yaml, kubeconfig.yaml, and
    compiler output directory.
    """

    def build(
        self,
        inputConfig: str | Path,
        configK3s: str | Path,
        kubeconfig: str | Path,
        *,
        inventory: str | Path | None = None,
        keepTemp: bool = False,
    ) -> None:
        """Create infrastructure and write K3s access files.

        Args:
            inputConfig: YAML with kind=kvmOvn, physicalOvn, or multiHostKvmOvn.
            configK3s: Output configK3s.yaml path.
            kubeconfig: Output kubeconfig path.
            inventory: Optional output inventory.yaml path.
            keepTemp: Keep temporary setup resources for debugging.
        """
        buildCluster(inputConfig, configK3s, kubeconfig, inventory=inventory, keep_temp=keepTemp)

    def up(
        self,
        outputDir: str | Path,
        kubeconfig: str | Path,
        configK3s: str | Path,
        *,
        imageRegistryPrefix: str | None = None,
        keepTemp: bool = False,
    ) -> None:
        """Build/push images, deploy workload, and wait for readiness.

        Args:
            outputDir: Compile output directory.
            kubeconfig: Kubeconfig path.
            configK3s: configK3s.yaml with registry and network backend data.
            imageRegistryPrefix: Logical compiler image prefix. If omitted,
                it is inferred from images.yaml.
            keepTemp: Keep temporary running resources for debugging.
        """
        deployWorkload(
            outputDir,
            kubeconfig,
            configK3s,
            image_registry_prefix=imageRegistryPrefix,
            keep_temp=keepTemp,
        )

    def down(self, outputDir: str | Path, kubeconfig: str | Path, *, keepTemp: bool = False) -> None:
        """Delete workload resources while keeping cluster infrastructure.

        Args:
            outputDir: Compile output directory.
            kubeconfig: Kubeconfig path.
            keepTemp: Keep temporary cleanup resources for debugging.
        """
        cleanWorkload(outputDir, kubeconfig, keep_temp=keepTemp)

    def clean(self, outputDir: str | Path, kubeconfig: str | Path, *, keepTemp: bool = False) -> None:
        """Delete workload resources while keeping cluster infrastructure.

        Args:
            outputDir: Compile output directory.
            kubeconfig: Kubeconfig path.
            keepTemp: Keep temporary cleanup resources for debugging.
        """
        self.down(outputDir, kubeconfig, keepTemp=keepTemp)

    def destroy(self, configK3s: str | Path, *, keepTemp: bool = False) -> None:
        """Destroy K3s/OVN and optional KVM infrastructure.

        Args:
            configK3s: configK3s.yaml produced by build().
            keepTemp: Keep temporary destroy resources for debugging.
        """
        destroyCluster(configK3s, keep_temp=keepTemp)

    def runCli(self, argv: list[str] | None = None) -> int:
        """Parse and execute the command-line interface.

        Args:
            argv: Optional argv override for tests.
        """
        parser = argparse.ArgumentParser(prog="k8sTools.py")
        sub = parser.add_subparsers(dest="command", required=True)

        build = sub.add_parser("build", help="create KVM/physical K3s + OVN infrastructure")
        build.add_argument("--input", required=True, help="input YAML with explicit kind")
        build.add_argument("--config-k3s", required=True, help="output configK3s.yaml")
        build.add_argument("--kubeconfig", required=True, help="output kubeconfig.yaml")
        build.add_argument("--inventory", help="optional output inventory.yaml with node resources")
        build.add_argument("--keep-temp", action="store_true", help="keep temporary setup resources")

        up = sub.add_parser("up", help="build images and deploy workload")
        up.add_argument("-f", "--folder", required=True, help="compile output directory")
        up.add_argument("-k", "--kubeconfig", required=True, help="kubeconfig.yaml")
        up.add_argument("-d", "--config-k3s", required=True, help="configK3s.yaml")
        up.add_argument(
            "--image-registry-prefix",
            help="logical compiler image prefix; inferred from images.yaml when omitted",
        )
        up.add_argument("--keep-temp", action="store_true", help="keep temporary running resources")

        down = sub.add_parser("down", help="delete workload resources only")
        down.add_argument("-f", "--folder", required=True, help="compile output directory")
        down.add_argument("-k", "--kubeconfig", required=True, help="kubeconfig.yaml")
        down.add_argument("--keep-temp", action="store_true", help="keep temporary cleanup resources")

        clean = sub.add_parser("clean", help="delete workload resources only")
        clean.add_argument("-f", "--folder", required=True, help="compile output directory")
        clean.add_argument("-k", "--kubeconfig", required=True, help="kubeconfig.yaml")
        clean.add_argument("--keep-temp", action="store_true", help="keep temporary cleanup resources")

        destroy = sub.add_parser("destroy", help="destroy cluster and optional KVM resources")
        destroy.add_argument("-d", "--config-k3s", required=True, help="configK3s.yaml")
        destroy.add_argument("--keep-temp", action="store_true", help="keep temporary destroy resources")

        args = parser.parse_args(argv)
        if args.command == "build":
            self.build(args.input, args.config_k3s, args.kubeconfig, inventory=args.inventory, keepTemp=args.keep_temp)
        elif args.command == "up":
            self.up(
                args.folder,
                args.kubeconfig,
                args.config_k3s,
                imageRegistryPrefix=args.image_registry_prefix,
                keepTemp=args.keep_temp,
            )
        elif args.command == "down":
            self.down(args.folder, args.kubeconfig, keepTemp=args.keep_temp)
        elif args.command == "clean":
            self.clean(args.folder, args.kubeconfig, keepTemp=args.keep_temp)
        elif args.command == "destroy":
            self.destroy(args.config_k3s, keepTemp=args.keep_temp)
        else:
            parser.error(f"unsupported command: {args.command}")
        return 0
