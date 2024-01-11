<p align="center">
<img src="docs/logo.png" height="200px"/>
</p>

> 爬取、下载哔哩哔哩、小红书等网站数据、视频, 持续更新中...

> **Warning:**
> 
> 本项目仅供学习交流使用, 请勿用于商业及非法用途, 由此引起的一切后果与作者无关


# Menu

- [Menu](#menu)
- [Quick Preview](#quick-preview)
- [Installation](#installation)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Known Issues](#known-issues)

# Quick Preview 

**根据用户id爬取b站用户主页投稿视频**

```sh
python -m spiders_for_all bilibili download-by-author -m 用户id -s 保存目录
```

**根据note_id批量爬取小红书笔记内容**

```sh
python -m spiders_for_all xhs download -i note_id1,note_id2,note_id3 -s 保存目录
```

**更多用法见[Documentation](#documentation)部份**

# Installation

```sh
pip install spiders-for-all # python 版本 >= 3.12
```

# Documentation

**点击进入对应平台的使用文档**

- [哔哩哔哩](./spiders_for_all/spiders/bilibili/README.md)

- [小红书](./spiders_for_all/spiders/xhs/README.md)

# Roadmap

- bilibili
  - [x] 综合热门、入站必刷等栏目爬虫
  - [x] 根据bvid爬取/批量爬取视频
  - [x] 根据用户id爬取用户主页投稿视频
  - [ ] 爬取用户动态
- xhs
  - [x] 根据note_id爬取/批量爬取笔记
  - [x] 根据用户id爬取用户主页首页笔记
  - [ ] 爬取笔记评论
- [ ] GUI

# Known Issues

- [ ] 小红书爬取用户投稿的笔记时, 由于小红书签名算法的问题尚未解决, 只能爬取用户投稿的首页数据, 需要下拉加载的数据暂时无法爬取
- [ ] 低版本的sqlite可能不支持`ON CONFLICT DO UPDATE`语法, 如果遇到该问题请尝试升级sqlite版本 