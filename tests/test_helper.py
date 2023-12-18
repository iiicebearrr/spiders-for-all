from unittest import TestCase

from spiders_for_all.utils import helper


class TestHelper(TestCase):
    def test_helper(self):
        self.assertIn("User-Agent", helper.user_agent_headers())
        self.assertIsInstance(helper.user_agent_headers()["User-Agent"], str)
