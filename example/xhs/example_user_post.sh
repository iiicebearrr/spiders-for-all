# Get notes of the user's main page(Only the first page)
# NOTE: For now, the other page notes are not supported due to the sign algorithm of xhs
python -m spiders_for_all xhs spider-author 5a8e92fc11be1001e0974f9e

# Get and download the user's post notes
python -m spiders_for_all xhs spider-author 5a8e92fc11be1001e0974f9e -s /tmp/xhs_spider_user_post -w "author_id='5a8e92fc11be1001e0974f9e'"
