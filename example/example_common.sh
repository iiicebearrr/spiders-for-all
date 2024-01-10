# This is example of common functions

# Example: List all tables
python -m spiders_for_all database list-schema

# Example: Execute sql
python -m spiders_for_all database sql "select title, bvid from t_bilibili_author_video limit 5"
