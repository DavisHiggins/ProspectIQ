"""Email, phone, and number extraction."""

from __future__ import annotations

import pytest

from prospectiq.utilities.text import (
    extract_email,
    extract_emails,
    extract_phone,
    extract_urls,
    is_valid_email,
    parse_abbreviated_number,
    strip_html,
    truncate,
)


class TestEmailExtraction:
    def test_finds_a_plain_address(self) -> None:
        assert extract_email("Reach me at hello@example.org please") == "hello@example.org"

    def test_finds_an_address_with_plus_and_dots(self) -> None:
        text = "contact first.last+tag@sub.example.co.uk"

        assert extract_email(text) == "first.last+tag@sub.example.co.uk"

    def test_returns_empty_when_absent(self) -> None:
        assert extract_email("no contact details here") == ""

    @pytest.mark.parametrize("text", ["", None])
    def test_handles_empty_input(self, text: str) -> None:
        assert extract_email(text) == ""

    def test_returns_addresses_in_order(self) -> None:
        text = "primary@example.org and secondary@example.net"

        assert extract_emails(text) == ["primary@example.org", "secondary@example.net"]

    def test_deduplicates_case_insensitively(self) -> None:
        text = "Hello@example.org and hello@example.org"

        assert extract_emails(text) == ["Hello@example.org"]

    @pytest.mark.parametrize(
        "address",
        [
            "someone@example.com",
            "test@test.com",
            "noreply@sentry.io",
            "a@wixpress.com",
            "x@w3.org",
        ],
    )
    def test_rejects_placeholder_and_service_domains(self, address: str) -> None:
        assert is_valid_email(address) is False

    def test_rejects_asset_filenames(self) -> None:
        """The email regex matches things like sprite@2x.png by accident."""
        assert is_valid_email("sprite@2x.png") is False

    def test_filters_blacklisted_domains_from_results(self) -> None:
        text = "real@business.org and fake@example.com"

        assert extract_emails(text) == ["real@business.org"]

    def test_accepts_a_normal_business_address(self) -> None:
        assert is_valid_email("sales@acme-corp.io") is True


class TestPhoneExtraction:
    def test_finds_a_us_number_with_parentheses(self) -> None:
        assert extract_phone("Call (704) 555-0142 today") == "(704) 555-0142"

    def test_finds_a_number_with_country_code(self) -> None:
        assert extract_phone("Ring +1 704-555-0142") == "+1 704-555-0142"

    def test_prefers_tel_links_over_free_text(self) -> None:
        html = '<p>Est. 2010 555-1234</p><a href="tel:+17045550142">Call</a>'

        assert extract_phone(html) == "+17045550142"

    def test_reads_whatsapp_links(self) -> None:
        assert extract_phone('<a href="https://wa.me/17045550142">chat</a>') == "+17045550142"

    def test_returns_empty_when_absent(self) -> None:
        assert extract_phone("no numbers to speak of") == ""

    def test_ignores_numbers_that_are_too_short(self) -> None:
        assert extract_phone("call 555-1234") == ""

    def test_handles_empty_input(self) -> None:
        assert extract_phone("") == ""


class TestNumberParsing:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("11.5K", 11_500),
            ("2.3M", 2_300_000),
            ("1.2B", 1_200_000_000),
            ("1,204", 1204),
            ("847", 847),
            ("0", 0),
            ("3k", 3_000),
        ],
    )
    def test_parses_known_formats(self, raw: str, expected: int) -> None:
        assert parse_abbreviated_number(raw) == expected

    @pytest.mark.parametrize("raw", ["", "not a number", "abc", "K"])
    def test_unparseable_input_yields_zero(self, raw: str) -> None:
        """Scraped markup must never crash a run with a ValueError."""
        assert parse_abbreviated_number(raw) == 0


class TestHtmlHelpers:
    def test_strip_html_removes_scripts_and_tags(self) -> None:
        html = "<div>Hello <script>var x = 1;</script><b>world</b></div>"

        assert strip_html(html) == "Hello world"

    def test_extract_urls_normalizes_and_trims(self) -> None:
        text = "See https://example.org/page. Also linktr.ee/someone"

        assert extract_urls(text) == ["https://example.org/page", "https://linktr.ee/someone"]

    def test_truncate_appends_a_suffix(self) -> None:
        assert truncate("abcdefghij", 6) == "abc..."

    def test_truncate_leaves_short_text_alone(self) -> None:
        assert truncate("abc", 10) == "abc"
