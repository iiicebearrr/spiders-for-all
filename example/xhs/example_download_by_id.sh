# Download note(s) by note id(s)

python -m spiders_for_all xhs download-by-id -i 659b671600000000110305b8,6598fac8000000001a0296a3 -s /tmp/xhs_download_by_id

# Download note(s) by sql
python -m spiders_for_all xhs download-by-sql "select note_id from t_xhs_author_notes limit 5" -s /tmp/xhs_download_by_sql
