from fake_useragent import UserAgent  # type: ignore

ua = UserAgent()


def user_agent_headers() -> dict[str, str]:
    return {
        "User-Agent": ua.random,
    }
