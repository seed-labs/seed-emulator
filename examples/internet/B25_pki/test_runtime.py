#!/usr/bin/env python3

from __future__ import annotations

from seedemu.testing import ComposeRuntimeTest


def main() -> int:
    test = ComposeRuntimeTest(__file__)

    ca1 = test.require_service(150, "ca1")
    ca2 = test.require_service(150, "ca2")
    web1 = test.require_service(151, "web1")
    web2 = test.require_service(151, "web2")
    client = test.require_service(150, "host_0", "representative PKI client is generated")

    if ca1:
        test.exec_check("CA1 step-ca process is running", ca1, "pgrep step-ca >/dev/null")
        test.exec_check(
            "CA1 ACME directory is reachable",
            ca1,
            "curl -kfsS https://seedCA.net/acme/acme/directory | grep -q 'newNonce'",
            retries=60,
            interval=5,
        )
        test.exec_check(
            "CA1 root certificate is installed locally",
            ca1,
            "test -s /usr/local/share/ca-certificates/SEEDEMU_Internal_Root_CA_0.crt",
        )

    if ca2:
        test.exec_check("CA2 step-ca process is running", ca2, "pgrep step-ca >/dev/null")
        test.exec_check(
            "CA2 ACME directory is reachable",
            ca2,
            "curl -kfsS https://seedCA.com/acme/acme/directory | grep -q 'newNonce'",
            retries=60,
            interval=5,
        )
        test.exec_check(
            "CA2 root certificate is installed locally",
            ca2,
            "test -s /usr/local/share/ca-certificates/SEEDEMU_Internal_Root_CA_1.crt",
        )

    if web1:
        test.structural_check(
            "web1 has the expected fixed address",
            web1.address == "10.151.0.7",
            "observed {}".format(web1.address),
        )
        test.exec_check("web1 nginx process is running", web1, "pgrep nginx >/dev/null")
        test.exec_check(
            "web1 obtained an ACME certificate for example32.com",
            web1,
            "test -s /etc/letsencrypt/live/example32.com/fullchain.pem",
            retries=60,
            interval=5,
        )

    if web2:
        test.structural_check(
            "web2 has the expected fixed address",
            web2.address == "10.151.0.8",
            "observed {}".format(web2.address),
        )
        test.exec_check("web2 nginx process is running", web2, "pgrep nginx >/dev/null")
        test.exec_check(
            "web2 obtained an ACME certificate for bank32.com",
            web2,
            "test -s /etc/letsencrypt/live/bank32.com/fullchain.pem",
            retries=60,
            interval=5,
        )

    if client:
        test.exec_check(
            "client resolves CA and web hostnames through EtcHosts",
            client,
            "getent hosts seedCA.net | grep -q '10.150.' && "
            "getent hosts seedCA.com | grep -q '10.150.' && "
            "getent hosts example32.com | grep -q '10.151.0.7' && "
            "getent hosts bank32.com | grep -q '10.151.0.8'",
        )
        test.exec_check(
            "client trusts example32.com HTTPS certificate",
            client,
            "curl -fsS https://example32.com | grep -q 'Web server at example32.com'",
            retries=60,
            interval=5,
        )
        test.exec_check(
            "client trusts bank32.com HTTPS certificate",
            client,
            "curl -fsS https://bank32.com | grep -q 'Web server at bank32.com'",
            retries=60,
            interval=5,
        )
        test.exec_check(
            "example32.com certificate has expected SAN",
            client,
            "step certificate inspect https://example32.com | grep -q 'DNS:example32.com'",
            retries=30,
            interval=5,
        )
        test.exec_check(
            "bank32.com certificate has expected SAN",
            client,
            "step certificate inspect https://bank32.com | grep -q 'DNS:bank32.com'",
            retries=30,
            interval=5,
        )

    test.write_summary("b25-pki-runtime-test.json")
    return test.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
