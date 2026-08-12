# chatgpt-tarot-divination → N.E.K.O Tarot 插件集成计划

## 项目概述

将 `chatgpt-tarot-divination` 项目（一个基于 ChatGPT 的 AI 算命/占卜应用）的核心功能和 UI 设计集成到 N.E.K.O 塔罗牌插件中。

## 源项目分析总结

### 核心功能（7种占卜类型）

| 类型 | Key | 前端页面 | Prompt 核心 |
|---|---|---|---|
| 塔罗牌 | `tarot` | TarotPage.tsx | "我请求你担任塔罗占卜师的角色。您将接受我的问题并使用虚拟塔罗牌进行塔罗牌阅读。不要忘记洗牌并介绍您在本套牌中使用的套牌。请帮我抽3张随机卡。拿到卡片后，请您仔细说明它们的意义，解释哪张卡片属于未来或现在或过去，结合我的问题来解释它们，并给我有用的建议或我现在应该做的事情。" |
| 生辰八字 | `birthday` | BirthdayPage.tsx | "我请求你担任中国传统的生辰八字算命的角色。我将会给你我的生日，请你根据我的生日推算命盘，分析五行属性、吉凶祸福、财运、婚姻、健康、事业等方面的情况，并为其提供相应的指导和建议。" |
| 姓名五格 | `name` | NamePage.tsx | "我请求你担任中国传统的姓名五格算命师的角色。我将会给你我的名字，请你根据我的名字推算，分析姓氏格、名字格、和自己格。并为其提供相应的指导和建议。" |
| 周公解梦 | `dream` | DreamPage.tsx | "我请求你担任中国传统的周公解梦师的角色。我将会给你我的梦境，请你解释我的梦境，并为其提供相应的指导和建议。" |
| 起名取名 | `new_name` | NewNamePage.tsx | "我请求你担任起名师的角色，我将会给你我的姓氏、生日、性别等，请返回你认为最适合我的名字，请注意姓氏在前，名字在后。" |
| 梅花易数 | `plum_flower` | PlumFlowerPage.tsx | "我请求你担任中国传统的梅花易数占卜师的角色。我会随意说出两个数，第一个数取为上卦，第二个数取为下卦。请你直接以数起卦, 并向解释结果" |
| 姻缘占卜 | `fate` | FatePage.tsx | "你是一个姻缘助手，我给你发两个人的名字，用逗号隔开，你来随机说一下，这两个人之间的缘分如何？不需要很真实，只需要娱乐化的说一下即可..." |

### 前端技术栈与设计模式

- **React + Vite + Tailwind CSS**
- **组件结构**:
  - `DivinationCardHeader` - 统一的卡片头部组件（标题、描述、图标）
  - `ResultDrawer` - 结果展示抽屉（Markdown 渲染）
  - `MainLayout` - 响应式主布局（移动端适配）
- **自定义 Hook**: `useDivination` - 流式输出 + 历史记录 + Markdown 渲染
- **图标库**: `lucide-react` (Sparkles, Heart, Calendar, Baby, User, Moon, Flower2)
- **特色功能**:
  - 🌊 **流式输出** - AI 占卜结果以打字机效果实时呈现
  - 📚 **历史记录** - 每种占卜类型自动保存最近 10 条记录
  - 📱 **响应式设计** - 完美适配手机、平板、电脑
  -  **暗色模式** - 支持明暗主题切换

### 后端技术栈与 API 设计

- **FastAPI + OpenAI Streaming**
- **核心架构**: `DivinationFactory` 工厂模式
- **API 端点**: `POST /api/divination`
  - 输入: `DivinationBody` (prompt, prompt_type, birthday, etc.)
  - 输出: Server-Sent Events (SSE) 流式响应
- **速率限制**: 未登录 10/min，已登录 600/hour
- **安全**: STOP_WORDS 过滤（防止 prompt 注入）

## 集成策略

### 阶段 1: 塔罗牌核心功能（当前优先级最高）

