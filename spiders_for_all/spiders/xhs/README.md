# 目录

- [目录](#目录)
- [Features](#features)
- [前言](#前言)
- [通过note\_id下载笔记内容](#通过note_id下载笔记内容)
- [批量下载笔记](#批量下载笔记)
  - [1. 多个note\_id直接传入命令行, 逗号分隔](#1-多个note_id直接传入命令行-逗号分隔)
  - [2. 传入一个包含note\_id列表的文件, 回车换行](#2-传入一个包含note_id列表的文件-回车换行)
- [爬取用户投稿的笔记](#爬取用户投稿的笔记)
- [根据SQL下载笔记](#根据sql下载笔记)
- [爬取笔记评论](#爬取笔记评论)
- [Configuration](#configuration)

# Features

- [x] 根据note_id下载笔记内容以及笔记内的图片、视频数据
- [x] 批量下载笔记
- [x] 爬取用户投稿的笔记
- [x] 爬取笔记评论


# 前言

命令行使用时, 基本的使用格式为:

`python -m spiders_for_all {platform} {sub_commands}`

其中`platform`为对应的平台, `sub_commands`为该平台目前可用的子命令

你可以通过`--help`参数查看详细的参数说明, 示例:

`python -m spiders_for_all --help`

`python -m spiders_for_all xhs --help`

`python -m spiders_for_all xhs download-by-id --help`

# 通过note_id下载笔记内容

```sh
python -m spiders_for_all xhs download-by-id -i 6577d19b000000003a00e0a8 -s /tmp/xhs_download
```

# 批量下载笔记

你可以通过多种方式来进行批量下载:

## 1. 多个note_id直接传入命令行, 逗号分隔

```sh
python -m spiders_for_all xhs download-by-id -i 6577d19b000000003a00e0a8,65964537000000001101c0ce -s /tmp/xhs_download
```

## 2. 传入一个包含note_id列表的文件, 回车换行

```sh
python -m spiders_for_all xhs download-by-id -i note_id_list.txt -s /tmp/xhs_download
```


# 爬取用户投稿的笔记


```sh
python -m spiders_for_all xhs download-by-author 5d9756b20000000001005857 \
    -s /tmp/xhs_spider_author 
```

>*注意*:
> 该命令仅会保存并下载本次爬取的笔记, 爬取的笔记信息(title, note_id等)会保存到本地数据库`.db/xhs.db`的`t_xhs_author_notes`表中, 这也就意味着如果你使用该命令分别爬取了不同的用户投稿笔记, 本地数据库将存储全部这些数据。如果你需要一次性下载多个用户的投稿笔记, 可以通过`download-by-sql`这个命令来指定你要下载哪些笔记[根据SQL下载笔记](#根据sql下载笔记)。

**NOTE: 该接口需要提前在本地配置好`nodejs`环境, 同时安装依赖包: `npm install jsdom`**


# 根据SQL下载笔记

**本地数据库正常情况下位于`./.db/xhs.db`**

```sh
python -m spiders_for_all xhs download-by-sql "select note_id from t_xhs_author_notes limit 5" -s /tmp/xhs_download_by_sql
```

# 爬取笔记评论

```sh
python -m spiders_for_all xhs get-comments 653619a2000000000d006d1a
```


# Configuration


你可以通过在当前目录创建`.env`来控制爬虫的一些行为, 针对`xhs`目前可用的配置为:

|配置名称|类型|描述|默认值|示例|
|---|---|---|---|---|
|XHS_HEADERS|json|全局请求头, 每次调用都会携带, 可以通过`self.client.headers.update`覆盖|None|XHS_HEADERS={"Referer":"referer"}|
|XHS_COOKIES|str|全局cookie, 每次调用都会携带, 可以通过`self.client.set_cookies`覆盖|None|XHS_COOKIES="key=value;key2=value2"|
|XHS_SIGN_JS_FILE|str|用来签名的js文件,默认使用仓库中的js文件`spiders_for_all/static/xhs.js`, 需要自行实现一个`get_xs`方法|XHS_SIGN_JS_FILE=/path/to/your/js|


同时, 还有一些配置为全局配置:

|配置名称|类型|描述|默认值|示例|
|---|---|---|---|---|
|DEBUG|bool|开启后将打印更详细的日志信息|false|DEBUG=true|
|LOG_LEVEL|str|日志级别, 可选值为: 10/20/30/40/50|DEBUG开启的情况下默认是10, 否则默认20|LOG_LEVEL=30|
|REQUEST_MAX_RETRIES|int|请求失败后最大重试次数|10|REQUEST_MAX_RETRIES=20|
|REQUEST_RETRY_INTERVAL|int|请求失败后重试间隔, 单位: 秒|30|REQUEST_RETRY_INTERVAL=45|
|REQUEST_RETRY_STEP|int|请求失败后重试间隔递增步长, 单位: 秒, 设置0将以固定的REQUEST_RETRY_INTERVAL进行重试|10|REQUEST_RETRY_STEP=5|
|HTTP_PROXIES|json|代理配置, 格式为json, 详细配置见[requests文档](https://docs.python-requests.org/en/latest/user/advanced/#proxies)|None|HTTP_PROXIES={"http":"http://your_proxy.com"}|

