from pathlib import Path
from unittest import TestCase, mock

from spiders_for_all import const
from spiders_for_all.core import downloader
from spiders_for_all.core import media as base_media


class TestLinerTask(TestCase):
    def test_liner_task(self):
        fn = mock.Mock()

        t = downloader.LinerTask(
            fn=fn,
            name="test",
            args=(1, 2, 3),
            kwargs={"a": 1, "b": 2},
        )

        t.start()

        self.assertEqual(
            t.args,
            (1, 2, 3),
        )

        self.assertEqual(
            t.kwargs,
            {"a": 1, "b": 2},
        )

        fn.assert_called_once_with(1, 2, 3, a=1, b=2)

    def test_liner_task_delay(self):
        obj = mock.Mock()

        obj.value = 1

        def fn_change_obj_value(obj):
            obj.value = 2

        fn_read_obj_value = mock.Mock()
        t1 = downloader.LinerTask(fn=fn_change_obj_value, name="test", args=(obj,))

        t2 = downloader.LinerTask(fn=fn_read_obj_value, delay_args=lambda: (obj.value,))

        t1.start()
        t2.start()

        fn_read_obj_value.assert_called_once_with(2)


class TestDownloadTask(TestCase):
    def setUp(self):
        self.media = base_media.Image(
            complete_url="http://test.com",
            name="test",
        )
        self.output_file = "test"
        self.download_task = downloader.DownloadTask(
            media=self.media,
            output_file=self.output_file,
        )

    def test_init(self):
        self.assertEqual(self.download_task.media, self.media)
        self.assertEqual(self.download_task.output_file, Path(self.output_file))
        self.assertEqual(self.download_task.chunk_size, const.CHUNK_SIZE)
        self.assertEqual(self.download_task.request_method, "GET")
        self.assertIsInstance(self.download_task.logger, downloader.logger.__class__)
        self.assertIsInstance(self.download_task.client, downloader.HttpClient)

    def test_str(self):
        expected = f"<Type: {self.media.media_type._name_}> {self.media.name or self.media.url}"
        self.assertEqual(str(self.download_task), expected)

    @mock.patch.object(downloader.HttpClient, "request")
    def test_request(self, mock_http_client_request):
        mock_response = mock.Mock(
            headers={},
            iter_content=mock.Mock(
                return_value=iter(
                    [
                        b"i" * self.download_task.chunk_size,
                        b"i" * self.download_task.chunk_size,
                    ]
                )
            ),
        )

        mock_context_manager = mock.Mock(
            __enter__=mock.Mock(return_value=mock_response),
            __exit__=mock.Mock(return_value=None),
        )

        mock_http_client_request.return_value = mock_context_manager

        r = self.download_task.request()

        self.assertEqual(next(r), 0)

        mock_http_client_request.assert_called_once_with(
            self.download_task.request_method,
            self.media.url,
            stream=True,
        )

        next(r)

        next(r)

        self.assertEqual(mock_response.iter_content.call_count, 1)

    @mock.patch.object(downloader.DownloadTask, "request")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    def test_start(self, mock_open, mock_request):
        mock_request.return_value = iter(
            [
                0,
                b"t",
                b"t",
            ]
        )

        list(self.download_task.start())

        mock_request.assert_called_once_with()

        mock_open.assert_called_once_with(
            self.download_task.output_file,
            "wb",
        )

        mock_open.return_value.__enter__.return_value.write.assert_called()


class TestDownloader(TestCase):
    ...


class TestMultipleDownloader(TestCase):
    ...
