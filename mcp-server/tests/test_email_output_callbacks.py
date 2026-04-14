import os
import tempfile
import unittest
from pathlib import Path

from seedemu.core.Compiler import Compiler
from seedemu.core.Emulator import Emulator
from seedemu.services.EmailService import EmailService


class _RenderedEmulator:
    def rendered(self) -> bool:
        return True


class _DummyCompiler(Compiler):
    def getName(self) -> str:
        return "Dummy"

    def _doCompile(self, emulator):
        Path("docker-compose.yml").write_text("services: {}\n", encoding="utf-8")


class TestEmailOutputCallbacks(unittest.TestCase):
    def test_update_output_directory_uses_last_compile_output_dir(self):
        compiler = _DummyCompiler()
        service = EmailService()
        service.add_provider(
            domain="example.com",
            asn=150,
            ip="10.150.0.10",
            gateway="10.150.0.254",
        )
        emulator = Emulator()

        previous_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as workdir, tempfile.TemporaryDirectory() as tempdir:
            output_dir = os.path.join(tempdir, "output")
            try:
                os.chdir(workdir)
                compiler.compile(_RenderedEmulator(), output_dir, override=True)
                result = emulator.updateOutputDirectory(compiler, service.get_output_callbacks())
            finally:
                os.chdir(previous_cwd)

            self.assertIs(result, emulator)
            self.assertTrue(
                os.path.exists(
                    os.path.join(output_dir, "mail-example-com_wrapper", "Dockerfile")
                )
            )
            self.assertFalse(
                os.path.exists(
                    os.path.join(workdir, "mail-example-com_wrapper", "Dockerfile")
                )
            )


if __name__ == "__main__":
    unittest.main()
