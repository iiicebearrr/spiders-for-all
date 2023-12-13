from spiders_for_all.database import session

SessionManager = session.SessionManager("bilibili.db")

Session = SessionManager.session