#### 1.1 后端 Prompt 优化
- **目标**: 使用源项目的 `TAROT_PROMPT` 替代现有的硬编码牌义
- **方法**: 
  - 保留现有的塔罗牌数据（22张大阿卡纳）
  - 集成 `TAROT_PROMPT` 到猫娘通知消息中
  - 让猫娘用更专业的语言解读塔罗牌结果

#### 1.2 前端 UI 重构
- **目标**: 参考源项目的 React 组件设计，用原生 HTML/CSS/JS 实现
- **方法**:
  - `DivinationCardHeader` → 卡片头部组件（标题、描述、图标）
  - `ResultDrawer` → 结果展示抽屉（Markdown 渲染效果）
  - `useDivination` → 占卜逻辑（流式输出效果模拟）
  - 使用 Tailwind CSS 风格的原生 CSS
  - 使用 SVG/emoji 替代 lucide-react 图标

#### 1.3 流式输出效果
- **目标**: 模拟源项目的打字机效果
- **方法**: 使用 JavaScript 逐字显示占卜结果

#### 1.4 历史记录
- **目标**: 每种占卜类型保存最近 10 条记录
- **方法**: 使用 localStorage 存储历史记录

### 阶段 2: 扩展其他占卜类型
逐步集成生辰八字、姓名五格、周公解梦、起名取名、梅花易数、姻缘占卜

## 关键技术决策

### 1. Prompt 设计
源项目的 `TAROT_PROMPT`:
```
"我请求你担任塔罗占卜师的角色。您将接受我的问题并使用虚拟塔罗牌进行塔罗牌阅读。"
"不要忘记洗牌并介绍您在本套牌中使用的套牌。请帮我抽3张随机卡。"
"拿到卡片后，请您仔细说明它们的意义，解释哪张卡片属于未来或现在或过去，"
"结合我的问题来解释它们，并给我有用的建议或我现在应该做的事情。"
```

这个 Prompt 可以直接用在猫娘通知消息中，让猫娘用更专业的语言解读。

### 2. 前端 UI 设计
- **不使用 React**（N.E.K.O 插件是静态文件服务）
- **使用原生 HTML/CSS/JS** 实现类似效果
- **Tailwind CSS 风格**：参考源项目的样式设计
- **图标替代**：使用 SVG/emoji 替代 lucide-react
- **保持风格**：塔罗牌的神秘浪漫风格（粉、蓝、白、橙等明亮色调）

### 3. 与 N.E.K.O 架构的适配
- **后端**: 集成到 `tarot/__init__.py`
- **前端**: 集成到 `tarot/static/index.html`
- **保持**: `@plugin_entry` 装饰器模式
- **猫娘通知**: 档2（`ai_behavior="respond"`）

### 4. 消息推送格式
```python
self.ctx.push_message(
    source="tarot_reader",
    ai_behavior="respond",  # 档2：猫娘会回应给用户听
    parts=[{"type": "text", "text": message}],
    priority=5,
)
```

## 实施步骤

1. ✅ 克隆源项目到本地
2. ✅ 分析源项目架构
3. ⏳ 重写塔罗牌后端逻辑（集成 TAROT_PROMPT + 优化猫娘通知）
4. ⏳ 重写前端 UI（参考源项目 DivinationCardHeader + ResultDrawer 设计）
5. ⏳ 实现流式输出效果
6. ⏳ 实现历史记录功能
7.  测试和验证
8. ⏳ 逐步集成其他占卜类型

## 注意事项

- 源项目使用 MIT License，可以免费使用和修改
- 需要适配 N.E.K.O 插件架构，不能直接照搬代码
- 保持塔罗牌的神秘浪漫风格（粉、蓝、白、橙等明亮色调）
- 猫娘通知要使用档2（给猫娘发，猫娘回应）
- 前端不使用 React，用原生 HTML/CSS/JS 实现类似效果
- 保留现有的塔罗牌数据（22张大阿卡纳），只优化 Prompt 和 UI
