# Spiders for all

[![codecov](https://codecov.io/github/iiicebearrr/bilibili-spiders/graph/badge.svg?token=7OysUawUSl)](https://codecov.io/github/iiicebearrr/bilibili-spiders)

> 爬取、下载哔哩哔哩、小红书等网站数据、视频, 持续更新中...



https://github.com/iiicebearrr/bilibili-spiders/assets/110714291/5b42abb8-9f18-404e-ba0f-407b817eef48



## Features

- bilibli 

    - [x] 提供bvid下载视频
    - [x] 提供bvid列表、文件批量下载视频
    - [x] 提供SESS_DATA下载高清视频
    - [x] 内置爬虫一键下载
        - [x] 【综合热门】栏目视频爬取、下载
        - [x] 【每周必看】栏目视频爬取、下载
        - [x] 【入站必刷】栏目视频爬取、下载
        - [x] 【排行榜】各分栏目视频爬取、下载
        - [x]  爬取数据可视化
        - [ ]  爬取某作者的所有视频

- 小红书(Coming soon)

- GUI(Coming soon)

## 目录

- [Spiders for all](#spiders-for-all)
  - [Features](#features)
  - [目录](#目录)
  - [安装](#安装)
  - [使用方法(bilibili)](#使用方法bilibili)
    - [命令行](#命令行)
      - [列出内置的爬虫](#列出内置的爬虫)
      - [运行一个爬虫](#运行一个爬虫)
      - [分析爬取的数据](#分析爬取的数据)
      - [通过bvid下载视频](#通过bvid下载视频)
      - [指定SESS\_DATA下载高清视频](#指定sess_data下载高清视频)
      - [查看帮助](#查看帮助)
    - [代码](#代码)
      - [运行爬虫](#运行爬虫)
      - [分析爬取的数据](#分析爬取的数据-1)
      - [通过bvid下载视频](#通过bvid下载视频-1)
  - [内置爬虫](#内置爬虫)

## 安装

```sh
pip install spiders-for-all # python 版本 >= 3.10
```

## 使用方法(bilibili)

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
        save_dir='./videos_dl',
        sess_data="YOUR_SESS_DATA_HERE"
    )
    downloader.download()
```

## 内置爬虫


*通过`list-spiders`列出内置的爬虫:*
```sh
python -m spiders_for_all list-spiders
```

*备注: 包含参数的爬虫:*

- 每周必看(`spiders_for_all.bilibili.spiders.WeeklySpider`):

    - 不传参数的情况下默认爬取最新一期的视频
    - 通过`-p week {week}`指定爬取第几期的视频, 比如`-p week 1`表示爬取第一期的视频
