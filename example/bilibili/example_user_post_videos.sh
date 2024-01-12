# Download 1 videos of the author, if -t not set, it will download all videos of the author
# Note: This command will only download the videos crawled this time,
#       which means if the local database has storaged 10 items for the author,
#       but you run this command with -t 1, it will only download 1 video.
#       If you want to download videos denpend on the database, you should use:
#           - run-spider author -p mid {userid} -w "where sql" -s {save_path} --download-only
#       or
#           - download-by-sql "sql to get bvid list" -s {save_path}
python -m spiders_for_all bilibili download-by-author -m 31283043 -s /tmp/bilibili_download_by_author -t 1
