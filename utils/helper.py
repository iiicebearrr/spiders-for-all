from fake_useragent import UserAgent

ua = UserAgent()


def user_agent_headers() -> dict[str, str]:
    return {
        "User-Agent": ua.random,
    }
