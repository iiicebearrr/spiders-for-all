
# 目录

- [目录](#目录)
- [Features](#features)
- [前言](#前言)
- [通过bvid下载视频](#通过bvid下载视频)
- [批量下载视频](#批量下载视频)
  - [1. 多个bvid直接传入命令行, 逗号分隔](#1-多个bvid直接传入命令行-逗号分隔)
  - [2. 传入一个包含bvid列表的文件, 回车换行](#2-传入一个包含bvid列表的文件-回车换行)
- [爬取用户投稿视频](#爬取用户投稿视频)
- [根据SQL下载视频](#根据sql下载视频)
- [列出内置的爬虫](#列出内置的爬虫)
- [运行内置爬虫](#运行内置爬虫)
- [Configuration](#configuration)

# Features

- [x] 根据bvid下载视频
- [x] 批量下载视频
- [x] 爬取用户投稿视频(可全部爬取)
- [x] 内置部份分栏爬虫

# 前言

命令行使用时, 基本的使用格式为:

`python -m spiders_for_all {platform} {sub_commands}`

其中`platform`为对应的平台, `sub_commands`为该平台目前可用的子命令

你可以通过`--help`参数查看详细的参数说明, 示例:

`python -m spiders_for_all --help`

`python -m spiders_for_all bilibili --help`

`python -m spiders_for_all bilibili download-by-id --help`

# 通过bvid下载视频

```sh
python -m spiders_for_all bilibili download-by-id -b BV1BK411L7DJ -s /tmp/bilibili_download_video
```

# 批量下载视频

你可以通过多种方式来进行批量下载:

## 1. 多个bvid直接传入命令行, 逗号分隔

```sh
python -m spiders_for_all bilibili download-by-ids -b BV1BK411L7DJ,BV1ph4y1g75E -s /tmp/bilibili_download_videos
```

## 2. 传入一个包含bvid列表的文件, 回车换行

```sh
python -m spiders_for_all bilibili download-by-ids -b bvid_list.txt -s /tmp/bilibili_download_videos
```

详细参数可以通过`python -m spiders_for_all bilibili download-by-ids --help`查看

# 爬取用户投稿视频

```sh
python -m spiders_for_all bilibili download-by-author -m 483879799 -s /tmp/bilibili_download_by_author -t 1
```

参数说明:

- `-m`: 用户的mid
- `-s`: 保存目录
- `-t`: 爬取的数目, 不指定将爬取全部投稿视频

>*注意*:
> 该命令仅会保存并下载本次爬取的视频, 爬取的视频信息(title, bvid等)会保存到本地数据库`.db/bilibili.db`的`t_bilibili_author_video`表中, 这也就意味着如果你使用该命令分别爬取了不同的用户投稿视频, 本地数据库将存储全部这些数据。如果你需要一次性下载多个用户的投稿视频, 可以通过`download-by-sql`这个命令来指定你要下载哪些视频, 详见[根据SQL下载视频](#根据sql下载视频), 同时`run-spider author`也提供了对应的途径, 详见[运行示例](../../../example/bilibili/example_run_spider.sh)中最后关于`author`的部份


# 根据SQL下载视频

**正常情况下本地的数据库文件位于`./.db/bilibili.db`**

```sh
python -m spiders_for_all bilibili download-by-sql "select bvid from t_bilibili_author_video limit 5" -s /tmp/bilibili_download_by_sql
```

# 列出内置的爬虫

```sh
python -m spiders_for_all bilibili list
```

# 运行内置爬虫

```sh
python -m spiders_for_all bilibili run-spider {name/alias}
```

**示例: 运行popular(综合热门)爬虫, 爬取最新100条视频数据**

```sh
python -m spiders_for_all bilibili run-spider popular -p total 100
```


**示例: 爬取综合热门前10条视频, 指定`-s`或`--save-dir`在爬取结束后下载视频**

> **注意, 不推荐在爬虫结束后立即下载视频, 因为`run-spider`是一个通用命令，每次执行都会将数据保存在本地, 因此如果直接通过`-s`指定下载目录进行下载, 可能会下载到历史数据, 建议使用`download-by-sql`或增加`-w`参数来指定要下载的视频**

```sh
python -m spiders_for_all bilibili run-spider popular -p total 10 -s /tmp
```

**完整示例见** [所有内置爬虫用法示例](../../../example/bilibili/example_run_spider.sh)

# Configuration

你可以通过在当前目录创建`.env`来控制爬虫的一些行为, 针对`bilibili`目前可用的配置为:

|配置名称|类型|描述|默认值|示例|
|---|---|---|---|---|
|BILIBILI_DM_IMG_STR|str|部份接口需要该参数作为签名|V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ|BILIBILI_DM_IMG_STR="DM IMG STR"|
|BILIBILI_DM_COVER_IMG_STR|str|部份接口需要该参数作为签名|QU5HTEUgKEludGVsIEluYy4sIEludGVsKFIpIElyaXMoVE0pIFBsdXMgR3JhcGhpY3MgNjU1LCBPcGVuR0wgNC4xKUdvb2dsZSBJbmMuIChJbnRlbCBJbmMuKQ|BILIBILI_DM_COVER_IMG_STR="DM COVER IMG STR"|
|BILIBILI_SESS_DATA|str|cookie: `SESSDATA`, 指定后可以下载更高清晰度的视频|None|BILIBILI_SESS_DATA="YOUR SESS DATA"|


同时, 还有一些配置为全局配置:

|配置名称|类型|描述|默认值|示例|
|---|---|---|---|---|
|DEBUG|bool|开启后将打印更详细的日志信息|false|DEBUG=true|
|LOG_LEVEL|str|日志级别, 可选值为: 10/20/30/40/50|DEBUG开启的情况下默认是10, 否则默认20|LOG_LEVEL=30|
|REQUEST_MAX_RETRIES|int|请求失败后最大重试次数|10|REQUEST_MAX_RETRIES=20|
|REQUEST_RETRY_INTERVAL|int|请求失败后重试间隔, 单位: 秒|30|REQUEST_RETRY_INTERVAL=45|
|REQUEST_RETRY_STEP|int|请求失败后重试间隔递增步长, 单位: 秒, 设置0将以固定的REQUEST_RETRY_INTERVAL进行重试|10|REQUEST_RETRY_STEP=5|
|HTTP_PROXIES|json|代理配置, 格式为json, 详细配置见[requests文档](https://docs.python-requests.org/en/latest/user/advanced/#proxies)|None|HTTP_PROXIES={"http":"http://your_proxy.com"}|

