"""Domain filter — enforces allowed/blocked navigation lists.

If ``allowed_domains`` is non-empty the agent may **only** navigate to those
domains.  ``blocked_domains`` always takes precedence (block-list wins over
allow-list).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from src.utils.logging import get_logger

logger = get_logger(__name__)


class DomainFilter:
    """Filters navigation requests by domain allow/block lists."""

    def __init__(
        self,
        allowed_domains: list[str] | None = None,
        blocked_domains: list[str] | None = None,
    ) -> None:
        self._allowed: set[str] = {d.lower() for d in (allowed_domains or [])}
        self._blocked: set[str] = {d.lower() for d in (blocked_domains or [])}

    # -- core check --------------------------------------------------------

    def is_allowed(self, url: str) -> bool:
        """Return True if the URL is permitted.

        Rules:
        1. Blocked list always wins — if domain is in blocked → False.
        2. If allowed list is non-empty and domain is NOT in it → False.
        3. Otherwise → True.
        """
        try:
            domain = urlparse(url).netloc.lower()
        except Exception:
            return False

        if not domain:
            return True  # Non-HTTP URLs (about:blank, data:, etc.)

        # Strip port
        domain = re.sub(r":\d+$", "", domain)

        if domain in self._blocked:
            logger.info("domain_blocked", domain=domain, url=url)
            return False

        if self._allowed and domain not in self._allowed:
            logger.info("domain_not_in_allowlist", domain=domain, url=url)
            return False

        return True

    # -- mutation ----------------------------------------------------------

    def add_allowed_domain(self, domain: str) -> None:
        """Add a domain to the allow list."""
        self._allowed.add(domain.lower())

    def remove_allowed_domain(self, domain: str) -> None:
        """Remove a domain from the allow list."""
        self._allowed.discard(domain.lower())

    def add_blocked_domain(self, domain: str) -> None:
        """Add a domain to the block list."""
        self._blocked.add(domain.lower())

    def remove_blocked_domain(self, domain: str) -> None:
        """Remove a domain from the block list."""
        self._blocked.discard(domain.lower())

    # -- introspection -----------------------------------------------------

    def get_lists(self) -> dict[str, list[str]]:
        """Return current allowed and blocked domain lists."""
        return {
            "allowed": sorted(self._allowed),
            "blocked": sorted(self._blocked),
        }
