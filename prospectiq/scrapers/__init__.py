"""Source scrapers.

Each module collects from one public source and returns a raw record. Use
:func:`~prospectiq.scrapers.registry.collect` rather than calling a scraper
directly — it normalizes the result into a :class:`~prospectiq.models.Lead`.
"""

from prospectiq.scrapers.registry import SOURCES, Source, collect, get_source, source_keys

__all__ = ["SOURCES", "Source", "collect", "get_source", "source_keys"]
