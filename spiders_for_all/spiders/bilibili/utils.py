from spiders_for_all.core.client import HttpClient


def get_buvid3(client: HttpClient | None = None):
    if isinstance(client, HttpClient):
        client = client.new()
    else:
        client = HttpClient()

    client.headers.update(
        {
            "referer": "https://space.bilibili.com/2/dynamic",
        }
    )  # type: ignore

    with client:  # type: ignore
        r = client.get("https://api.bilibili.com/x/frontend/finger/spi")  # type: ignore
        data = r.json()
        buvid3 = data.get("data", {}).get("b_3", None)
        if buvid3 is None:
            raise ValueError(f"Failed to get buvid3 from: {data}")
        return buvid3


if __name__ == "__main__":
    print(get_buvid3())
