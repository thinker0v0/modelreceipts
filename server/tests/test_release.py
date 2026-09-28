"""Release hygiene: one version string everywhere, and a dashboard with no external
resources (no CDN, fonts or trackers). Run from repo root:

    python3 -m unittest discover -s server/tests
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))

from modelreceipts_server import REPO_ROOT, __version__  # noqa: E402  (also puts collector/ on sys.path)

import modelreceipts  # noqa: E402


def _pep440_to_semver(v: str) -> str:
    return re.sub(r"(\d)(a|b|rc)(\d+)$", r"\1-\2\3", v)  # 1.0.0rc2 -> 1.0.0-rc2


class VersionTest(unittest.TestCase):
    def test_versions_agree(self):
        self.assertEqual(modelreceipts.__version__, __version__)
        pyproject = (REPO_ROOT / "collector" / "pyproject.toml").read_text(encoding="utf-8")
        self.assertTrue(f'version = "{__version__}"' in pyproject, "collector/pyproject.toml")
        semver = _pep440_to_semver(__version__)
        dashboard = (REPO_ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertTrue(f">v{semver}<" in dashboard, "dashboard version pill")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(f"Status: v{semver}" in readme, "README English summary")
        self.assertTrue(semver.replace("-", "--") in readme, "README status badge")  # shields.io escapes '-'
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        first = re.search(r"^## \[(\d[^\]]*)\]", changelog, re.M)
        self.assertEqual(first.group(1), semver)


class DashboardSelfContainedTest(unittest.TestCase):
    def test_no_external_resources(self):
        html = (REPO_ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r"<script[^>]+src=")
        self.assertNotRegex(html, r"<link[^>]+href=")
        self.assertNotRegex(html, r"@import|url\(\s*['\"]?https?:")
        self.assertNotRegex(html, r"fetch\(\s*['\"`]https?:")
        for tracker in ("googletagmanager", "google-analytics", "plausible", "segment.io", "sentry"):
            self.assertNotIn(tracker, html)

    def test_accessibility_basics_are_present(self):
        html = (REPO_ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        for needle in ('lang="ko"', "prefers-reduced-motion", "prefers-color-scheme: dark", ":focus-visible",
                       'class="skip"', "aria-live", 'data-theme="dark"'):
            self.assertIn(needle, html)


if __name__ == "__main__":
    unittest.main()
