from spiders_for_all.core import db

SessionMaker = db.SessionMaker("xhs.db")

Session = SessionMaker.session
