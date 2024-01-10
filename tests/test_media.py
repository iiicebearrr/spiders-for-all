from unittest import TestCase

from spiders_for_all.core.media import HttpUrl, Media


class TestMedia(TestCase):
    def setUp(self):
        self.media = Media(complete_url="http://test.com", name="Test")

    def test_init(self):
        self.assertEqual(self.media.complete_url, "http://test.com")
        self.assertEqual(self.media.name, "Test")
        self.assertIsNone(self.media.base_url)
        self.assertIsNone(self.media.url_id)

    def test_url(self):
        self.assertEqual(self.media.url, "http://test.com/")

    def test_get_url(self):
        self.assertEqual(self.media.get_url(), HttpUrl("http://test.com"))

    def test_str(self):
        self.assertEqual(str(self.media), "<Test>")

    def test_str_with_description(self):
        self.media.description = "Test description"
        self.assertEqual(str(self.media), "<Test Test description>")

    def test_get_url_with_base_url_and_url_id(self):
        self.media.complete_url = None
        self.media.base_url = "http://test.com"
        self.media.url_id = "123"
        self.assertEqual(self.media.get_url(), HttpUrl("http://test.com/123"))

    def test_get_url_with_no_url(self):
        self.media.complete_url = None
        self.media.base_url = None
        self.media.url_id = None
        with self.assertRaises(ValueError):
            self.media.get_url()
