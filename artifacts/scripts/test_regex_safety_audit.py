"""Tests for regex_safety_audit.py — the systemic ReDoS-shape gate."""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import regex_safety_audit as rsa  # noqa: E402


class TestDetectShapes:
    def test_flags_double_dot_unbounded(self):
        # the REDOS-01 motif
        assert "double-dot-unbounded" in rsa.detect_shapes(r"^\[(\d+)\]\s+.+\..+(?:x)\)$")

    def test_flags_nested_quantifier(self):
        assert "nested-quantifier" in rsa.detect_shapes(r"(a+)+$")
        assert "nested-quantifier" in rsa.detect_shapes(r"(?:.*)+")

    def test_flags_dual_tempered_fill(self):
        # the REDOS-02 motif: lazy negated fill then greedy negated fill
        assert "dual-tempered-fill" in rsa.detect_shapes(r"[（(][^)）\n]*?X\.md[^)）\n]*[)）]")

    def test_does_not_flag_linear_fixed_redos01(self):
        # the linear replacement shipped for REDOS-01 must NOT be flagged
        p = (r"^\[(\d+)\]\s+(?P<title>.*)(?:https?://\S+|[A-Za-z0-9_./\\-]{1,256}"
             r"\.[A-Za-z0-9]{1,10})\s+\(\d{4}-\d{2}-\d{2}\s+retrieved\)$")
        assert rsa.detect_shapes(p) == []

    def test_does_not_flag_simple_anchored(self):
        assert rsa.detect_shapes(r"^TASK-\d{3,}$") == []
        assert rsa.detect_shapes(r"\bAKIA[0-9A-Z]{16}\b") == []


class TestAuditRepo:
    def test_repo_is_clean(self):
        # every ReDoS-shaped pattern in the repo must be annotated/justified
        root = SCRIPTS_DIR.parent.parent
        assert rsa.main(["--root", str(root)]) == rsa.EXIT_OK

    def test_redos_ok_marker_exempts(self, tmp_path):
        scripts = tmp_path / "artifacts" / "scripts"
        scripts.mkdir(parents=True)
        bad = scripts / "danger.py"
        bad.write_text("import re\nP = re.compile(r'.+\\..+x')\n", encoding="utf-8")
        assert rsa.main(["--root", str(tmp_path)]) == rsa.EXIT_FAIL

        bad.write_text("import re\nP = re.compile(r'.+\\..+x')  # redos-ok: test\n", encoding="utf-8")
        assert rsa.main(["--root", str(tmp_path)]) == rsa.EXIT_OK
