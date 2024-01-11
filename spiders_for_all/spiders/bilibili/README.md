
# 目录

- [目录](#目录)
- [Features](#features)
- [前言](#前言)
- [通过bvid下载视频](#通过bvid下载视频)
- [批量下载视频](#批量下载视频)
  - [1. 多个bvid直接传入命令行, 逗号分隔](#1-多个bvid直接传入命令行-逗号分隔)
  - [2. 传入一个包含bvid列表的文件, 回车换行](#2-传入一个包含bvid列表的文件-回车换行)
- [爬取用户投稿视频](#爬取用户投稿视频)
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

`python -m spiders_for_all bilibili download-video --help`

# 通过bvid下载视频

```sh
python -m spiders_for_all bilibili download-video -b BV1BK411L7DJ -s /tmp/bilibili_download_video
```

# 批量下载视频

你可以通过多种方式来进行批量下载:

## 1. 多个bvid直接传入命令行, 逗号分隔

```sh
python -m spiders_for_all bilibili download-videos -b BV1BK411L7DJ,BV1ph4y1g75E -s /tmp/bilibili_download_videos
```

## 2. 传入一个包含bvid列表的文件, 回车换行

```sh
python -m spiders_for_all bilibili download-videos -b bvid_list.txt -s /tmp/bilibili_download_videos
```

详细参数可以通过`python -m spiders_for_all bilibili download-videos --help`查看

# 爬取用户投稿视频

```sh
python -m spiders_for_all bilibili download-by-author -m 483879799 -s /tmp/bilibili_download_by_author -t 1
```

参数说明:

- `-m`: 用户的mid
- `-s`: 保存目录
- `-t`: 爬取的数目, 不指定将爬取全部投稿视频

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

