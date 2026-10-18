# tests/test_theme.py
"""Unit tests for the multi-family theme system in ``ui.theme``."""
import os
import re
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from ui import theme  # noqa: E402


class ThemeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_every_palette_defines_the_same_tokens(self):
        reference = set(theme.tokens("arisu", "dark"))
        self.assertTrue(reference)
        for family in theme.family_names():
            for mode in theme.MODES:
                self.assertEqual(
                    set(theme.tokens(family, mode)), reference,
                    f"{family}/{mode} token set differs",
                )

    def test_every_family_has_both_modes(self):
        for family in theme.family_names():
            for mode in theme.MODES:
                self.assertIn(mode, theme.THEMES[family])

    def test_stylesheet_renders_without_placeholders(self):
        for family in theme.family_names():
            for mode in theme.MODES:
                css = theme.stylesheet(family, mode)
                self.assertNotIn("@{", css)
                self.assertIsNone(re.search(r"\$[A-Za-z_]", css))

    def test_families_produce_distinct_stylesheets(self):
        sheets = {
            theme.stylesheet(family, mode)
            for family in theme.family_names()
            for mode in theme.MODES
        }
        self.assertEqual(len(sheets), len(theme.family_names()) * len(theme.MODES))

    def test_apply_theme_drives_the_rendered_stylesheet(self):
        """Regression: the QSS must follow the active family, not the default."""
        for family in theme.family_names():
            for mode in theme.MODES:
                theme.apply_theme(self.app, family, mode)
                css = self.app.styleSheet()
                self.assertEqual(theme.current_family(), family)
                self.assertEqual(theme.current_mode(), mode)
                self.assertIn(theme.tokens()["accent"], css)
                self.assertEqual(theme.stylesheet(), css)

    def test_legacy_mode_only_call_reads_as_a_mode(self):
        theme.apply_theme(self.app, "saas", "dark")
        theme.apply_theme(self.app, "light")
        self.assertEqual(theme.current_family(), "saas")  # family untouched
        self.assertEqual(theme.current_mode(), "light")

    def test_family_only_call_keeps_the_current_mode(self):
        theme.apply_theme(self.app, "saas", "light")
        theme.apply_theme(self.app, "arch")
        self.assertEqual(theme.current_family(), "arch")
        self.assertEqual(theme.current_mode(), "light")

    def test_flip_mode(self):
        self.assertEqual(theme.flip_mode("dark"), "light")
        self.assertEqual(theme.flip_mode("light"), "dark")

    def test_color_follows_the_active_theme(self):
        theme.apply_theme(self.app, "saas", "dark")
        self.assertEqual(theme.color("accent"), theme.tokens("saas", "dark")["accent"])

    def test_unknown_family_and_mode_fall_back(self):
        theme.apply_theme(self.app, "nope", "nope")
        self.assertEqual(theme.current_family(), theme.DEFAULT_FAMILY)
        self.assertEqual(theme.current_mode(), theme.DEFAULT_MODE)


if __name__ == "__main__":
    unittest.main()
