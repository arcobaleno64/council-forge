"""Unit tests for security_txt_gate.py — full-coverage, fail-closed RFC 9116 gate."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

import pytest

import security_txt_gate as gate

NOW = datetime(2026, 6, 8, tzinfo=timezone.utc)
FUTURE = "2026-09-08T00:00:00Z"  # ~92 days from NOW (< 365)
PAST = "2026-01-01T00:00:00Z"


def _txt(*, contact="Contact: mailto:security@example.com", expires=FUTURE, extra=()):
    lines = ["# a comment", ""]
    if contact is not None:
        lines.append(contact)
    if expires is not None:
        lines.append(f"Expires: {expires}")
    lines.extend(extra)
    return "\n".join(lines) + "\n"


def _eval(text, now=NOW, max_validity_days=365):
    return gate.evaluate(text, now=now, max_validity_days=max_validity_days)


# --------------------------------------------------------------------------- #
# validate_uri — every branch
# --------------------------------------------------------------------------- #
def test_uri_missing_scheme():
    assert "missing URI scheme" in gate.validate_uri("notauri")


def test_uri_http_rejected():
    assert "MUST use https" in gate.validate_uri("http://example.com")


def test_uri_https_no_host():
    assert "no host" in gate.validate_uri("https://")


def test_uri_https_valid():
    assert gate.validate_uri("https://example.com/security") is None


def test_uri_mailto_no_address():
    assert "no address" in gate.validate_uri("mailto:not-an-email")


def test_uri_mailto_valid():
    assert gate.validate_uri("mailto:security@example.com") is None


def test_uri_tel_empty():
    assert "no number" in gate.validate_uri("tel:")


def test_uri_tel_valid():
    assert gate.validate_uri("tel:+1-555-0100") is None


def test_uri_other_scheme_empty():
    assert "no target" in gate.validate_uri("dns:")


def test_uri_other_scheme_valid():
    assert gate.validate_uri("openpgp4fpr:ABCDEF0123456789") is None


# --------------------------------------------------------------------------- #
# parse_expires
# --------------------------------------------------------------------------- #
def test_expires_z_upper():
    dt, err = gate.parse_expires("2026-09-08T00:00:00Z")
    assert err is None and dt.tzinfo is not None


def test_expires_z_lower():
    dt, err = gate.parse_expires("2026-09-08T00:00:00z")
    assert err is None and dt.tzinfo is not None


def test_expires_offset():
    dt, err = gate.parse_expires("2026-09-08T00:00:00+08:00")
    assert err is None and dt.tzinfo is not None


def test_expires_unparseable():
    dt, err = gate.parse_expires("not-a-date")
    assert dt is None and "not a valid RFC 3339" in err


def test_expires_no_tz():
    dt, err = gate.parse_expires("2026-09-08T00:00:00")
    assert dt is None and "timezone" in err


# --------------------------------------------------------------------------- #
# parse_fields
# --------------------------------------------------------------------------- #
def test_parse_skips_blank_and_comment():
    fields, err = gate.parse_fields("# c\n\nContact: mailto:a@b.com\n")
    assert err is None and fields == [("contact", "mailto:a@b.com")]


def test_parse_no_colon():
    fields, err = gate.parse_fields("NoColonLineHere\n")
    assert fields is None and "malformed line" in err


def test_eval_propagates_parse_error():
    # evaluate() must surface a parse_fields error as a fail-closed result (not crash)
    code, msg = _eval("UnknownField: x\n")
    assert code == gate.EXIT_FAIL and "unknown field" in msg


def test_parse_empty_name():
    fields, err = gate.parse_fields(": value\n")
    assert fields is None and "empty name or value" in err


def test_parse_empty_value():
    fields, err = gate.parse_fields("Contact:\n")
    assert fields is None and "empty name or value" in err


def test_parse_unknown_field():
    fields, err = gate.parse_fields("Whatever: x\n")
    assert fields is None and "unknown field" in err


# --------------------------------------------------------------------------- #
# evaluate — cardinality, contact, fields, expires
# --------------------------------------------------------------------------- #
def test_eval_valid():
    code, msg = _eval(_txt())
    assert code == gate.EXIT_OK and "valid security.txt" in msg


def test_eval_expires_duplicate_failclosed():
    code, msg = _eval(_txt(extra=[f"Expires: {FUTURE}"]))
    assert code == gate.EXIT_FAIL and "MUST NOT appear more than once" in msg


def test_eval_preferred_languages_duplicate_failclosed():
    text = _txt(extra=["Preferred-Languages: en", "Preferred-Languages: fr"])
    assert _eval(text)[0] == gate.EXIT_FAIL


def test_eval_bug_bounty_duplicate_failclosed():
    text = _txt(extra=["Bug-Bounty: True", "Bug-Bounty: False"])
    assert _eval(text)[0] == gate.EXIT_FAIL


def test_eval_contact_missing_failclosed():
    code, msg = _eval(_txt(contact=None))
    assert code == gate.EXIT_FAIL and "Contact field is required" in msg


def test_eval_uri_field_error_failclosed():
    code, msg = _eval(_txt(extra=["Canonical: http://example.com/.well-known/security.txt"]))
    assert code == gate.EXIT_FAIL and "canonical" in msg


def test_eval_bug_bounty_valid():
    for value in ("True", "False", "true"):
        assert _eval(_txt(extra=[f"Bug-Bounty: {value}"]))[0] == gate.EXIT_OK


def test_eval_bug_bounty_invalid_failclosed():
    code, msg = _eval(_txt(extra=["Bug-Bounty: yes"]))
    assert code == gate.EXIT_FAIL and "Bug-Bounty must be True or False" in msg


def test_eval_preferred_languages_not_uri_validated():
    # Preferred-Languages is not a URI; a plain language list is fine.
    assert _eval(_txt(extra=["Preferred-Languages: en, fr"]))[0] == gate.EXIT_OK


def test_eval_expires_missing_failclosed():
    code, msg = _eval(_txt(expires=None))
    assert code == gate.EXIT_FAIL and "Expires field is required exactly once" in msg


def test_eval_expires_unparseable_failclosed():
    assert _eval(_txt(expires="bogus"))[0] == gate.EXIT_FAIL


def test_eval_expires_past_failclosed():
    code, msg = _eval(_txt(expires=PAST))
    assert code == gate.EXIT_FAIL and "in the past" in msg


def test_eval_expires_too_far_failclosed():
    code, msg = _eval(_txt(expires=FUTURE), max_validity_days=30)  # 92d out > 30
    assert code == gate.EXIT_FAIL and "days out" in msg


def test_eval_full_valid_with_all_fields():
    text = _txt(extra=[
        "Contact: https://example.com/report",
        "Encryption: https://example.com/pgp-key.txt",
        "Canonical: https://example.com/.well-known/security.txt",
        "Policy: https://example.com/security-policy",
        "Acknowledgments: https://example.com/hall-of-fame",
        "Hiring: https://example.com/jobs",
        "CSAF: https://example.com/.well-known/csaf/provider-metadata.json",
        "Preferred-Languages: en",
        "Bug-Bounty: True",
    ])
    assert _eval(text)[0] == gate.EXIT_OK


# --------------------------------------------------------------------------- #
# read_source / run() — CLI, exit codes, standing advisory
# --------------------------------------------------------------------------- #
def test_read_source_file(tmp_path: Path):
    p = tmp_path / "security.txt"
    p.write_text("Contact: mailto:a@b.com\n", encoding="utf-8")
    assert "Contact" in gate.read_source(str(p))


def test_read_source_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("Contact: x\n"))
    assert gate.read_source("-") == "Contact: x\n"


def _write(p: Path, text: str) -> Path:
    p.write_text(text, encoding="utf-8")
    return p


def test_run_valid_exit0_advisory_on_stdout(tmp_path: Path, capsys):
    # NOTE: run() uses datetime.now(); FUTURE is far enough to stay valid for this test's lifetime.
    far_future = "2099-01-01T00:00:00Z"
    p = _write(tmp_path / "security.txt", _txt(expires=far_future))
    assert gate.run(["--file", str(p), "--max-validity-days", "100000"]) == gate.EXIT_OK
    out = capsys.readouterr().out
    assert "[OK]" in out and "ADVISORY" in out and "HUMAN-REVIEW" in out


def test_run_fail_exit1_advisory_on_stderr(tmp_path: Path, capsys):
    p = _write(tmp_path / "security.txt", _txt(expires=PAST))
    assert gate.run(["--file", str(p)]) == gate.EXIT_FAIL
    err = capsys.readouterr().err
    assert "[FAIL]" in err and "ADVISORY" in err


def test_run_empty_failclosed(tmp_path: Path, capsys):
    p = _write(tmp_path / "security.txt", "   \n")
    assert gate.run(["--file", str(p)]) == gate.EXIT_FAIL
    assert "empty security.txt" in capsys.readouterr().err


def test_run_non_utf8_failclosed(tmp_path: Path, capsys):
    p = tmp_path / "security.txt"
    p.write_bytes(b"\xff\xfeContact: mailto:a@b.com\n")
    assert gate.run(["--file", str(p)]) == gate.EXIT_FAIL
    assert "not valid UTF-8" in capsys.readouterr().err


def test_run_missing_file_usage(tmp_path: Path, capsys):
    assert gate.run(["--file", str(tmp_path / "ghost.txt")]) == gate.EXIT_USAGE
    assert "cannot read" in capsys.readouterr().err


def test_run_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(_txt(expires="2099-01-01T00:00:00Z")))
    assert gate.run(["--file", "-", "--max-validity-days", "100000"]) == gate.EXIT_OK
