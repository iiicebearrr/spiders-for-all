from unittest import TestCase, mock
from click.testing import CliRunner

import spiders_for_all.bilibili.__main__ as bilibili_main
from spiders_for_all.bilibili.__main__ import cli
from pathlib import Path


class TestCli(TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_run_spider(self):
        mock_spider_cls = mock.Mock()
        mock_spider_instance = mock.Mock(run=mock.Mock())
        mock_spider_cls.return_value = mock_spider_instance

        with mock.patch.dict(bilibili_main.SPIDERS, {"popular": mock_spider_cls}):
            result = self.runner.invoke(
                cli,  # type: ignore
                ["run-spider", "-n", "popular"],
            )

            self.assertEqual(result.exit_code, 0)
            mock_spider_instance.run.assert_called_once()

    def test_list_spiders(self):
        result = self.runner.invoke(cli, ["list-spiders"])  # type: ignore
        self.assertEqual(result.exit_code, 0)

    @mock.patch("spiders_for_all.bilibili.analysis.Analysis")
    def test_data_analysis(self, mock_analysis: mock.Mock):
        mock_spider_cls = mock.Mock(string=mock.Mock())
        mock_spider_cls.database_model = mock.Mock()
        mock_analysis_instance = mock.Mock(show=mock.Mock())
        mock_analysis.return_value = mock_analysis_instance

        with mock.patch.dict(bilibili_main.SPIDERS, {"popular": mock_spider_cls}):
            result = self.runner.invoke(
                cli,  # type: ignore
                ["data-analysis", "-n", "popular", "-t", "10"],
            )
            self.assertEqual(result.exit_code, 0)
            mock_spider_cls.string.assert_called_once()

            mock_analysis.assert_called_once_with(mock_spider_cls.database_model, 10)
            mock_analysis_instance.show.assert_called_once()

    @mock.patch("spiders_for_all.bilibili.download.Downloader")
    def test_download(self, mock_downloader: mock.Mock):
        mock_downloader_inst = mock.Mock(download=mock.Mock())

        mock_downloader.return_value = mock_downloader_inst

        result = self.runner.invoke(
            cli,  # type: ignore
            ["download-video", "-b", "BV1Kb411W7KC", "-s", "/tmp", "-f", "test.mp4"],
        )
        self.assertEqual(result.exit_code, 0)

        mock_downloader.assert_called_once_with(
            "BV1Kb411W7KC", Path("/tmp"), "test.mp4", True, None, 0, None, ()
        )

        mock_downloader_inst.download.assert_called_once()
