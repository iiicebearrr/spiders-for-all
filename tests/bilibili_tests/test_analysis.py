from unittest import mock
from tests._utils import DbBindTestCase
from spiders_for_all.bilibili import analysis, db


class TestAnalysis(DbBindTestCase):
    def test_key(self):
        model = analysis.Analysis(db.BaseBilibiliVideos)
        self.assertEqual(model._key((1, (1, 2))), 1)

    def test_url_field(self):
        model = analysis.Analysis(db.BaseBilibiliPlay)
        self.assertEqual(model.url_field, "url")
        model = analysis.Analysis(db.BaseBilibiliVideos)
        self.assertEqual(model.url_field, "short_link_v2")

    @mock.patch("spiders_for_all.bilibili.analysis.print", return_value=None)
    def test_show(self, mock_rich_print: mock.Mock):
        analyzer = analysis.Analysis(db.BilibiliPopularVideos)
        analyzer.show()
        mock_rich_print.assert_called_with(analyzer.table)
        analyzer = analysis.Analysis(db.BilibiliRankCnCartoon)
        analyzer.show()
        mock_rich_print.assert_called_with(analyzer.table)
