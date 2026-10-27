#!/usr/bin/env python3
"""Tests for the session-marker handling in grade.py.

Usage: python3 evals/test_grade.py

Each test sets grade.MARKERS itself, so the result does not depend on the
PRREVIEW_MARKERS value in your shell.
"""
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade

REPORT = "APPROVE. 0 must, 0 should, 0 question, 0 nit. No findings. Tests 3 pass, 0 fail.\n.adp/T-1/pr-review-local-20261026-r1.md"


class TerminalLines(unittest.TestCase):
    def lines(self, text, patterns):
        grade.MARKERS = [re.compile(p) for p in patterns]
        with tempfile.TemporaryDirectory() as run:
            os.makedirs(os.path.join(run, "outputs"))
            with open(os.path.join(run, "outputs", "terminal.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            _, lines, marker = grade.terminal_lines(run)
        return lines, marker

    def test_no_patterns_keeps_marker(self):
        self.assertEqual(self.lines(REPORT + "\n⟦lc:3⟧", []), (REPORT.splitlines() + ["⟦lc:3⟧"], False))

    def test_configured_marker_is_dropped(self):
        for marker in ("⟦lc:3⟧", "  ⟦lc:3⟧\t"):
            self.assertEqual(self.lines(REPORT + "\n" + marker, ["⟦lc:[^⟧]*⟧"]), (REPORT.splitlines(), True))

    def test_marker_with_text_is_kept(self):
        self.assertEqual(self.lines(REPORT + "\n⟦lc:3⟧ Done.", ["⟦lc:[^⟧]*⟧"]), (REPORT.splitlines() + ["⟦lc:3⟧ Done."], False))

    def test_only_one_line_is_dropped(self):
        lines, marker = self.lines(REPORT + "\nDone.\n⟦lc:3⟧", ["⟦lc:[^⟧]*⟧"])
        self.assertEqual((len(lines), lines[-1], marker), (3, "Done.", True))

    def test_two_line_reply_is_unchanged(self):
        for patterns in ([], ["⟦lc:[^⟧]*⟧"], ["⟦sc:[^⟧]*⟧", "⟦lc:[^⟧]*⟧"]):
            self.assertEqual(self.lines(REPORT, patterns), (REPORT.splitlines(), False))


if __name__ == "__main__":
    unittest.main()
