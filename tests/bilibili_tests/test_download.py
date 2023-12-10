import logging
from typing import Any
from unittest import TestCase, mock
from pathlib import Path
from spiders_for_all.bilibili import download, models
from spiders_for_all.conf import settings
from rich.progress import TaskID, Progress
from rich.console import Console


class TestTask(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.video_for_test = models.PlayVideo(
            base_url="test_base_url",
            codecs="test_codecs",
            id=0,  # type: ignore
            backup_url=["test_backup_url_1", "test_backup_url_2"],
        )

        cls.audio_for_test = models.PlayAudio(
            base_url="test_base_url",
            backup_url=["test_backup_url_1", "test_backup_url_2"],
            id=0,  # type: ignore
        )

    def test_base_task(self):
        class _Task(download.BaseTask):
            def start(self) -> Any:
                pass

        t = _Task()

        self.assertFalse(t.finished)

    def test_liner_task(self):
        mock_fn = mock.Mock()

        t = download.LinerTask(
            mock_fn,
            name="liner task",
            args=(1, 2, 3),
            kwargs={"a": 1, "b": 2},
        )

        t.start()

        self.assertEqual(t.task_name, "liner task")

        mock_fn.assert_called_once_with(1, 2, 3, a=1, b=2)

        self.assertTrue(t.finished)

    def test_liner_task_delay(self):
        class _T:
            def __init__(self):
                self.value = None

        def fn_set_value(instance: _T, value: int):
            instance.value = value

        mock_fn = mock.Mock()

        inst = _T()

        task_pre = download.LinerTask(fn_set_value, args=(inst, 1))
        task_post = download.LinerTask(mock_fn, delay_args=lambda: (inst.value,))
        task_no_delay = download.LinerTask(mock_fn, args=(inst.value,))

        task_pre.start()
        task_post.start()
        task_no_delay.start()

        self.assertEqual(inst.value, 1)

        mock_fn.assert_has_calls(
            [
                mock.call(1),
                mock.call(None),
            ]
        )

    @mock.patch("spiders_for_all.bilibili.download.open", new_callable=mock.mock_open)
    @mock.patch("spiders_for_all.bilibili.download.Path.unlink")
    @mock.patch("spiders_for_all.bilibili.download.requests.get")
    def test_download_media_task(
        self,
        mock_get: mock.Mock,
        mock_unlink: mock.Mock,
        mock_open: mock.Mock,
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
            headers={"Content-Length": "3"},
        )

        mock_stream_response = mock.Mock(
            __enter__=mock.Mock(return_value=mock_response),
            __exit__=mock.Mock(return_value=False),
        )

        mock_get.return_value = mock_stream_response

        download_media_task = download.DownloadMediaTask(
            media=self.audio_for_test,
            save_dir="test_save_dir",
        )

        mock_unlink.assert_called_once_with(missing_ok=True)

        it = download_media_task.start()

        total_size = next(it)

        self.assertEqual(total_size, 3)

        self.assertEqual(mock_get.call_args.args[0], "test_base_url")

        mock_response.raise_for_status.assert_called_once()

        list(it)

        mock_response.iter_content.assert_called_once_with(
            chunk_size=download_media_task.chunk_size
        )
        mock_open.assert_called_once_with(download_media_task.save_dir, "wb")
        mock_write = mock_open().write
        self.assertEqual(
            mock_write.call_args_list,
            [
                mock.call(b"test_chunk_1"),
                mock.call(b"test_chunk_2"),
                mock.call(b"test_chunk_3"),
            ],
        )
        self.assertTrue(
            download_media_task.finished,
        )

        self.assertEqual(str(download_media_task), str(self.audio_for_test))

    @mock.patch.object(download.Path, "unlink", return_value=None)
    def test_download_video_task(self, mock_unlink: mock.Mock):
        download_video_task = download.DownloadVideoTask(
            media=self.video_for_test,
            save_dir="test_save_dir",
            quality_map={0: "test_quality"},
        )

        mock_unlink.assert_called_once_with(missing_ok=True)

        self.assertDictEqual(
            download_video_task.quality_map,
            {0: "test_quality"},
        )

        self.assertEqual(
            str(download_video_task),
            "Download video <test_quality>",
        )

    @mock.patch.object(download.Path, "unlink", return_value=None)
    def test_download_audio_task(self, mock_unlink: mock.Mock):
        download_audio_task = download.DownloadAudioTask(
            media=self.audio_for_test,
            save_dir="test_save_dir",
        )

        mock_unlink.assert_called_once_with(missing_ok=True)

        self.assertEqual(
            str(download_audio_task),
            "Download audio",
        )


def get_mock_future() -> mock.Mock:
    return mock.Mock(
        spec=download.futures.Future,
        result=mock.Mock(),
    )


class TestDownloader(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bvid = "test_download_bv"
        cls.save_dir = settings.BASE_DIR / "tests" / "bilibili_tests"
        cls.ffmpeg = "ffmpeg"

        cls.videos_for_test = [
            models.PlayVideo(
                base_url=f"base url {i}",
                backup_url=[f"backup url {i}"],
                id=i,  # type: ignore
                quality=i,
                codecs=f"codecs {i}",
            )
            for i in range(10, 1, -1)
        ]

        cls.audios_for_test = [
            models.PlayAudio(
                base_url=f"base url {i}",
                backup_url=[f"backup url {i}"],
                id=i,  # type: ignore
            )
            for i in range(3)
        ]

        cls.html_test = settings.BASE_DIR / "tests" / "bilibili_tests" / "play_info.txt"

        cls.play_info_for_test = models.PlayInfoData(
            accept_quality=[cls.videos_for_test[0].quality],
            accept_description=["test"],
            dash={"video": cls.videos_for_test, "audio": cls.audios_for_test},  # type: ignore
        )

    def setUp(self):
        self.downloader, self.mock_mkdir = self.get_test_downloader(ffmpeg=self.ffmpeg)

    def get_download_media_task(self) -> download.DownloadMediaTask:
        with mock.patch.object(download.Path, "unlink"):
            return download.DownloadMediaTask(
                media=self.audios_for_test[0],
                save_dir=self.save_dir,
            )

    @classmethod
    def get_test_downloader(cls, *args, **kwargs):
        with mock.patch.object(download.Path, attribute="mkdir") as m:
            return download.Downloader(cls.bvid, cls.save_dir, *args, **kwargs), m

    def test_init(self):
        downloader = self.downloader
        self.assertEqual(downloader.bvid, self.bvid)
        self.assertEqual(downloader.save_dir, self.save_dir)
        self.assertEqual(downloader.remove_temp_dir, True)
        self.assertEqual(downloader.sess_data, None)
        self.assertEqual(downloader.quality, download.HIGHEST_QUALITY)
        self.assertEqual(downloader.codecs, None)
        self.assertEqual(downloader.ffmpeg_params, None)
        self.assertEqual(downloader.process_func, None)
        self.assertEqual(downloader.api, download.Downloader.api.format(bvid=self.bvid))
        self.assertEqual(
            downloader.from_cli,
            True,
        )
        self.assertEqual(downloader.exit_on_error, False)
        self.assertEqual(downloader.ffmpeg, "ffmpeg")
        self.assertEqual(downloader.disable_terminal_log, False)
        self.assertEqual(downloader.exit_on_error, False)
        self.assertEqual(self.mock_mkdir.call_count, 2)

        with mock.patch("spiders_for_all.bilibili.download.get_ffmpeg_executable") as m:
            m.return_value = "test_ffmpeg"

            downloader, _ = self.get_test_downloader(ffmpeg=None)

            self.assertEqual(downloader.ffmpeg, "test_ffmpeg")

            m.assert_called_once()

    def test_init_filename_with_suffix(self):
        # test filename with suffix
        filename_with_suffix = "test.mkv"
        downloader, mock_mkdir = self.get_test_downloader(
            filename=filename_with_suffix, ffmpeg="ffmpeg"
        )

        self.assertEqual(downloader.filepath, self.save_dir / filename_with_suffix)
        self.assertEqual(mock_mkdir.call_count, 2)

    @mock.patch.object(download.Console, "save_text")
    @mock.patch.object(download.Downloader, "log")
    def test_context_manager(self, mock_log: mock.Mock, mock_save_text: mock.Mock):
        with download.Downloader(
            bvid="test-bv-id", save_dir=Path("."), ffmpeg="ffmpeg"
        ) as downloader:
            self.assertEqual(downloader.state, download.DownloadState.STARTED)

            self.assertIsInstance(downloader.console, Console)

        self.assertEqual(downloader.state, download.DownloadState.FINISHED)

        mock_log.assert_called_once()

        mock_save_text.assert_called_once_with(str(downloader.log_file))

    @mock.patch.object(download.Console, "save_text")
    @mock.patch.object(download.Downloader, "log")
    def test_context_manager_with_exception(
        self, mock_log: mock.Mock, mock_save_text: mock.Mock
    ):
        with self.assertRaisesRegex(ValueError, "test error"):
            with download.Downloader(
                bvid="test-bv-id", save_dir=Path("."), ffmpeg="ffmpeg"
            ) as downloader:
                self.assertEqual(downloader.state, download.DownloadState.STARTED)

                raise ValueError("test error")

        self.assertEqual(downloader.state, download.DownloadState.FAILED)

        mock_log.assert_called_once()

        mock_save_text.assert_called_once_with(str(downloader.log_file))

    @mock.patch.object(download.Downloader, "log")
    def test_disable_terminal_log(self, mock_log: mock.Mock):
        with download.Downloader(
            bvid="test-bv-id",
            save_dir=Path("."),
            disable_terminal_log=True,
            ffmpeg="ffmpeg",
        ) as downloader:
            self.assertEqual(downloader.state, download.DownloadState.STARTED)

            self.assertEqual(downloader.disable_terminal_log, True)

            self.assertFalse(downloader.console.record)

        self.assertEqual(downloader.state, download.DownloadState.FINISHED)

        mock_log.assert_called_once()

    @mock.patch("spiders_for_all.bilibili.download.open", new_callable=mock.mock_open)
    @mock.patch("spiders_for_all.bilibili.download.Console")
    def test_console(self, mock_console: mock.Mock, mock_open: mock.Mock):
        self.downloader.get_console()

        mock_console.assert_called_once_with(record=True)

        mock_console.reset_mock()

        self.downloader.disable_terminal_log = True

        self.downloader.get_console()

        mock_open.assert_called_once_with(self.downloader.log_file, "w")

        mock_console.assert_called_with(file=mock_open())

    @mock.patch.object(download.requests, "get")
    @mock.patch.object(download.logger, "log")
    def test_get_play_info(self, mock_log: mock.Mock, mock_get: mock.Mock):
        html_mock = self.html_test.read_text(encoding="utf-8")
        mock_response = mock.Mock(
            raise_for_status=mock.Mock(),
        )
        mock_response_text = mock.PropertyMock(return_value=html_mock)

        type(mock_response).text = mock_response_text

        mock_get.return_value = mock_response

        play_info = self.downloader.get_play_info()

        mock_log.assert_called_once_with(
            logging.DEBUG,
            f"[{self.downloader.downloader_name}] Requesting {self.downloader.api}",
            exc_info=False,
        )

        self.assertEqual(mock_get.call_args.args[0], self.downloader.api)

        mock_response.raise_for_status.assert_called_once()

        mock_response_text.assert_called_once()

        self.assertIsInstance(play_info, models.PlayInfoData)

    @mock.patch.object(download.requests, "get")
    @mock.patch.object(download.logger, "log")
    def test_get_play_info_with_sess_data(
        self, mock_log: mock.Mock, mock_get: mock.Mock
    ):
        downloader, _ = self.get_test_downloader(
            sess_data="test_sess_data",
            ffmpeg="ffmpeg",
        )

        html_mock = self.html_test.read_text(encoding="utf-8")
        mock_response = mock.Mock(
            raise_for_status=mock.Mock(),
        )
        mock_response_text = mock.PropertyMock(return_value=html_mock)

        type(mock_response).text = mock_response_text

        mock_get.return_value = mock_response

        play_info = downloader.get_play_info()

        mock_log.assert_called_once_with(
            logging.DEBUG,
            f"[{self.downloader.downloader_name}] Requesting {self.downloader.api} with cookies {{'SESSDATA': 'test_sess_data'}}",
            exc_info=False,
        )

        self.assertEqual(mock_get.call_args.args[0], self.downloader.api)

        self.assertEqual(
            mock_get.call_args.kwargs["cookies"], {"SESSDATA": "test_sess_data"}
        )

        mock_response.raise_for_status.assert_called_once()

        mock_response_text.assert_called_once()

        self.assertIsInstance(play_info, models.PlayInfoData)

    def test_filter_quality_highest(self):
        filter_videos = self.downloader.filter_quality(self.videos_for_test)

        self.assertEqual(
            filter_videos[0].quality,
            10,
        )

    def test_filter_quality_specified(self):
        self.downloader.quality = 5

        filter_videos = self.downloader.filter_quality(self.videos_for_test)

        self.assertEqual(
            filter_videos[0].quality,
            5,
        )

    def test_choose_codecs_video(self):
        self.downloader.codecs = "codecs 8"
        video = self.downloader.choose_codecs(self.videos_for_test)
        self.assertEqual(
            video.codecs,
            "codecs 8",
        )

    def test_use_default_codecs_video(self):
        video = self.downloader.choose_codecs(self.videos_for_test)

        self.assertEqual(
            video.codecs,
            "codecs 10",
        )

    def test_property_videos(self):
        self.downloader.get_play_info = mock.Mock(return_value=self.play_info_for_test)

        reversed_videos = self.videos_for_test[::-1]

        self.assertListEqual(self.downloader.videos[::-1], reversed_videos)

    @mock.patch.object(download.Downloader, "choose_codecs")
    @mock.patch.object(download.Downloader, "filter_quality")
    def test_property_video_to_download(
        self, mock_filter: mock.Mock, mock_choose_codecs: mock.Mock
    ):
        video = self.videos_for_test[0]
        mock_choose_codecs.return_value = video
        mock_filter.return_value = [video]

        self.downloader.get_play_info = mock.Mock(return_value=self.play_info_for_test)

        self.assertEqual(self.downloader.video_to_download, video)

        mock_filter.assert_called_once_with(self.videos_for_test)
        mock_choose_codecs.assert_called_once_with([video])

    @mock.patch.object(download.Downloader, "filepath", new_callable=mock.PropertyMock)
    @mock.patch.object(download.Downloader, "log")
    @mock.patch.object(download, "rm_tree")
    def test_clean(
        self,
        mock_rm_tree: mock.Mock,
        mock_log: mock.Mock,
        mock_filepath: mock.Mock,
    ):
        pre_filename = self.downloader.filepath
        save_dir = self.downloader.save_dir
        new_file_path = save_dir.parent / pre_filename.name
        mock_filepath.return_value = new_file_path
        mock_rm_tree.return_value = None

        self.downloader.clean()

        self.assertEqual(self.downloader.filepath, new_file_path)

        mock_rm_tree.assert_called_once_with(self.downloader.temp_dir)

        mock_log.assert_has_calls(
            [
                mock.call(
                    f"[{self.downloader.downloader_name}] Remove temporary directory",
                    level=logging.INFO,
                ),
                mock.call(
                    f"[{self.downloader.downloader_name}] Finished. File save to: {new_file_path}",
                    level=logging.INFO,
                ),
            ]
        )

    @mock.patch.object(download.Downloader, "filepath", new_callable=mock.PropertyMock)
    @mock.patch.object(download.subprocess, "run")
    @mock.patch.object(download.Downloader, "log")
    def test_process(
        self, mock_log: mock.Mock, mock_run: mock.Mock, mock_filepath: mock.Mock
    ):
        video_path, audio_path = Path("test_video_path"), Path("test_audio_path")
        mock_filepath.return_value = Path("test_filepath")
        mock_run_result = mock.Mock()
        mock_run_result.returncode = 0
        mock_run.return_value = mock_run_result

        self.downloader.process(
            video_path=video_path,
            audio_path=audio_path,
        )

        mock_run.assert_called_once_with(
            [
                self.ffmpeg,
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                str(self.downloader.filepath),
                "-y",
            ],
            capture_output=True,
        )

        self.assertEqual(mock_log.call_count, 2)

    @mock.patch.object(download.Downloader, "filepath", new_callable=mock.PropertyMock)
    @mock.patch.object(download.subprocess, "run")
    @mock.patch.object(download.Downloader, "log")
    def test_process_failed(
        self, mock_log: mock.Mock, mock_run: mock.Mock, mock_filepath: mock.Mock
    ):
        video_path, audio_path = Path("test_video_path"), Path("test_audio_path")

        mock_run_result = mock.Mock()
        mock_run_result.returncode = 1
        mock_run_result.stderr = b"test error"
        mock_run.return_value = mock_run_result

        with self.assertRaisesRegex(ValueError, ".* failed with code 1"):
            self.downloader.process(
                video_path=video_path,
                audio_path=audio_path,
            )

    @mock.patch.object(download.Path, "unlink", return_value=None)
    @mock.patch.object(download.Downloader, "log")
    @mock.patch.object(download.DownloadVideoTask, "start")
    def test_run_task_directly(
        self, mock_task_start: mock.Mock, mock_log: mock.Mock, mock_unlink: mock.Mock
    ):
        def test_it():
            yield 1
            yield b"test_chunk_1"
            yield b"test_chunk_2"
            yield b"test_chunk_3"
            yield b"test_chunk_4"

        mock_task_start.return_value = test_it()

        task = download.DownloadVideoTask(
            media=self.videos_for_test[0],
            save_dir=self.save_dir,
            quality_map={10: "test_quality"},
        )

        self.downloader.run_task_directly(task)

        mock_task_start.assert_called_once()

        self.assertEqual(mock_log.call_count, 4)

    @mock.patch.object(download.Downloader, "get_play_info")
    @mock.patch.object(download.Path, "unlink", return_value=None)
    def test_add_video_task(
        self, mock_unlink: mock.Mock, mock_get_play_info: mock.Mock
    ):
        mock_get_play_info.return_value = self.play_info_for_test
        self.downloader.add_video_task()
        self.assertEqual(len(self.downloader.downloading_tasks), 1)

    @mock.patch.object(download.Downloader, "get_play_info")
    @mock.patch.object(download.Path, "unlink", return_value=None)
    def test_add_audio_task(
        self, mock_unlink: mock.Mock, mock_get_play_info: mock.Mock
    ):
        mock_get_play_info.return_value = self.play_info_for_test
        self.downloader.add_audio_task()
        self.assertEqual(
            len(self.downloader.downloading_tasks),
            len(self.play_info_for_test.dash.audio),
        )

    def test_prepare_tasks(self):
        downloader = self.downloader

        downloader.prepare_tasks()

        tasks = downloader.tasks

        self.assertEqual(tasks[0].fn, downloader.add_video_task)
        self.assertEqual(tasks[1].fn, downloader.add_audio_task)
        self.assertEqual(tasks[2].fn, downloader.download_with_progress)
        self.assertEqual(tasks[3].fn, downloader.concat_audio)
        self.assertEqual(tasks[4].fn, downloader.process)
        self.assertEqual(tasks[5].fn, downloader.clean)

    def test_prepare_tasks_directly(self):
        downloader = self.downloader

        downloader.from_cli = False

        downloader.prepare_tasks()

        tasks = downloader.tasks

        self.assertEqual(tasks[2].fn, downloader.download_directly)

    def test_prepare_tasks_with_custom_process_func(self):
        downloader = self.downloader

        downloader.process_func = mock.Mock()

        downloader.prepare_tasks()

        tasks = downloader.tasks

        self.assertEqual(tasks[4].fn, downloader.process_func)

    @mock.patch.object(download.LinerTask, "start")
    @mock.patch.object(download.Downloader, "log")
    def test_run_tasks(self, mock_log: mock.Mock, mock_task_start: mock.Mock):
        self.downloader.prepare_tasks()
        self.downloader.run_tasks()

        self.assertEqual(
            mock_log.call_count,
            len(self.downloader.tasks),
        )

        self.assertEqual(
            mock_task_start.call_count,
            len(self.downloader.tasks),
        )

    @mock.patch.object(download.LinerTask, "start")
    def test_iter_tasks(self, mock_task_start: mock.Mock):
        self.downloader.prepare_tasks()

        self.assertEqual(
            list(self.downloader.iter_tasks()),
            self.downloader.tasks,
        )

        self.assertEqual(
            mock_task_start.call_count,
            len(self.downloader.tasks),
        )

    @mock.patch.object(download.Downloader, "run_tasks")
    def test_download(self, mock_run_tasks: mock.Mock):
        self.downloader.download()

        mock_run_tasks.assert_called_once()

    @mock.patch.object(download.Downloader, "iter_tasks")
    def test_download_yield(self, mock_iter_tasks: mock.Mock):
        mock_iter_tasks.return_value = [1, 2, 3]

        self.assertEqual(
            list(self.downloader.download(yield_tasks=True)),
            [1, 2, 3],
        )
        mock_iter_tasks.assert_called_once()

    @mock.patch.object(download.Path, "unlink", return_value=None)
    @mock.patch.object(download.DownloadMediaTask, "start")
    def test__update_progress(
        self,
        mock_task_start: mock.Mock,
        mock_unlink: mock.Mock,
    ):
        def test_it(_task: download.DownloadMediaTask):
            yield 10
            yield b"123"
            yield b"456"
            yield b"789"
            yield b"0"
            _task._finished = True

        task = download.DownloadMediaTask(
            media=self.videos_for_test[0],
            save_dir=self.save_dir,
        )

        progress_task_id = TaskID(0)

        mock_progress = mock.Mock(spec=Progress)

        mock_progress.start_task.return_value = None

        mock_progress.update.return_value = None

        mock_task_start.return_value = test_it(task)

        self.downloader._update_progress(task, progress_task_id, mock_progress)

        mock_progress.start_task.assert_called_once_with(progress_task_id)

        mock_progress.update.assert_has_calls(
            [
                mock.call(progress_task_id, total=10, advance=3),
                mock.call(progress_task_id, total=10, advance=3),
                mock.call(progress_task_id, total=10, advance=3),
                mock.call(progress_task_id, total=10, advance=1),
            ]
        )

    @mock.patch.object(download.Downloader, "handle_tasks")
    @mock.patch.object(download.futures.ThreadPoolExecutor, "submit")
    @mock.patch("spiders_for_all.bilibili.download.Progress")
    def test_download_with_progress(
        self,
        mock_progress: mock.Mock,
        mock_submit: mock.Mock,
        mock_handle_tasks: mock.Mock,
    ):
        mock_handle_tasks.side_effect = None

        mock_progress_instance = mock.Mock(
            add_task=mock.Mock(),
        )

        mock_progress.return_value = mock.Mock(
            __enter__=mock.Mock(return_value=mock_progress_instance),
            __exit__=mock.Mock(return_value=False),
        )

        tasks = [1, 2, 3, 4, 5]

        self.downloader.downloading_tasks = tasks

        self.downloader.download_with_progress()

        mock_progress.assert_called_once()

        self.assertEqual(
            mock_progress_instance.add_task.call_count,
            len(tasks),
        )

        self.assertEqual(
            mock_submit.call_count,
            len(tasks),
        )

        mock_handle_tasks.assert_called_once()

    @mock.patch.object(download.Downloader, "handle_tasks")
    @mock.patch.object(download.futures.ThreadPoolExecutor, "submit")
    def test_download_directly(
        self, mock_submit: mock.Mock, mock_handle_tasks: mock.Mock
    ):
        tasks = [1, 2, 3, 4, 5]

        self.downloader.downloading_tasks = tasks

        self.downloader.download_directly()

        self.assertEqual(
            mock_submit.call_count,
            len(tasks),
        )

        mock_handle_tasks.assert_called_once()

    @mock.patch.object(download.Path, "unlink", return_value=None)
    @mock.patch.object(download.Downloader, "log")
    @mock.patch.object(download.Path, "read_bytes")
    @mock.patch("spiders_for_all.bilibili.download.open", new_callable=mock.mock_open)
    def test_concat_audio_video(
        self,
        mock_open: mock.Mock,
        mock_read_bytes: mock.Mock,
        mock_log: mock.Mock,
        mock_unlink: mock.Mock,
    ):
        self.downloader.audio_temp_path = Path("test_audio_temp_path")
        self.downloader.downloading_tasks = [
            download.DownloadVideoTask(
                media=self.videos_for_test[0],
                save_dir=self.save_dir,
                quality_map={10: "test_quality"},
            ),
            download.DownloadAudioTask(
                media=self.audios_for_test[0],
                save_dir=self.save_dir,
            ),
        ]

        self.downloader.concat_audio()

        mock_open.assert_called_once_with(
            self.downloader.audio_temp_path,
            "wb",
        )

        mock_write = mock_open().write

        mock_write.assert_called_once()

        mock_read_bytes.assert_called_once()

        mock_log.assert_called_once()

    @mock.patch.object(download.futures, "as_completed")
    def test_handle_tasks(self, mock_as_completed: mock.Mock):
        tasks = {get_mock_future(): self.get_download_media_task() for _ in range(10)}

        mock_as_completed.return_value = tasks.keys()

        self.downloader.handle_tasks(tasks)

        mock_as_completed.assert_called_once_with(tasks)

        for f in tasks:
            f.result.assert_called_once()

    @mock.patch.object(download.Downloader, "log")
    @mock.patch("spiders_for_all.bilibili.download.exit")
    @mock.patch.object(download.futures, "as_completed")
    def test_handle_tasks_failed(
        self, mock_as_completed: mock.Mock, mock_exit: mock.Mock, mock_log: mock.Mock
    ):
        mock_future = get_mock_future()
        mock_future.result.side_effect = ValueError("test error")
        tasks = {mock_future: self.get_download_media_task()}
        mock_as_completed.return_value = tasks.keys()

        self.downloader.exit_on_error = True
        self.downloader.handle_tasks(tasks)

        mock_as_completed.assert_called_once_with(tasks)

        mock_log.assert_called_once()

        mock_exit.assert_called_once_with(1)


class TestMultiThreadDownloader(TestCase):
    def setUp(self):
        self.downloader_without_init = self.get_downloader_without_init()
        self.downloader = self.get_downloader()

    def get_downloader_without_init(self) -> download.MultiThreadDownloader:
        with mock.patch.object(
            download.MultiThreadDownloader, "__init__", return_value=None
        ):
            return download.MultiThreadDownloader()

    @mock.patch.object(download.Downloader, "get_logfile")
    @mock.patch.object(download.Path, "unlink")
    @mock.patch.object(download.Path, "mkdir")
    def get_downloader(
        self, mock_mkdir: mock.Mock, mock_unlink: mock.Mock, mock_get_logfile: mock.Mock
    ) -> download.MultiThreadDownloader:
        return download.MultiThreadDownloader(
            bvid_list=["test_bv1", "test_bv2"],
            save_dir=Path("test_save_dir"),
            ffmpeg="ffmpeg",
        )

    def get_sub_downloader(self) -> download.Downloader:
        with mock.patch.object(download.Path, "unlink"):
            return download.Downloader(
                bvid="test_bv1",
                save_dir=Path("test_save_dir"),
                ffmpeg="ffmpeg",
            )

    def test_read_bvid_list_from_str(self):
        downloader = self.downloader_without_init

        # comma separated
        self.assertEqual(
            downloader.read_bvid_list("test_bv1, test_bv2"),
            ["test_bv1", "test_bv2"],
        )

        # space separated
        self.assertEqual(
            downloader.read_bvid_list("test_bv1 test_bv2"),
            ["test_bv1", "test_bv2"],
        )

        # \n separated
        self.assertEqual(
            downloader.read_bvid_list("test_bv1\ntest_bv2"),
            ["test_bv1", "test_bv2"],
        )

        # \t separated
        self.assertEqual(
            downloader.read_bvid_list("test_bv1\ttest_bv2"),
            ["test_bv1", "test_bv2"],
        )

        # \t\n\s mixed
        self.assertEqual(
            downloader.read_bvid_list("test_bv1\ttest_bv2\ntest_bv3 test_bv4"),
            ["test_bv1", "test_bv2", "test_bv3", "test_bv4"],
        )

    def test_read_bvid_list_from_path_object(self):
        downloader = self.downloader_without_init
        with mock.patch.object(download.Path, "read_text") as mock_read_text:
            mock_read_text.return_value = "test_bv1\ttest_bv2\ntest_bv3 test_bv4"
            self.assertEqual(
                downloader.read_bvid_list(Path("test_path")),
                ["test_bv1", "test_bv2", "test_bv3", "test_bv4"],
            )

    def test_read_bvid_list_from_file_like_object(self):
        downloader = self.downloader_without_init

        mock_file_like_object = mock.Mock(spec=download.BinaryIO)
        mock_file_like_object.read.return_value = (
            b"test_bv1\ttest_bv2\ntest_bv3 test_bv4"
        )

        self.assertEqual(
            downloader.read_bvid_list(mock_file_like_object),
            ["test_bv1", "test_bv2", "test_bv3", "test_bv4"],
        )

    def test_read_bvid_list_from_list_of_any(self):
        downloader = self.downloader_without_init

        with mock.patch.object(download.Path, "read_text") as mock_read_text:
            mock_read_text.return_value = "test_bv1\ntest_bv2"

            mock_file_like_object = mock.Mock(
                spec=download.BinaryIO,
                read=mock.Mock(return_value=b"test_bv3\ntest_bv4"),
            )

            self.assertEqual(
                downloader.read_bvid_list(
                    ["test_bv5", Path("test_path"), mock_file_like_object]
                ),
                ["test_bv5", "test_bv1", "test_bv2", "test_bv3", "test_bv4"],
            )

    def test_invalid_bvid_list(self):
        downloader = self.downloader_without_init

        with self.assertRaisesRegex(
            TypeError, "bvid_list should be str, Path, BinaryIO or list, got"
        ):
            downloader.read_bvid_list(1)

    @mock.patch.object(download.MultiThreadDownloader, "handle_tasks")
    @mock.patch.object(download.futures.ThreadPoolExecutor, "submit")
    def test_download_directly(
        self, mock_submit: mock.Mock, mock_handle_tasks: mock.Mock
    ):
        self.downloader.download_directly()

        self.assertEqual(
            mock_submit.call_count,
            len(self.downloader.bvid_list),
        )

        mock_handle_tasks.assert_called_once()

    @mock.patch.object(download.Downloader, "log")
    @mock.patch.object(download.logger, "info")
    @mock.patch.object(download.Path, "rename")
    @mock.patch.object(download.Downloader, "filepath", new_callable=mock.PropertyMock)
    @mock.patch.object(download.LinerTask, "start")
    @mock.patch("spiders_for_all.bilibili.download.Progress")
    def test__worker_update_progress(
        self,
        mock_progress: mock.Mock,
        mock_start_task: mock.Mock,
        mock_filepath: mock.Mock,
        mock_rename: mock.Mock,
        mock_log: mock.Mock,
        mock_sub_log: mock.Mock,
    ):
        task_id, overall_task_id = TaskID(0), TaskID(1)
        mock_filepath.return_value = Path("test_filepath")
        mock_start_task.return_value = None
        mock_progress.update.return_value = None
        mock_progress.remove_task.return_value = None
        mock_progress.add_task.return_value = task_id

        sub_downloader = self.get_sub_downloader()
        self.downloader._worker_update_progress(
            downloader=sub_downloader,
            progress=mock_progress,
            overall_task_id=overall_task_id,
        )

        self.assertEqual(self.downloader.success_count, 1)

        self.assertEqual(self.downloader.failed_count, 0)

        self.assertEqual(
            mock_progress.update.call_count,
            len(sub_downloader.tasks) + 3,
        )

        mock_progress.remove_task.assert_called_once_with(task_id)

        mock_progress.add_task.assert_called_once()

        self.assertEqual(mock_rename.call_count, 2)

    @mock.patch.object(download.logger, "info")
    @mock.patch.object(download.MultiThreadDownloader, "handle_tasks")
    @mock.patch.object(download.futures.ThreadPoolExecutor, "submit")
    @mock.patch("spiders_for_all.bilibili.download.Progress")
    def test_download_with_progress(
        self,
        mock_progress: mock.Mock,
        mock_submit: mock.Mock,
        mock_handle_tasks: mock.Mock,
        mock_log: mock.Mock,
    ):
        mock_handle_tasks.side_effect = None

        mock_progress_instance = mock.Mock(
            add_task=mock.Mock(),
            start_task=mock.Mock(),
        )

        mock_progress.return_value = mock.Mock(
            __enter__=mock.Mock(return_value=mock_progress_instance),
            __exit__=mock.Mock(return_value=False),
        )

        self.downloader.download_with_progress()

        mock_progress.assert_called_once()

        mock_progress_instance.assert_has_calls(
            [
                mock.call.add_task(
                    "[green] All jobs: ", total=len(self.downloader.bvid_list), event=""
                ),
            ]
        )

        self.assertEqual(
            mock_progress_instance.add_task.call_count,
            1,
        )

        mock_handle_tasks.assert_called_once()

        self.assertEqual(
            mock_submit.call_count,
            len(self.downloader.bvid_list),
        )

        mock_log.assert_called_once()

    def test_download(self):
        with mock.patch.object(
            download.MultiThreadDownloader, "download_with_progress"
        ) as mock_download_with_progress:
            self.downloader.download()
            mock_download_with_progress.assert_called_once()

        with mock.patch.object(
            download.MultiThreadDownloader, "download_directly"
        ) as mock_download_directly:
            self.downloader.from_cli = False
            self.downloader.download()
            mock_download_directly.assert_called_once()

    @mock.patch.object(download.futures, "as_completed")
    def test_handle_tasks(self, mock_as_completed: mock.Mock):
        tasks = {get_mock_future(): self.get_sub_downloader() for _ in range(10)}

        mock_as_completed.return_value = tasks.keys()

        self.downloader.handle_tasks(tasks)

        mock_as_completed.assert_called_once_with(tasks)

        for f in tasks:
            f.result.assert_called_once()

    @mock.patch.object(download.logger, "error")
    @mock.patch("spiders_for_all.bilibili.download.exit")
    @mock.patch.object(download.futures, "as_completed")
    def test_handle_tasks_failed(
        self, mock_as_completed: mock.Mock, mock_exit: mock.Mock, mock_log: mock.Mock
    ):
        mock_future = get_mock_future()
        mock_future.result.side_effect = ValueError("test error")
        tasks = {mock_future: self.get_sub_downloader()}
        mock_as_completed.return_value = tasks.keys()

        self.downloader.exit_on_error = True
        self.downloader.handle_tasks(tasks)

        mock_as_completed.assert_called_once_with(tasks)

        mock_log.assert_called_once()

        mock_exit.assert_called_once_with(1)
