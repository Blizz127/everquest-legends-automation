"""Read-only login-host inspection and explicit private-target binding.

Future live adapters must call require_private_target before opening input.
This module does not connect to a server or change a client configuration.
"""
from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from .client_ingest import sha256_file


OFFICIAL_SUFFIXES = (".everquestlegends.com", ".daybreakgames.com")
OFFICIAL_HOSTS = {"everquestlegends.com", "daybreakgames.com"}


@dataclass(frozen=True)
class LoginTarget:
    host: str
    port: int
    eqhost_sha256: str
    official_domain: bool


def inspect_eqhost(path: Path) -> LoginTarget:
    parser = ConfigParser(interpolation=None)
    with path.open(encoding="latin-1") as stream:
        parser.read_file(stream)
    endpoint = parser.get("LoginServer", "Host", fallback="").strip()
    host, separator, port_text = endpoint.rpartition(":")
    if not separator or not host or not port_text.isdigit():
        raise ValueError("eqhost.txt has no valid LoginServer Host:port")
    host = host.casefold().rstrip(".")
    port = int(port_text)
    if not 1 <= port <= 65535:
        raise ValueError("Invalid login port")
    official = host in OFFICIAL_HOSTS or host.endswith(OFFICIAL_SUFFIXES)
    return LoginTarget(host, port, sha256_file(path), official)


def require_private_target(actual: LoginTarget, *, expected_host: str,
                           expected_port: int, expected_eqhost_sha256: str) -> None:
    """Fail closed unless a candidate matches a separately reviewed binding."""

    if actual.official_domain:
        raise PermissionError("Login host is Daybreak official, not a private target")
    if (actual.host != expected_host.casefold().rstrip(".") or
            actual.port != expected_port or
            actual.eqhost_sha256 != expected_eqhost_sha256.lower()):
        raise PermissionError("Private login host does not match reviewed target binding")
