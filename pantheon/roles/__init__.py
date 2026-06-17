"""Built-in Pantheon roles (the gods)."""

from pantheon.roles.apollo import Apollo
from pantheon.roles.athena import Athena
from pantheon.roles.chronos import Chronos
from pantheon.roles.hephaestus import Hephaestus

_BUILTIN_ROLES = {
    "hephaestus": Hephaestus,
    "athena": Athena,
    "apollo": Apollo,
    "chronos": Chronos,
}


def register_default_roles() -> dict:
    """Return the dict of built-in role classes."""
    return dict(_BUILTIN_ROLES)


__all__ = [
    "Hephaestus",
    "Athena",
    "Apollo",
    "Chronos",
    "register_default_roles",
]
