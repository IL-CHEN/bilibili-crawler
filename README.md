# B 站评论爬虫与数据看板

一个完整的 B 站评论采集与分析项目：**关键词搜索 → 提取 BV 号 → 爬取评论 → 存入 MongoDB → Web 可视化看板**。

前端基于 Flask + ECharts，采用「接口抽象 + 模板方法」的爬虫骨架设计，存储层可灵活替换（文件 / MongoDB）。

## 功能特性

- **关键词采集**：搜索关键词 → 批量提取视频 BV 号（支持翻页）
- **评论爬取**：主评论 + 楼中楼子评论，自动分页、随机延时降低风控
- **双存储后端**：MongoDB（推荐，支持去重 upsert）/ CSV 文件
- **可视化看板**（ECharts）：
  - 总览指标卡：总评论数 / 覆盖视频 / 活跃用户 / 国内 / 海外 / 国内占比
  - 国内评论地区分布 TOP15、国内 vs 海外占比
  - 近 30 天评论趋势（新爬取数据自动带时间字段）
  - 活跃用户 TOP10、评论最多视频 TOP10、评论高频词云
  - 评论明细表格：内容关键词 / 地区 / 视频 / 排序多条件筛选 + 分页
- **配置化**：全部配置走 `.env` 环境变量，敏感信息（B 站 Cookie）不落代码
- **单元测试**：`unittest`，覆盖清洗、提取、分析等纯函数

## 技术栈


| 模块 | 技术                                                |
| ---- | --------------------------------------------------- |
| 爬虫 | Python 3.10+ · requests · 接口抽象 + 模板方法模式 |
| 存储 | MongoDB（pymongo）· pandas（CSV 输出）             |
| 后端 | Flask · pandas · jieba（中文分词）                |
| 前端 | ECharts 5 · echarts-wordcloud · 原生 HTML/CSS/JS  |

## 目录结构

```
bilibili_crawler/
├── app.py                 # Flask 应用入口（看板页面 + REST API）
├── analytics.py           # 数据分析模块（统计 / 查询 / 词频，与视图解耦）
├── config.py              # 全局配置（.env 驱动，含安全提示）
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量模板（复制为 .env 使用）
├── .gitignore
├── LICENSE                # MIT 许可
├── README.md
├── baidu_stopwords.txt    # 词频统计停用词表
├── templates/
│   └── index.html         # 数据看板页面
├── bilibili/              # 爬虫核心包
│   ├── interfaces.py      # 抽象接口（Fetcher / Extractor / Parser / Cleaner / Repository）
│   ├── session.py         # 请求会话（单例，统一 headers）
│   ├── fetchers.py        # HTML / API 抓取实现
│   ├── extractors.py      # BV 号提取
│   ├── parsers.py         # 评论报文解析（主评论 / 子评论）
│   ├── cleaners.py        # 评论清洗
│   ├── repositories.py    # 存储实现（文件 / MongoDB）
│   ├── crawlers.py        # 爬虫骨架（模板方法）+ 具体实现
│   └── main.py            # 命令行入口
└── tests/                 # 单元测试（unittest）
```

## 快速开始

### 1. 环境准备

- Python 3.10+
- MongoDB（本地默认 `localhost:27017`，或用 Docker 启动）

```bash
# 拉取依赖
pip install -r requirements.txt

# 生成环境变量文件并编辑（填入 B 站 Cookie 等）
cp .env.example .env        # Windows: copy .env.example .env
```

> **Cookie 说明**：B 站部分接口需要登录态。在浏览器登录 bilibili.com 后，按 `F12 → 网络 → 任意接口请求头` 复制完整 `Cookie` 串，填入 `.env` 的 `BILI_COOKIE`。Cookie 属敏感信息，请勿提交到 Git（`.env` 已在 `.gitignore` 中忽略）。

### 2. 启动爬虫（采集数据）

```bash
# 爬取关键词「Python 教程」搜索结果前 1-5 页对应视频的评论，入库 MongoDB
python -m bilibili.main --keyword "Python 教程" --start 1 --end 5
```

### 3. 启动数据看板

```bash
python app.py
# 浏览器访问 http://localhost:5000
```

## API 文档


| 接口            | 方法 | 说明                                     | 主要参数                                                                                              |
| --------------- | ---- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `/`             | GET  | 看板页面                                 | -                                                                                                     |
| `/api/health`   | GET  | MongoDB 健康检查                         | -                                                                                                     |
| `/api/stats`    | GET  | 全局统计数据（地域/占比/排行/词云/趋势） | -                                                                                                     |
| `/api/comments` | GET  | 评论分页查询                             | `page` `page_size` `bv` `keyword` `user` `region`（`国内`/`海外`/具体地区）`sort`（`time`/`default`） |
| `/api/bvs`      | GET  | 视频评论数排行（供筛选下拉框）           | -                                                                                                     |

统一响应结构：`{"ok": true, "data": ...}`；出错时 `{"ok": false, "error": "..."}`。

## 数据字段

评论文档字段：


| 字段        | 说明                                  |
| ----------- | ------------------------------------- |
| `rp_id`     | 评论 ID                               |
| `user_id`   | 用户 ID                               |
| `user_name` | 用户昵称                              |
| `content`   | 评论文本（已清洗）                    |
| `ip`        | 评论归属地（如`上海` / `海外`）       |
| `bv`        | 视频 BV 号                            |
| `video_url` | 视频链接                              |
| `c_time`    | 评论发布时间（Unix 秒，新爬数据才有） |
| `crawl_at`  | 抓取入库时间（新爬数据才有）          |

## 运行测试

```bash
python -m unittest discover -s tests -v
```

## 免责声明

本项目仅供**学习与研究**使用，数据来源于 B 站公开接口。请遵守：

- [哔哩哔哩用户协议]([用户使用协议](https://www.bilibili.com/blackboard/era/I1IzQXW4myXZIzBi.html)) 与相关法律法规；
- 控制请求频率（本项目已内置随机延时），避免对目标服务造成压力；
- 不得将采集数据用于任何商业用途或二次分发。

因使用本项目产生的任何问题，本项目作者不承担相关责任。

## License

[MIT](./LICENSE) © 2026 IL-CHEN
