# 目录

- [目录](#目录)
- [Features](#features)
- [前言](#前言)
- [通过note\_id下载笔记内容](#通过note_id下载笔记内容)
- [批量下载笔记](#批量下载笔记)
  - [1. 多个note\_id直接传入命令行, 逗号分隔](#1-多个note_id直接传入命令行-逗号分隔)
  - [2. 传入一个包含note\_id列表的文件, 回车换行](#2-传入一个包含note_id列表的文件-回车换行)
- [爬取用户投稿的笔记](#爬取用户投稿的笔记)
- [Configuration](#configuration)

# Features

- [x] 根据note_id下载笔记内容以及笔记内的图片、视频数据
- [x] 批量下载笔记
- [x] 爬取用户投稿的笔记(**目前由于小红书签名算法的问题, 只能爬取用户投稿的首页数据, 需要下拉加载的数据暂时无法爬取**)


# 前言

命令行使用时, 基本的使用格式为:

`python -m spiders_for_all {platform} {sub_commands}`

其中`platform`为对应的平台, `sub_commands`为该平台目前可用的子命令

你可以通过`--help`参数查看详细的参数说明, 示例:

`python -m spiders_for_all --help`

`python -m spiders_for_all xhs --help`

`python -m spiders_for_all xhs download --help`

# 通过note_id下载笔记内容

```sh
python -m spiders_for_all xhs download -i 6577d19b000000003a00e0a8 -s /tmp/xhs_download
```

# 批量下载笔记

你可以通过多种方式来进行批量下载:

## 1. 多个note_id直接传入命令行, 逗号分隔

```sh
python -m spiders_for_all xhs download -i 6577d19b000000003a00e0a8,65964537000000001101c0ce -s /tmp/xhs_download
```

## 2. 传入一个包含note_id列表的文件, 回车换行

```sh
python -m spiders_for_all xhs download -i note_id_list.txt -s /tmp/xhs_download
```


# 爬取用户投稿的笔记

```sh
python -m spiders_for_all xhs spider-author 5d9756b20000000001005857 \
    -s /tmp/xhs_spider_author \
    -w "author_id='5d9756b20000000001005857'"
```

*需要注意的是`spider-author`是通用命令, 本地数据库会保存多个作者的笔记数据, 如果你想通过这个命令下载某作者笔记, 请按照示例添加`-w`参数来过滤作者笔记，否则会下载本地数据库存储的所有笔记数据*

**NOTE: 目前该接口由于小红书的签名算法问题, 只能爬取到用户首页投稿数据, 如果有分页数据则无法爬取。当然如果你有现成的途径可以解决这个问题，也可以通过修改`spiders_for_all/spiders/xhs.py`内的`XhsAuthorSpider`来解决这个问题。`XhsAuthorSpider`已实现了分页逻辑, 只需要在以下部份添加你已实现的签名算法即可:**

`spiders_for_all/spiders/xhs.py`:

```python
class XhsAuthorSpider(BaseXhsSpider, RateLimitMixin):
    ...

    def get_items_from_response(
        self,
        response: requests.Response,  # type: ignore
    ) -> t.Iterable[models.XhsUserPostedNote]:
        ...
        if next_query is None:
            ...
        else:
            
            # 注释掉这里return的代码
            # self.warning(
            #     "For now, we can only get the first page of notes due to the lack of x-s algorithm."
            # )

            # return (
            #     models.XhsAuthorPageNote(**note).note_item
            #     for note in chain.from_iterable(notes)
            # )

            ...
    
    
    def iter_notes_by_cursor(
        self, query: models.XhsNoteQuery, formats: str | None = None
    ) -> t.Generator[models.XhsUserPostedNote, None, None]:

        ...

        while query.cursor:
            
            # 你已实现的签名算法
            headers = your_headers_implementation()
            cookies = your_cookies_implementation()

            self.client.headers.update(headers)
            self.client.cookies.update(cookies)

            ...

```


# Configuration


你可以通过在当前目录创建`.env`来控制爬虫的一些行为, 针对`xhs`目前可用的配置为:

|配置名称|类型|描述|默认值|示例|
|---|---|---|---|---|
|XHS_HEADERS|json|全局请求头, 每次调用都会携带, 可以通过`self.client.headers.update`覆盖|None|XHS_HEADERS={"Referer":"referer"}|
|XHS_COOKIES|json|全局cookie, 每次调用都会携带, 可以通过`self.client.cookies.update`覆盖|None|XHS_COOKIES={"cookie_name":"cookie_value"}|


同时, 还有一些配置为全局配置:

|配置名称|类型|描述|默认值|示例|
|---|---|---|---|---|
|DEBUG|bool|开启后将打印更详细的日志信息|false|DEBUG=true|
|LOG_LEVEL|str|日志级别, 可选值为: 10/20/30/40/50|DEBUG开启的情况下默认是10, 否则默认20|LOG_LEVEL=30|
|REQUEST_MAX_RETRIES|int|请求失败后最大重试次数|10|REQUEST_MAX_RETRIES=20|
|REQUEST_RETRY_INTERVAL|int|请求失败后重试间隔, 单位: 秒|30|REQUEST_RETRY_INTERVAL=45|
|REQUEST_RETRY_STEP|int|请求失败后重试间隔递增步长, 单位: 秒, 设置0将以固定的REQUEST_RETRY_INTERVAL进行重试|10|REQUEST_RETRY_STEP=5|
|HTTP_PROXIES|json|代理配置, 格式为json, 详细配置见[requests文档](https://docs.python-requests.org/en/latest/user/advanced/#proxies)|None|HTTP_PROXIES={"http":"http://your_proxy.com"}|
