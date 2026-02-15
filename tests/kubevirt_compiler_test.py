#!/usr/bin/env python3

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
import yaml

from seedemu.compiler import KubernetesCompiler
from seedemu.core import Emulator, Binding, Filter, Node
from seedemu.core.enums import NodeRole
from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService


class KubeVirtCompilerTest(unittest.TestCase):
    def _build_emulator(self, include_extra_commands: bool = False) -> Emulator:
        emulator = Emulator()
        base = Base()
        routing = Routing()
        ebgp = Ebgp()
        web = WebService()

        base.createInternetExchange(100)

        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        router150 = as150.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
        router150.setVirtualizationMode("KubeVirt")
        if include_extra_commands:
            router150.appendStartCommand("sleep 5", True)
            router150.appendStartCommand(
                "echo post-config > /tmp/post-config",
                isPostConfigCommand=True,
            )

        as150.createHost("web").joinNetwork("net0")
        web.install("web150")
        emulator.addBinding(Binding("web150", filter=Filter(nodeName="web", asn=150)))

        as151 = base.createAutonomousSystem(151)
        as151.createNetwork("net0")
        as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
        as151.createHost("web").joinNetwork("net0")
        web.install("web151")
        emulator.addBinding(Binding("web151", filter=Filter(nodeName="web", asn=151)))

        ebgp.addRsPeer(100, 150)
        ebgp.addRsPeer(100, 151)

        emulator.addLayer(base)
        emulator.addLayer(routing)
        emulator.addLayer(ebgp)
        emulator.addLayer(web)
        emulator.render()

        return emulator

    def _compile_and_read_manifest(self, emulator: Emulator) -> str:
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp_dir:
            compiler = KubernetesCompiler(
                registry_prefix="",
                namespace="seedemu-test",
                use_multus=True,
                internetMapEnabled=False,
                image_pull_policy="IfNotPresent",
            )
            try:
                emulator.compile(compiler, tmp_dir, override=True)
            finally:
                os.chdir(original_cwd)

            manifest_path = os.path.join(tmp_dir, "k8s.yaml")
            with open(manifest_path, "r", encoding="utf-8") as manifest_file:
                return manifest_file.read()

    def _extract_vm_manifest(self, manifest_text: str) -> dict:
        for document in manifest_text.split("\n---\n"):
            stripped = document.strip()
            if not stripped.startswith("{"):
                continue

            parsed = json.loads(stripped)
            if parsed.get("kind") == "VirtualMachine":
                return parsed

        raise AssertionError("VirtualMachine manifest not found")

    def _extract_cloud_init(self, manifest_text: str, vm_manifest: dict) -> dict:
        volumes = vm_manifest["spec"]["template"]["spec"]["volumes"]
        secret_name = None
        for volume in volumes:
            if volume.get("name") == "cloudinitdisk":
                secret_name = volume["cloudInitNoCloud"]["secretRef"]["name"]
                break

        if not secret_name:
            raise AssertionError("cloudinitdisk volume not found")

        for document in manifest_text.split("\n---\n"):
            stripped = document.strip()
            if not stripped.startswith("{"):
                continue

            parsed = json.loads(stripped)
            if parsed.get("kind") != "Secret":
                continue

            if parsed["metadata"].get("name") != secret_name:
                continue

            cloud_init_text = parsed["stringData"]["userdata"]
            return yaml.safe_load(cloud_init_text.replace("#cloud-config\n", "", 1))

        raise AssertionError("cloud-init secret not found")

    def test_hybrid_output_contains_deployment_and_vm(self):
        emulator = self._build_emulator()
        manifest_text = self._compile_and_read_manifest(emulator)

        self.assertIn('"kind": "Deployment"', manifest_text)
        self.assertIn('"kind": "VirtualMachine"', manifest_text)

    def test_cloud_init_includes_fork_and_post_config_commands(self):
        emulator = self._build_emulator(include_extra_commands=True)
        manifest_text = self._compile_and_read_manifest(emulator)
        vm_manifest = self._extract_vm_manifest(manifest_text)
        cloud_init = self._extract_cloud_init(manifest_text, vm_manifest)

        self.assertEqual(vm_manifest["spec"]["runStrategy"], "Always")
        self.assertIn(["/usr/local/bin/replace_address.sh"], cloud_init["runcmd"])
        self.assertIn(["sh", "-c", "sleep 5 &"], cloud_init["runcmd"])
        self.assertIn(["sh", "-c", "echo post-config > /tmp/post-config"], cloud_init["runcmd"])

    def test_unsupported_import_file_fails_fast_for_kubevirt(self):
        emulator = self._build_emulator()
        base_layer = emulator.getLayer("Base")
        router150 = base_layer.getAutonomousSystem(150).getRouter("router0")
        temporary_file = tempfile.NamedTemporaryFile("w", delete=False)
        temporary_file.write("unsupported")
        temporary_file.close()
        router150.importFile(temporary_file.name, "/tmp/unsupported")
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmp_dir:
            compiler = KubernetesCompiler(
                registry_prefix="",
                namespace="seedemu-test",
                use_multus=True,
                internetMapEnabled=False,
                image_pull_policy="IfNotPresent",
            )
            with self.assertRaises(AssertionError):
                try:
                    emulator.compile(compiler, tmp_dir, override=True)
                finally:
                    os.chdir(original_cwd)

        os.unlink(temporary_file.name)

    def test_copy_settings_preserves_virtualization_mode(self):
        source_node = Node("source", NodeRole.Host, 150)
        target_node = Node("target", NodeRole.Host, 150)

        source_node.setVirtualizationMode("KubeVirt")
        target_node.copySettings(source_node)

        self.assertEqual(target_node.getVirtualizationMode(), "KubeVirt")


class KubeVirtRuntimeProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        hybrid_script = Path(__file__).resolve().parents[1] / "examples" / "kubernetes" / "k8s_hybrid_kubevirt_demo.py"
        spec = importlib.util.spec_from_file_location("k8s_hybrid_kubevirt_demo", hybrid_script)
        if spec is None or spec.loader is None:
            raise RuntimeError("Failed to load k8s_hybrid_kubevirt_demo module")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.hybrid_module = module

    def test_auto_profile_degrades_on_arm_without_kvm(self):
        profile, reason = self.hybrid_module.resolve_runtime_profile(
            "auto",
            {"arch": "arm64", "has_kvm": False},
        )
        self.assertEqual(profile, "degraded")
        self.assertIn("arm64", reason)

    def test_auto_profile_full_on_x86_without_kvm(self):
        profile, reason = self.hybrid_module.resolve_runtime_profile(
            "auto",
            {"arch": "x86_64", "has_kvm": False},
        )
        self.assertEqual(profile, "full")
        self.assertIn("auto", reason)

    def test_strict_profile_rejects_arm_without_kvm(self):
        with self.assertRaises(RuntimeError):
            self.hybrid_module.resolve_runtime_profile(
                "strict",
                {"arch": "arm64", "has_kvm": False},
            )

    def test_apply_router_profile_switches_mode(self):
        router = Node("router0", NodeRole.Router, 150)

        mode_degraded = self.hybrid_module.apply_router_profile(router, "degraded")
        self.assertEqual(mode_degraded, "Container")
        self.assertEqual(router.getVirtualizationMode(), "Container")

        mode_full = self.hybrid_module.apply_router_profile(router, "full")
        self.assertEqual(mode_full, "KubeVirt")
        self.assertEqual(router.getVirtualizationMode(), "KubeVirt")


if __name__ == "__main__":
    unittest.main()
