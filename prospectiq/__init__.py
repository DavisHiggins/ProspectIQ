"""ProspectIQ — open-source lead intelligence and contact enrichment CLI.

ProspectIQ collects publicly available profile information from supported
sources, normalizes it into a single lead schema, enriches it with website and
company-domain analysis, scores it, and exports it to CSV.

The version declared here is the single source of truth for the whole project;
``pyproject.toml`` reads it dynamically and ``prospectiq --version`` prints it.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
