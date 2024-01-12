# download by bvid
python -m spiders_for_all bilibili download-by-id -b BV1xJ411x7fd -s /tmp/bilibili_download_video

# multiple download
python -m spiders_for_all bilibili download-by-ids -b BV1HM411h7YB,BV1rG4y1j7TJ -s /tmp/bilibili_download_videos

# download by sql
python -m spiders_for_all bilibili download-by-sql "select bvid from t_bilibili_author_video limit 5" -s /tmp/bilibili_download_videos_by_sql
