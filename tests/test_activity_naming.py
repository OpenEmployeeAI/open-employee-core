"""Tests for the mcp__<server>__<tool> Activity naming invariant."""

import unittest

from core.workflows import ACTIVITY_NAME_RE, mcp_activity_name


class ActivityNamingTest(unittest.TestCase):
    def test_canonical_name(self):
        self.assertEqual(
            mcp_activity_name("github", "create_issue"),
            "mcp__github__create_issue",
        )

    def test_name_matches_regex(self):
        name = mcp_activity_name("linear", "list_issues")
        self.assertRegex(name, ACTIVITY_NAME_RE)

    def test_rejects_uppercase(self):
        with self.assertRaises(ValueError):
            mcp_activity_name("GitHub", "create_issue")

    def test_rejects_empty_segments(self):
        with self.assertRaises(ValueError):
            mcp_activity_name("", "create_issue")
        with self.assertRaises(ValueError):
            mcp_activity_name("github", "")

    def test_rejects_separator_injection(self):
        # A server containing the separator could collide with a different
        # (server, tool) split; the regex must reject it.
        with self.assertRaises(ValueError):
            mcp_activity_name("github__evil", "tool")

    def test_rejects_invalid_chars(self):
        with self.assertRaises(ValueError):
            mcp_activity_name("git hub", "create_issue")
        with self.assertRaises(ValueError):
            mcp_activity_name("github", "create.issue")


if __name__ == "__main__":
    unittest.main()
