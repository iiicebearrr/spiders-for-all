from fake_useragent import UserAgent

ua = UserAgent()


def user_agent_headers():
    return {
        "User-Agent": ua.random,
    }
