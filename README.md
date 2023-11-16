<h1 align="center">Welcome to bilibili-spider 👋</h1>
<p>
</p>

> 爬取/下载/展示bilibili综合热门/每周必看/入站必刷/排行榜视频数据信息

[![codecov](https://codecov.io/github/iiicebearrr/bilibili-spiders/graph/badge.svg?token=7OysUawUSl)](https://codecov.io/github/iiicebearrr/bilibili-spiders)

## Install

### Using pip

```sh
git clone https://github.com/iiicebearrr/bilibili-spiders.git 
cd bilibili-spiders
# Make sure your python version >= 3.12
python -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Using docker

```sh
git clone https://github.com/iiicebearrr/bilibili-spiders.git 
cd bilibili-spiders
docker build -t bilibili-spiders .
docker run --name bs -d bilibili-spiders
```

*Now you can connect to the container or run command locally using
like `docker exec bs python -m bilibili list-spiders`*

## Usage

### Cli

#### List all spiders

```sh
python -m bilibili list-spiders
```

#### Run a spider

*Before run a spider, you should run `python -m bilibili.db` to initialize database*

```sh
python -m bilibili run-spider -n precious
```

or, use an alias:

```sh
python -m bilibili run-spider -n 入站必刷
```

#### Analysis crawled data

```sh
python -m bilibili data-analysis -n precious
```

#### Download a video by bvid

*Note: Before downloading the video, you should install `ffmpeg` on your host first*

```sh
python -m bilibili download-video -b BV1hx411w7MG -s ./videos_dl
```

#### Download a high quality video by bvid and session data

*How to get your {SESS_DATA}:*

- Open your edge/chrome browser
- Login to bilibili
- Press `F12` to open developer tools
- Refresh the page
- Click `Network` tab
- Choose any request
- Find `SESSDATA` in `Request Headers` section and copy it

```sh
python -m bilibili download-video -b BV1hx411w7MG -s ./videos_dl -d {SESS_DATA}
```

### Code

#### Run a spider

```python
from bilibili.spiders import PreciousSpider

if __name__ == '__main__':
    spider = PreciousSpider()
    spider.run()
```

#### Analysis crawled data

```python
from bilibili.analysis import Analysis
from bilibili import db

if __name__ == '__main__':
    analysis = Analysis(db.BilibiliPreciousVideos)
    analysis.show()
```

#### Download a video by bvid

```python
from bilibili.download import Downloader

if __name__ == '__main__':
    downloader = Downloader(
        bvid='BV1hx411w7MG',
        save_path='./videos_dl',
        sess_data="YOUR_SESS_DATA_HERE"
    )
    downloader.download()
```

## Spiders Reference

#### PopularSpider

TODO

#### WeeklySpider

TODO

#### PreciousSpider

TODO

#### RankSpider

TODO

## Customize your own spider

#### Inherit `core.base.Spider`

```python
from core.base import Spider


class CustomSpider(Spider):
    api = "Your api url to request"
    name = "Your spider name"
    alias = "Your spider alias"

    # database model to save all your crawled data
    database_model = YourDatabaseModel  # type: db.Base

    # item model to validate your crawled data
    item_model = YourItemModel  # type: pydantic.BaseModel

    # response model to validate your api response
    response_model = YourResponseModel  # type: pydantic.BaseModel

    def run(self):
        # Your spider logic here.
        # Note: You must implement this method.
        pass

```

## Author

👤 **iiiicebeaaaar@gmail.com**

* Github: [@iiiicebeaaaar](https://github.com/iiiicebeaaaar)

## Show your support

Give a ⭐️ if this project helped you!

***
_This README was generated with ❤️ by [readme-md-generator](https://github.com/kefranabg/readme-md-generator)_