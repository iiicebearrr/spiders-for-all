from unittest import TestCase
from unittest.mock import patch

from requests.models import Response

from spiders_for_all.core.client import Headers, HttpClient, RequestsCookieJar


class TestHttpClient(TestCase):
    def setUp(self):
        self.client = HttpClient()

    def test_close(self):
        with patch.object(self.client.session, "close") as mock_close:
            self.client.close()
            mock_close.assert_called_once()

    def test_headers(self):
        self.assertIsInstance(self.client.headers, Headers)

    def test_cookies(self):
        self.assertIsInstance(self.client.cookies, RequestsCookieJar)

    def test_new(self):
        new_client = self.client.new()
        self.assertIsNot(self.client, new_client)
        self.assertEqual(self.client._headers, new_client._headers)
        self.assertEqual(self.client._cookies, new_client._cookies)

    @patch.object(HttpClient, "request")
    def test_get(self, mock_request):
        url = "http://test.com"
        self.client.get(url)
        mock_request.assert_called_once_with("get", url)

    @patch.object(HttpClient, "request")
    def test_options(self, mock_request):
        url = "http://test.com"
        self.client.options(url)
        mock_request.assert_called_once_with("options", url)

    @patch.object(HttpClient, "request")
    def test_head(self, mock_request):
        url = "http://test.com"
        self.client.head(url)
        mock_request.assert_called_once_with("head", url, allow_redirects=False)

    @patch.object(HttpClient, "request")
    def test_post(self, mock_request):
        url = "http://test.com"
        self.client.post(url)
        mock_request.assert_called_once_with("post", url)

    @patch.object(HttpClient, "request")
    def test_put(self, mock_request):
        url = "http://test.com"
        self.client.put(url)
        mock_request.assert_called_once_with("put", url)

    @patch.object(HttpClient, "request")
    def test_patch(self, mock_request):
        url = "http://test.com"
        self.client.patch(url)
        mock_request.assert_called_once_with("patch", url)

    @patch.object(HttpClient, "request")
    def test_delete(self, mock_request):
        url = "http://test.com"
        self.client.delete(url)
        mock_request.assert_called_once_with("delete", url)

    @patch.object(HttpClient, "request")
    def test_request(self, mock_request):
        url = "http://test.com"
        method = "get"
        mock_request.return_value = Response()
        response = self.client.request(method, url)
        self.assertIsInstance(response, Response)
