import pathlib
from unittest import TestCase, mock

from bilibili import download, models
from conf import settings


class TestDownloader(TestCase):
    def setUp(self):
        self.bvid = "test_download_bv"
        self.save_path = settings.BASE_DIR / "tests/bilibili_tests"
        self.downloader, self.mock_mkdir = self.get_test_downloader()

        self.video = models.PlayVideo(
            base_url="test_base_url",
            codecs="test_codecs",
            id=0,  # type: ignore
            backup_url=["test_backup_url_1", "test_backup_url_2"],
        )  # type: ignore

        self.videos = [
            models.PlayVideo(
                base_url=f"base url {i}",
                backup_url=[f"backup url {i}"],
                id=i,  # type: ignore
                quality=i,
                codecs=f"codecs {i}",
            )
            for i in range(10, 1, -1)
        ]

        self.audios = [
            models.PlayAudio(
                base_url=f"base url {i}",
                backup_url=[f"backup url {i}"],
                id=i,  # type: ignore
            )
            for i in range(3)
        ]

        self.html_test = settings.BASE_DIR / "tests/bilibili_tests/play_info.txt"
        self.play_info = models.PlayInfoData(
            accept_quality=[self.video.quality],
            accept_description=["test"],
            dash={"video": self.videos, "audio": self.audios},  # type: ignore
        )

    def get_test_downloader(self, **kwargs):
        with mock.patch.object(download.Path, attribute="mkdir") as m:
            return download.Downloader(self.bvid, self.save_path, **kwargs), m

    def test_init(self):
        downloader = self.downloader
        self.assertEqual(downloader.bvid, self.bvid)
        self.assertEqual(downloader.save_path, self.save_path)
        self.assertEqual(downloader.filename, self.save_path / (self.bvid + ".mp4"))
        self.assertEqual(downloader.remove_temp_dir, True)
        self.assertEqual(downloader.sess_data, None)
        self.assertEqual(downloader.quality, download.HIGHEST_QUALITY)
        self.assertEqual(downloader.codecs, None)
        self.assertEqual(downloader.ffmpeg_params, None)
        self.assertEqual(downloader.process_func, None)
        self.assertEqual(downloader.api, download.Downloader.api.format(bvid=self.bvid))
        self.assertEqual(self.mock_mkdir.call_count, 2)

    def test_init_filename_with_suffix(self):
        # test filename with suffix
        filename_with_suffix = "test.mkv"
        downloader, mock_mkdir = self.get_test_downloader(filename=filename_with_suffix)

        self.assertEqual(downloader.filename, self.save_path / filename_with_suffix)
        self.assertEqual(mock_mkdir.call_count, 2)

    @mock.patch.object(download.requests, "get")
    @mock.patch.object(download.logger, "debug")
    def test_get_play_info(self, mock_debug: mock.Mock, mock_get: mock.Mock):
        html_mock = self.html_test.read_text(encoding="utf-8")
        mock_response = mock.Mock(
            raise_for_status=mock.Mock(),
        )
        mock_response_text = mock.PropertyMock(return_value=html_mock)

        type(mock_response).text = mock_response_text

        mock_get.return_value = mock_response

        play_info = self.downloader.get_play_info()

        mock_debug.assert_called_once_with(f"Requesting {self.downloader.api}")

        self.assertEqual(mock_get.call_args.args[0], self.downloader.api)

        mock_response.raise_for_status.assert_called_once()

        mock_response_text.assert_called_once()

        self.assertIsInstance(play_info, models.PlayInfoData)

    @mock.patch.object(download.requests, "get")
    @mock.patch.object(download.logger, "debug")
    def test_get_play_info_with_sess_data(
        self, mock_debug: mock.Mock, mock_get: mock.Mock
    ):
        downloader, _ = self.get_test_downloader(
            sess_data="test_sess_data",
        )

        html_mock = self.html_test.read_text(encoding="utf-8")
        mock_response = mock.Mock(
            raise_for_status=mock.Mock(),
        )
        mock_response_text = mock.PropertyMock(return_value=html_mock)

        type(mock_response).text = mock_response_text

        mock_get.return_value = mock_response

        play_info = downloader.get_play_info()

        mock_debug.assert_called_once_with(
            f"Requesting {self.downloader.api} with cookies {{'SESSDATA': 'test_sess_data'}}"
        )

        self.assertEqual(mock_get.call_args.args[0], self.downloader.api)

        self.assertEqual(
            mock_get.call_args.kwargs["cookies"], {"SESSDATA": "test_sess_data"}
        )

        mock_response.raise_for_status.assert_called_once()

        mock_response_text.assert_called_once()

        self.assertIsInstance(play_info, models.PlayInfoData)

    @mock.patch.object(download.requests, "get")
    @mock.patch.object(download.logger, "debug")
    @mock.patch.object(download.Path, "open")
    @mock.patch.object(download.Path, "unlink")
    def test__download(
        self,
        mock_unlink: mock.Mock,
        mock_open: mock.Mock,
        mock_debug: mock.Mock,
        mock_get: mock.Mock,
    ):
        mock_response = mock.Mock(
            iter_content=mock.Mock(
                return_value=[
                    b"test_chunk_1",
                    b"test_chunk_2",
                    b"test_chunk_3",
                ]
            ),
            raise_for_status=mock.Mock(),
        )

        mock_stream_response = mock.Mock(
            __enter__=mock.Mock(return_value=mock_response),
            __exit__=mock.Mock(return_value=False),
        )

        mock_get.return_value = mock_stream_response

        mock_open.return_value = mock.Mock(
            __enter__=mock.Mock(return_value=mock.Mock()),
            __exit__=mock.Mock(return_value=False),
            write=mock.Mock(),
        )

        self.downloader._download(self.video, self.downloader.save_path)

        mock_unlink.assert_called_once_with(missing_ok=True)

        self.assertEqual(mock_debug.call_count, 2)

        self.assertEqual(mock_get.call_args.args[0], self.video.base_url)

        self.assertTrue(mock_get.call_args.kwargs["stream"])

        mock_response.raise_for_status.assert_called_once()

        mock_response.iter_content.assert_called_once_with(chunk_size=8192)

        mock_open.assert_called_once_with("wb")

    @mock.patch.object(download.logger, "info")
    def test_download_video(self, mock_info: mock.Mock):
        self.downloader._download = mock.Mock()

        self.downloader.get_play_info = mock.Mock(
            return_value=self.play_info,
        )

        self.downloader.download_video(self.video)
        mock_info.assert_called_once_with(
            f"[{self.video.quality}] Downloading video..."
        )

        self.downloader._download.assert_called_once_with(
            self.video,
            self.downloader.temp_dir
            / f"video-{self.downloader.play_info.quality_map[self.video.quality]}-{self.video.codecs}.mp4",
        )

    @mock.patch.object(download.Path, "read_bytes")
    @mock.patch.object(download.Path, "open")
    @mock.patch.object(download.logger, "debug")
    def test_download_audios(
        self, mock_debug: mock.Mock, mock_open: mock.Mock, mock_read_bytes: mock.Mock
    ):
        self.downloader._download = mock.Mock(
            return_value=pathlib.Path("test_audio_path")
        )

        mock_file_like_object = mock.Mock(write=mock.Mock())

        mock_open.return_value = mock.Mock(
            __enter__=mock_file_like_object,
            __exit__=mock.Mock(return_value=False),
        )

        self.downloader.download_audios(self.audios)

        mock_debug.assert_called_with("Downloading audio...")

        self.assertEqual(mock_debug.call_count, len(self.audios))

        mock_open.assert_called_with("wb")

        # FIXME: mock_file_like_object.write has been called for wrong times
        # self.assertEqual(mock_file_like_object.write.call_count, len(self.test_audios))

        self.assertEqual(mock_read_bytes.call_count, len(self.audios))

    @mock.patch.object(download.Path, "rmdir")
    def test_clean(self, mock_rmdir: mock.Mock):
        self.downloader.remove_temp_dir = True
        self.downloader.clean()

        mock_rmdir.assert_called_once()

    @mock.patch.object(download.logger, "debug")
    @mock.patch.object(download.subprocess, "check_output")
    @mock.patch.object(download.subprocess, "run")
    def test_process(
        self, mock_run: mock.Mock, mock_check_output: mock.Mock, mock_debug: mock.Mock
    ):
        mock_check_output.return_value = b"ffmpeg"

        video_path = pathlib.Path("test_video_path")
        audio_path = pathlib.Path("test_audio_path")

        self.downloader.process(video_path=video_path, audio_path=audio_path)

        mock_debug.assert_called_once_with(
            f"Process {video_path} with FFMPEG: ffmpeg -i test_video_path -i test_audio_path -c:v copy -c:a aac {self.downloader.filename}"
        )

        mock_check_output.assert_called_once_with(["which", "ffmpeg"])

        mock_run.assert_called_once_with(
            [
                "ffmpeg",
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                str(self.downloader.filename),
            ],
            check=True,
        )

    def test_filter_quality_highest(self):
        filter_videos = self.downloader.filter_quality(self.videos)

        self.assertEqual(
            filter_videos[0].quality,
            10,
        )

    def test_filter_quality_specified(self):
        self.downloader.quality = 5

        filter_videos = self.downloader.filter_quality(self.videos)

        self.assertEqual(
            filter_videos[0].quality,
            5,
        )

    def test_choose_codecs_video(self):
        self.downloader.codecs = "codecs 8"
        video = self.downloader.choose_codecs(self.videos)
        self.assertEqual(
            video.codecs,
            "codecs 8",
        )

    def test_use_default_codecs_video(self):
        video = self.downloader.choose_codecs(self.videos)

        self.assertEqual(
            video.codecs,
            "codecs 10",
        )

    def test_property_videos(self):
        self.downloader.get_play_info = mock.Mock(return_value=self.play_info)

        reversed_videos = self.videos[::-1]

        self.assertListEqual(self.downloader.videos[::-1], reversed_videos)

    @mock.patch.object(download.Downloader, "choose_codecs")
    @mock.patch.object(download.Downloader, "filter_quality")
    def test_property_video_to_download(
        self, mock_filter: mock.Mock, mock_choose_codecs: mock.Mock
    ):
        mock_choose_codecs.return_value = self.video
        mock_filter.return_value = [self.video]

        self.downloader.get_play_info = mock.Mock(return_value=self.play_info)

        self.assertEqual(self.downloader.video_to_download, self.video)

        mock_filter.assert_called_once_with(self.videos)
        mock_choose_codecs.assert_called_once_with([self.video])

    @mock.patch.object(download.Downloader, "process")
    @mock.patch.object(download.Downloader, "download_audios")
    @mock.patch.object(download.Downloader, "download_video")
    def test_download(
        self,
        mock_dl_video: mock.Mock,
        mock_dl_audios: mock.Mock,
        mock_process: mock.Mock,
    ):
        self.downloader.get_play_info = mock.Mock(return_value=self.play_info)

        self.downloader.download()

        mock_dl_video.assert_called_once_with(self.downloader.video_to_download)

        mock_dl_audios.assert_called_once_with(self.audios)

        mock_process.assert_called_once_with(
            mock_dl_video.return_value,
            mock_dl_audios.return_value,
        )

        # test with customize process function

        mock_process.reset_mock()

        self.downloader.process_func = lambda x, y: None

        self.downloader.download()

        self.assertEqual(mock_process.call_count, 0)
