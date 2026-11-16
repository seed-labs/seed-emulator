#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)
    host = test.require_service(152, "host0")

    if host:
        test.exec_check(
            "Imported program exists",
            host,
            "test -f /myprog.py",
        )
        test.exec_check(
            "Generated file content is preserved",
            host,
            "grep -qx hello.world /file.txt",
        )
        test.exec_check(
            "Installed Python executes imported program",
            host,
            "python3 /myprog.py | grep -qx Hello.World!",
        )

    test.write_summary("a09-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
