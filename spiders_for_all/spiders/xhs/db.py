from spiders_for_all.database import session

SessionManager = session.SessionManager("xhs.db")

Session = SessionManager.session
