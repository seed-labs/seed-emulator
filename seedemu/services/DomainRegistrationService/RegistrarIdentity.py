from dataclasses import dataclass
import re
from urllib.parse import SplitResult, urlsplit


@dataclass(frozen=True)
class RegistrarIdentity:
    """Shared public identity used by Loom, Registrar RDDS.

    Attributes:
        name: Human-readable Registrar name.
        company_name: Legal or display name shown by Loom.
        domain: Registrar application domain, without a URL scheme.
        iana_id: Numeric Registrar identifier advertised by RDDS.
        url: Public Registrar HTTP(S) URL.
        whois_host: Public Registrar WHOIS hostname.
        rdap_url: Public Registrar RDAP base URL.
        email: General contact email address.
        phone: General contact telephone number.
        address: Postal address displayed by the Registrar.
        country_code: Two-letter uppercase country code.
        abuse_email: Abuse contact email address.
        abuse_phone: Abuse contact telephone number.
    """

    name: str
    company_name: str
    domain: str
    iana_id: int
    url: str
    whois_host: str
    rdap_url: str
    email: str
    phone: str
    address: str
    country_code: str
    abuse_email: str
    abuse_phone: str

    def __post_init__(self) -> None:
        """Validate identity fields immediately after dataclass construction."""
        values = {
            field: value
            for field, value in self.__dict__.items()
            if isinstance(value, str)
        }
        assert all(values.values()), "Registrar identity values cannot be empty"
        assert all(
            "\n" not in value and "\r" not in value for value in values.values()
        ), "Registrar identity values cannot contain newlines"
        hostname = re.compile(
            r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?\Z"
        )
        assert hostname.fullmatch(self.domain), "invalid Registrar domain"
        assert hostname.fullmatch(self.whois_host), "invalid Registrar WHOIS host"
        assert 0 <= self.iana_id <= 99999, "invalid Registrar IANA id"
        assert re.fullmatch(r"[A-Z]{2}", self.country_code), (
            "invalid Registrar country code"
        )
        for label, address in {
            "email": self.email,
            "abuse email": self.abuse_email,
        }.items():
            assert re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", address), (
                "invalid Registrar {}".format(label)
            )
        self._parse_url(self.url, "URL")
        self._parse_url(self.rdap_url, "RDAP URL")

    @staticmethod
    def _parse_url(value: str, label: str) -> SplitResult:
        """Validate an HTTP(S) URL and return its parsed representation."""
        parsed = urlsplit(value)
        assert parsed.scheme in {"http", "https"}, (
            "Registrar {} must use HTTP or HTTPS".format(label)
        )
        assert parsed.hostname is not None, "invalid Registrar {}".format(label)
        assert parsed.username is None and parsed.password is None, (
            "Registrar {} cannot contain user information".format(label)
        )
        try:
            parsed.port
        except ValueError as error:
            raise AssertionError("invalid Registrar {} port".format(label)) from error
        return parsed

    @property
    def rdap_host(self) -> str:
        """Return the hostname expected by Loom's ``RDAP_SERVER`` setting."""
        parsed = self._parse_url(self.rdap_url, "RDAP URL")
        assert parsed.hostname is not None
        return parsed.hostname


__all__ = ["RegistrarIdentity"]
