<p align="center">
<img src="docs/logo.png" height="200px"/>
</p>





[![codecov](https://codecov.io/github/iiicebearrr/spiders-for-all/graph/badge.svg?token=7OysUawUSl)](https://codecov.io/github/iiicebearrr/spiders-for-all)

> 爬取、下载哔哩哔哩、小红书等网站数据、视频, 持续更新中...

https://github.com/iiicebearrr/spiders-for-all/assets/110714291/d28e67f5-8ff2-4e39-b6de-14434cfb9804

https://github.com/iiicebearrr/spiders-for-all/assets/110714291/4696cd19-0940-451c-9206-c03efe4a65a5

https://github.com/iiicebearrr/spiders-for-all/assets/110714291/53079374-6c28-4b41-9b89-ed6ab5fb40a2

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
        - [x]  爬取某作者的所有视频

- 小红书(Coming soon)

- GUI(Coming soon)

## 目录

- [Features](#features)
- [目录](#目录)
- [安装](#安装)
- [使用方法(bilibili)](#使用方法bilibili)
  - [命令行](#命令行)
    - [列出内置的爬虫](#列出内置的爬虫)
    - [运行一个爬虫](#运行一个爬虫)
    - [分析爬取的数据](#分析爬取的数据)
    - [通过bvid下载视频](#通过bvid下载视频)
    - [多线程下载视频](#多线程下载视频)
    - [指定SESS\_DATA下载高清视频](#指定sess_data下载高清视频)
    - [爬取某作者的主页视频](#爬取某作者的主页视频)
    - [查看帮助](#查看帮助)
  - [代码](#代码)
    - [运行爬虫](#运行爬虫)
    - [分析爬取的数据](#分析爬取的数据-1)
    - [通过bvid下载视频](#通过bvid下载视频-1)
- [内置爬虫](#内置爬虫)

## 安装

```sh
pip install spiders-for-all # python 版本 >= 3.12
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

*注意: 在下载视频前, 你需要确保你的主机上已安装了`ffmpeg`, 并确保可以直接命令行调用, 如果是使用docker方式启动, 则可以忽略这一步*


```sh
python -m spiders_for_all download-video -b BV1hx411w7MG -s ./videos_dl
```

#### 多线程下载视频

*传入多个bvid:*
```sh
python -m spiders_for_all download-videos -b "BVID1 BVID2" -s ./videos_dl
```

*或传入一个包含bvid列表的文件, 回车换行:*


`bvid_list.txt`: 
```txt
BVID1
BVID2
...
```

```sh
python -m spiders_for_all download-videos -b bvid_list.txt -s ./videos_dl
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

#### 爬取某作者的主页视频

*注意: 

- bilibili对主页数据爬取有风控策略, 一次不建议爬取太多视频, 会触发风控
- 实际测试大概在**200-300条视频**左右时就会**触发风控**, 因此如果超过这个数量, 建议按照以下步骤分两步爬取

1. 收集主页视频bvid信息

```sh
python -m spiders_for_all run-spider -n author -p mid {mid} -p total {total} -p sess_data {SESS_DATA} -p page_size {page_size} -p page_number {page_number}
```

**参数说明(打勾的是必传参数):**

- [x] `mid`: 作者的mid 
- [ ] `total`: 要爬取的数量, 会取min(作者主页视频总数, 传入的total), 建议一次<200, 不传会使用作者视频总数
- [ ] `sess_data`: 传入SESS_DATA可能一定程度上降低风控策略的触发, 但是不保证一定不会触发(待更有说服力的测试验证)
- [ ] `page_number`: 从第几页开始爬取, 默认为1, 分批次爬取时修改该参数
- [ ] `page_size`: 每页的爬取数量
- [ ] `-s`: 爬取bvid后直接下载, 数量多时不建议添加该参数, 会触发风控, 先收集完所有需要下载的bvid再按照第2步进行下载
- [ ] `-d`: 指定后从数据库查询当前爬虫存储的bvid下载视频, 不进行爬取操作

1. 下载视频(后续会优化这个步骤)

```sh
python -m spiders_for_all download-by-author -m {mid} -s {save_dir} -d {sess_data}
```

**分批次爬取完整示例:**


```sh
# 爬取主页视频bvid, 一次爬取30 * 7 = 210条
python -m spiders_for_all run-spider -n author -p mid 作者的mid -p total 210 -p page_size 30 -p page_number 1

python -m spiders_for_all run-spider -n author -p mid 作者的mid -p total 210 -p page_size 30 -p page_number 8

python -m spiders_for_all run-spider -n author -p mid 作者的mid -p total 210 -p page_size 30 -p page_number 16

...

# 爬取完bvid后再下载视频
python -m spiders_for_all download-by-author -m {mid} -s {save_dir} -d {sess_data}
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
    with downloader:
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
