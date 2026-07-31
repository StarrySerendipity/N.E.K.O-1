# Web Searching

> 独立开发的联网搜索插件 — 让猫娘可以搜索世界上的一切。

## 与 upstream `web_search` 的区别

| 维度 | upstream `web_search` | 本插件 `web_searching` |
|------|----------------------|----------------------|
| 搜索策略 | 仅 HTML 抓取（百度/DDG） | 多策略：API + 百科 + 抓取 |
| DDG Instant Answer API | 无 | 有（结构化 JSON） |
| Wikipedia API | 无 | 有（知识增强） |
| Bing fallback | 无 | 有 |
| `@llm_tool` 注册 | 无 | 有 |
| 搜索历史 | 无 | SQLite 持久化 |
| 前端 UI | 无 | 白蓝粉渐变 + 樱花动画 |

## 搜索策略（分层 fallback）

```
用户查询
  │
  ├── 1. DuckDuckGo Instant Answer API（JSON，无抓取）
  │      返回：摘要、定义、相关主题
  │
  ├── 2. Wikipedia API（百科知识增强）
  │      返回：百科摘要（中英文）
  │
  ├── 3. DuckDuckGo HTML 抓取（web 结果）
  │      返回：网页标题、摘要、链接
  │
  └── 4. Bing HTML 抓取（最终 fallback）
         返回：网页标题、摘要、链接
```

步骤 1-2 并行执行（知识层），步骤 3-4 串行 fallback（web 结果层）。

## 插件入口

| Entry | 说明 |
|-------|------|
| `web_search` (LLM Tool) | 猫娘自动调用 |
| `search` | 手动搜索 |
| `get_history` | 获取搜索记录 |
| `clear_history` | 清空记录 |
| `get_stats` | 搜索统计 |
| `get_status` | 插件状态 |

## 前端 UI

访问路径：`/plugin/web_searching/ui/`

- 白蓝粉渐变配色，诗意浪漫风格
- 樱花飘落背景动画
- 搜索结果分区显示：即时答案 / 百科知识 / 网页结果
