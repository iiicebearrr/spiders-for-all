from unittest import TestCase

from spiders_for_all.core import media


class TestMedia(TestCase):
    def test_init_with_only_base_url(self):
        m = media.Media(base_url="http://test.com")
        self.assertEqual(m.base_url, "http://test.com")
        self.assertEqual(m.backup_url, [])
        self.assertEqual(m.name, "NAME NOT SET")

    def test_init_with_base_url_and_backup_url(self):
        m = media.Media(
            base_url="http://test.com",
            backup_url=["http://backup1.com", "http://backup2.com"],
        )
        self.assertEqual(m.base_url, "http://test.com")
        self.assertEqual(m.backup_url, ["http://backup1.com", "http://backup2.com"])
        self.assertEqual(m.name, "NAME NOT SET")

    def test_init_with_base_url_and_name(self):
        m = media.Media(base_url="http://test.com", name="Test Name")
        self.assertEqual(m.base_url, "http://test.com")
        self.assertEqual(m.backup_url, [])
        self.assertEqual(m.name, "Test Name")

    def test_init_with_all_parameters(self):
        m = media.Media(
            base_url="http://test.com",
            backup_url=["http://backup1.com"],
            name="Test Name",
        )
        self.assertEqual(m.base_url, "http://test.com")
        self.assertEqual(m.backup_url, ["http://backup1.com"])
        self.assertEqual(m.name, "Test Name")
