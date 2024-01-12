BASE="python -m spiders_for_all"

# Run built-in spiders
# NOTE: weekly spider now need w_rid parameter, which has not been solved yet.
# ${BASE} bilibili run-spider weekly
# Spiders now available:
${BASE} bilibili run-spider popular -p total 100
${BASE} bilibili run-spider precious
${BASE} bilibili run-spider rank_all
${BASE} bilibili run-spider rank_drama
${BASE} bilibili run-spider rank_cn_cartoon
${BASE} bilibili run-spider rank_cn_related
${BASE} bilibili run-spider rank_documentary
${BASE} bilibili run-spider rank_cartoon
${BASE} bilibili run-spider rank_music
${BASE} bilibili run-spider rank_dance
${BASE} bilibili run-spider rank_game
${BASE} bilibili run-spider rank_tech
${BASE} bilibili run-spider rank_knowledge
${BASE} bilibili run-spider rank_sport
${BASE} bilibili run-spider rank_car
${BASE} bilibili run-spider rank_life
${BASE} bilibili run-spider rank_food
${BASE} bilibili run-spider rank_animal
${BASE} bilibili run-spider rank_auto_tune
${BASE} bilibili run-spider rank_fashion
${BASE} bilibili run-spider rank_ent
${BASE} bilibili run-spider rank_film
${BASE} bilibili run-spider rank_movie
${BASE} bilibili run-spider rank_tv
${BASE} bilibili run-spider rank_variety
${BASE} bilibili run-spider rank_origin
${BASE} bilibili run-spider rank_new

# Author spider, which is a little different from others
# ${BASE} bilibili run-spider author \
#   -p mid xxx       # [required] mid is the author id, which can be found in the url of the author's homepage
#   -p total 10      # [optional] total is the number of videos to be crawled, if not specified, all videos will be crawled
#   -p sess_data xxx # [optional] sess_data is the cookie value of SESSDATA, which can be found in the cookie of the author's homepage
#   ... other parameters, see --help for more details, or check the readme.md

# example 1: crawl the first 1 videos of some author
${BASE} bilibili run-spider author -p mid 31283043 -p total 1

# example 2: crawl the first 1 videos of some author and download them
# Note: `run-spider` is a general command, you should specify the videos to be downloaded by `-w "sql_where_clause"`
#       You can also use `download-by-author` or `download-by-sql` command to avoid this
${BASE} bilibili run-spider author -p mid 31283043 -p total 1 -w "mid=31283043" -s /tmp/bilibili_author_videos

# example 3: Download the specified videos of the author directly without crawling
#   You should run the spider first to make sure the local database has the video information
#   Instead of using `run-spider`, `download-by-sql` or `download-by-author` is recommended
${BASE} bilibili run-spider author -p mid 31283043 -w "mid=31283043 limit 3" -s /tmp/bilibili_author_videos -d

# example 4: crawl all videos of some author
# NOTE: This may take a very long time due to the risk control strategy of bilibili api
${BASE} bilibili run-spider author -p mid 40966108
