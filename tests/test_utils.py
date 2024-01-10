from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from spiders_for_all.utils.helper import Path as _Path
from spiders_for_all.utils.helper import (
    correct_filename,
    javascript_to_dict,
    not_none_else,
    read_ids_to_list,
    rm_tree,
    user_agent_headers,
)


class TestHelper(TestCase):
    @patch("spiders_for_all.utils.helper.ua")
    def test_user_agent_headers(self, mock_ua):
        mock_ua.random = "Test User Agent"
        expected = {"user-agent": "Test User Agent"}
        self.assertEqual(user_agent_headers(), expected)

    def test_correct_filename(self):
        filename = 'test\\/:*?"<>|file'
        expected = "test_________file"
        self.assertEqual(correct_filename(filename), expected)

    @patch.object(_Path, "exists")
    @patch.object(_Path, "glob")
    @patch.object(_Path, "unlink")
    @patch.object(_Path, "rmdir")
    @patch.object(_Path, "is_file")
    def test_rm_tree(
        self, mock_is_file, mock_rmdir, mock_unlink, mock_glob, mock_exists
    ):
        mock_exists.return_value = True
        mock_is_file.return_value = True
        mock_glob.return_value = [Path("test"), Path("test")]
        mock_rmdir.return_value = None
        mock_unlink.return_value = None

        rm_tree(Path("test"))

        mock_rmdir.assert_called_once()
        mock_exists.assert_called_once()
        mock_is_file.assert_called()
        mock_glob.assert_called_once()
        mock_unlink.assert_called()

    def test_not_none_else(self):
        self.assertEqual(not_none_else(None, "default"), "default")
        self.assertEqual(not_none_else("value", "default"), "value")

    def test_javascript_to_dict(self):
        raw = '{"key": undefined}'
        expected = {"key": None}
        self.assertEqual(javascript_to_dict(raw), expected)

    def test_read_ids_to_list_str(self):
        ids = "1,2,3,4,5"
        read = read_ids_to_list(ids)

        self.assertIn("1", read)
        self.assertIn("2", read)
        self.assertIn("3", read)
        self.assertIn("4", read)
        self.assertIn("5", read)

    def test_read_ids_to_list_path(self):
        mock_path = Mock(spec=Path)
        mock_path.read_text.return_value = "1,2,3,4,5"
        read = read_ids_to_list(mock_path)

        self.assertIn("1", read)
        self.assertIn("2", read)
        self.assertIn("3", read)
        self.assertIn("4", read)
        self.assertIn("5", read)

    def test_read_ids_to_list_binary_io(self):
        ids = BytesIO(b"1,2,3,4,5")
        read = read_ids_to_list(ids)

        self.assertIn("1", read)
        self.assertIn("2", read)
        self.assertIn("3", read)
        self.assertIn("4", read)
        self.assertIn("5", read)

    def test_read_ids_to_list_list(self):
        ids = ["1,2,3", "4,5"]
        read = read_ids_to_list(ids)

        self.assertIn("1", read)
        self.assertIn("2", read)
        self.assertIn("3", read)
        self.assertIn("4", read)
        self.assertIn("5", read)

    def test_read_ids_to_list_invalid_type(self):
        ids = 123
        with self.assertRaises(TypeError):
            read_ids_to_list(ids)  # type: ignore
