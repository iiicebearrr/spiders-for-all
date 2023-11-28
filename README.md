# 欢迎来到 bilibili-spiders

[![codecov](https://codecov.io/github/iiicebearrr/bilibili-spiders/graph/badge.svg?token=7OysUawUSl)](https://codecov.io/github/iiicebearrr/bilibili-spiders)

> 爬取/下载/展示bilibili综合热门/每周必看/入站必刷/排行榜视频数据信息



https://github.com/iiicebearrr/bilibili-spiders/assets/110714291/5b42abb8-9f18-404e-ba0f-407b817eef48



## 目录

- [安装](#安装)
- [使用方法](#使用方法)
    - [命令行](#命令行)
        - [列出内置的爬虫](#列出内置的爬虫)
        - [运行一个爬虫](#运行一个爬虫)
        - [分析爬取的数据](#分析爬取的数据)
        - [通过bvid下载视频](#通过bvid下载视频)
        - [指定SESS_DATA下载高清视频](#指定sess_data下载高清视频)
    - [代码](#代码)
- [内置爬虫](#内置爬虫)
- [定制你自己的爬虫](#定制你自己的爬虫)

## 安装

```sh
pip install spiders-for-all # python 版本 >= 3.10
```

## 使用方法

### 命令行

#### 列出内置的爬虫

```sh
python -m spiders_for_all list-spiders
```

#### 运行一个爬虫

**通过爬虫名称运行:**

```sh
python -m spiders_for_all run-spider -n precious
```

**或通过别名**:

```sh
python -m spiders_for_all run-spider -n 入站必刷
```

#### 分析爬取的数据

```sh
python -m spiders_for_all data-analysis -n precious
```

#### 通过bvid下载视频

*注意: 在下载视频前, 你需要确保你的主机上已安装了`ffmpeg`, 如果是使用docker方式启动, 则可以忽略这一步*

```sh
python -m spiders_for_all download-video -b BV1hx411w7MG -s ./videos_dl
```

#### 指定SESS_DATA下载高清视频

*如何获取SESS_DATA*

- 网页登陆bilibili
- 按`F12`打开开发者工具
- 刷新页面
- 打开`Network`选项卡
- 选中任何一个包含`Cookies`的请求
- 复制`Request Headers`中的`Cookie`字段中的`SESSDATA`值

```sh
python -m spiders_for_all download-video -b BV1hx411w7MG -s ./videos_dl -d {SESS_DATA}
```

#### 查看帮助

```sh
python -m spiders_for_all --help
```

### 代码

#### 运行爬虫

```python

from spiders_for_all.bilibili.spiders import PreciousSpider

if __name__ == '__main__':
    spider = PreciousSpider()
    spider.run()
```

#### 分析爬取的数据

```python
from spiders_for_all.bilibili.analysis import Analysis
from spiders_for_all.bilibili import db

if __name__ == '__main__':
    analysis = Analysis(db.BilibiliPreciousVideos)
    analysis.show()
```

#### 通过bvid下载视频

```python
from spiders_for_all.bilibili.download import Downloader

if __name__ == '__main__':
    downloader = Downloader(
        bvid='BV1hx411w7MG',
        save_path='./videos_dl',
        sess_data="YOUR_SESS_DATA_HERE"
    )
    downloader.download()
```

## 定制你自己的爬虫

```python

from spiders_for_all.core.base import Spider


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
