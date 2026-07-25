"""Centralized configuration loading.

All runtime configuration enters the application through :func:`load_config`.
Nothing else in the codebase reads ``os.environ`` directly, which keeps the
settings surface small enough to document and test.

Environment variables use the ``PROSPECTIQ_`` prefix. For users migrating from
the upstream Scout project, the matching ``SCOUT_`` variable is still accepted
as a deprecated fallback and emits a one-time, non-blocking warning.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from prospectiq.constants import (
    DEFAULT_DELAY_MAX,
    DEFAULT_DELAY_MIN,
    DEFAULT_OUTPUT_DIR,
    ENV_FILE_NAME,
    ENV_PREFIX,
    LEGACY_ENV_PREFIX,
    MIN_ALLOWED_DELAY,
    SOURCE_DELAYS,
)

#: Settings whose legacy ``SCOUT_``-prefixed spelling is still honoured.
DEPRECATED_ALIASES: tuple[str, ...] = (
    "PROXY",
    "PROXY_FILE",
    "FREE_PROXY",
    "DELAY_MIN",
    "DELAY_MAX",
)

#: Unprefixed names kept because they are vendor settings, not project
#: settings. ``PROSPECTIQ_``-prefixed spellings take precedence.
VENDOR_ALIASES: dict[str, str] = {
    "LINKEDIN_COOKIE": "LINKEDIN_COOKIE",
    "HUNTER_API_KEY": "HUNTER_API_KEY",
}

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})

#: Deprecation notices collected during loading, surfaced once by the CLI.
_warnings: list[str] = []


def get_deprecation_warnings() -> list[str]:
    """Return deprecation notices raised while loading configuration."""
    return list(_warnings)


def _reset_warnings() -> None:
    """Clear collected warnings. Used by :func:`load_config` and by tests."""
    _warnings.clear()


def _read_env(name: str, default: str = "") -> str:
    """Read a setting, falling back to its deprecated ``SCOUT_`` spelling.

    Args:
        name: Unprefixed setting name, e.g. ``"PROXY"``.
        default: Value returned when neither spelling is set.

    Returns:
        The configured value, or ``default``.
    """
    current = os.environ.get(f"{ENV_PREFIX}{name}", "").strip()
    if current:
        return current

    if name in DEPRECATED_ALIASES:
        legacy = os.environ.get(f"{LEGACY_ENV_PREFIX}{name}", "").strip()
        if legacy:
            _warnings.append(
                f"{LEGACY_ENV_PREFIX}{name} is deprecated and will be removed in a "
                f"future release. Rename it to {ENV_PREFIX}{name}."
            )
            return legacy

    if name in VENDOR_ALIASES:
        vendor = os.environ.get(VENDOR_ALIASES[name], "").strip()
        if vendor:
            return vendor

    return default


def _read_bool(name: str, default: bool = False) -> bool:
    """Read a boolean setting."""
    raw = _read_env(name)
    if not raw:
        return default
    return raw.lower() in _TRUE_VALUES


def _read_float(name: str, default: float) -> float:
    """Read a float setting, falling back to ``default`` when unparseable."""
    raw = _read_env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        _warnings.append(f"{ENV_PREFIX}{name}={raw!r} is not a number; using {default}.")
        return default


@dataclass(frozen=True)
class Config:
    """Immutable snapshot of runtime configuration.

    Attributes:
        proxy_url: Single proxy URL, or empty for none.
        proxy_file: Path to a newline-delimited proxy list, or ``None``.
        use_free_proxy: Whether to source free public proxies (unreliable).
        delay_min: Lower bound of the inter-request delay, in seconds.
        delay_max: Upper bound of the inter-request delay, in seconds.
        delay_explicitly_set: True when the user configured a delay, which
            suppresses the per-source delay defaults.
        linkedin_cookie: LinkedIn ``li_at`` session cookie, or empty.
        hunter_api_key: Optional Hunter.io key for supplemental lookups.
        output_dir: Directory that CSV exports are written to.
        smtp_verify: Whether to attempt SMTP existence checks on candidates.
        update_check: Whether to query the releases API on startup.
        no_color: Whether colored terminal output is disabled.
    """

    proxy_url: str = ""
    proxy_file: Path | None = None
    use_free_proxy: bool = False
    delay_min: float = DEFAULT_DELAY_MIN
    delay_max: float = DEFAULT_DELAY_MAX
    delay_explicitly_set: bool = False
    linkedin_cookie: str = ""
    hunter_api_key: str = ""
    output_dir: Path = field(default_factory=lambda: Path(DEFAULT_OUTPUT_DIR))
    smtp_verify: bool = True
    update_check: bool = False
    no_color: bool = False

    @property
    def proxy_mode(self) -> str:
        """Describe the active proxy strategy: custom, file, free, or none."""
        if self.proxy_url:
            return "custom"
        if self.proxy_file:
            return "file"
        if self.use_free_proxy:
            return "free"
        return "none"

    def delay_for(self, source: str) -> tuple[float, float]:
        """Return the ``(min, max)`` request delay to use for a source.

        An explicit user setting always wins. Otherwise the per-source default
        from :data:`~prospectiq.constants.SOURCE_DELAYS` applies.
        """
        if self.delay_explicitly_set:
            return (self.delay_min, self.delay_max)
        return SOURCE_DELAYS.get(source, (self.delay_min, self.delay_max))

    def has_linkedin_cookie(self) -> bool:
        """Whether a LinkedIn session cookie is configured."""
        return bool(self.linkedin_cookie.strip())


def load_dotenv(path: Path | None = None) -> None:
    """Load ``KEY=VALUE`` pairs from a ``.env`` file into the environment.

    Existing environment variables always win, so a shell export overrides the
    file. Missing or malformed files are ignored rather than raising.

    Args:
        path: Explicit ``.env`` location. Defaults to ``./.env``.
    """
    env_path = path or Path.cwd() / ENV_FILE_NAME
    if not env_path.is_file():
        return

    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError:
        return

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def load_config(*, load_env_file: bool = True, env_path: Path | None = None) -> Config:
    """Build a :class:`Config` from the environment.

    Args:
        load_env_file: Read ``.env`` before inspecting the environment.
        env_path: Explicit ``.env`` location.

    Returns:
        A validated, immutable configuration snapshot.
    """
    _reset_warnings()

    if load_env_file:
        load_dotenv(env_path)

    proxy_file_raw = _read_env("PROXY_FILE")
    proxy_file: Path | None = None
    if proxy_file_raw:
        candidate = Path(proxy_file_raw).expanduser()
        if candidate.is_file():
            proxy_file = candidate
        else:
            _warnings.append(f"Proxy file not found: {candidate}")

    delay_min_set = bool(_read_env("DELAY_MIN"))
    delay_max_set = bool(_read_env("DELAY_MAX"))
    delay_min = _read_float("DELAY_MIN", DEFAULT_DELAY_MIN)
    delay_max = _read_float("DELAY_MAX", DEFAULT_DELAY_MAX)

    # Guard against inverted or unreasonably aggressive pacing.
    delay_min = max(delay_min, MIN_ALLOWED_DELAY)
    if delay_max < delay_min:
        _warnings.append(
            f"Delay max ({delay_max}s) is below delay min ({delay_min}s); "
            f"using {delay_min}s for both."
        )
        delay_max = delay_min

    output_dir_raw = _read_env("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)

    return Config(
        proxy_url=_read_env("PROXY"),
        proxy_file=proxy_file,
        use_free_proxy=_read_bool("FREE_PROXY"),
        delay_min=delay_min,
        delay_max=delay_max,
        delay_explicitly_set=delay_min_set or delay_max_set,
        linkedin_cookie=_read_env("LINKEDIN_COOKIE"),
        hunter_api_key=_read_env("HUNTER_API_KEY"),
        output_dir=Path(output_dir_raw).expanduser(),
        smtp_verify=_read_bool("SMTP_VERIFY", default=True),
        update_check=_read_bool("UPDATE_CHECK", default=False),
        no_color=bool(os.environ.get("NO_COLOR", "").strip()),
    )
