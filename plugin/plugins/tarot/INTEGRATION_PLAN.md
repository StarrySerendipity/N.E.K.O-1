# chatgpt-tarot-divination → N.E.K.O Tarot 插件集成计划

## 项目概述

将 `chatgpt-tarot-divination` 项目（一个基于 ChatGPT 的 AI 算命/占卜应用）的核心功能和 UI 设计集成到 N.E.K.O 塔罗牌插件中。

## 源项目分析

### 功能列表
1. **塔罗牌占卜** - 三牌阵（过去/现在/未来）
2. **生辰八字** - 根据出生时间分析命理
3. **姓名五格** - 通过姓名笔画分析性格和命运
4. **周公解梦** - 解析梦境含义
5. **起名取名** - 根据生辰八字和五行推荐吉祥名字
6. **梅花易数** - 传统易学占卜方法
7. **姻缘占卜** - 分析感情运势和姻缘走向

### 核心技术栈
- **后端**: Python + FastAPI
- **前端**: React + Vite + Tailwind CSS
- **特色**: 流式输出、历史记录、响应式设计、暗色模式

### 后端核心架构
```
src/
├── divination/          # 占卜逻辑
│   ├── base.py          # DivinationFactory 工厂模式
│   ├── tarot.py         # 塔罗牌 Prompt
│   ├── birthday.py      # 生辰八字 Prompt
│   ├── dream.py         # 周公解梦 Prompt
│   ├── name.py          # 姓名五格 Prompt
│   ├── new_name.py      # 起名取名 Prompt
│   ├── plum_flower.py   # 梅花易数 Prompt
│   └── fate.py          # 姻缘占卜 Prompt
├── app.py               # FastAPI 应用
├── chatgpt_router.py    # ChatGPT API 路由
├── config.py            # 配置管理
└── models.py            # 数据模型
```

### 前端核心架构
```
frontend/src/
├── pages/divination/    # 占卜页面
│   ├── TarotPage.tsx    # 塔罗牌页面
│   ├── BirthdayPage.tsx # 生辰八字页面
│   ├── DreamPage.tsx    # 周公解梦页面
│   ├── NamePage.tsx     # 姓名五格页面
│   ├── NewNamePage.tsx  # 起名取名页面
│   ├── PlumFlowerPage.tsx # 梅花易数页面
│   └── FatePage.tsx     # 姻缘占卜页面
├── components/          # 共享组件
├── hooks/              # React Hooks
├── config/constants.ts  # 配置常量
└── store/index.ts      # 状态管理
```

## 集成策略

### Phase 1: 塔罗牌核心功能（当前优先级最高）
1. **后端 Prompt 优化**: 使用源项目的 `TAROT_PROMPT`，让猫娘更专业地解读
2. **前端 UI 重构**: 参考源项目的 React 组件设计，使用原生 HTML/CSS/JS 实现
3. **流式输出**: 模拟源项目的打字机效果
4. **历史记录**: 每种占卜类型保存最近记录

### Phase 2: 扩展其他占卜类型
逐步将其他占卜类型（生辰八字、姓名五格等）集成进来

## 关键技术决策

### 1. Prompt 设计
源项目的 `TAROT_PROMPT`:
```
"我请求你担任塔罗占卜师的角色。您将接受我的问题并使用虚拟塔罗牌进行塔罗牌阅读。"
"不要忘记洗牌并介绍您在本套牌中使用的套牌。请帮我抽3张随机卡。"
"拿到卡片后，请您仔细说明它们的意义，解释哪张卡片属于未来或现在或过去，"
"结合我的问题来解释它们，并给我有用的建议或我现在应该做的事情."
```

### 2. 前端 UI 设计
- 使用原生 HTML/CSS/JS（不使用 React，因为 N.E.K.O 插件是静态文件服务）
- 参考源项目的 Tailwind CSS 样式和组件设计
- 保持塔罗牌的神秘浪漫风格

### 3. 与 N.E.K.O 架构的适配
- 后端逻辑集成到 `tarot/__init__.py` 中
- 前端集成到 `tarot/static/index.html` 中
- 保持 N.E.K.O 插件的 `@plugin_entry` 装饰器模式

## 实施步骤

1. ✅ 克隆源项目到本地
2.  分析源项目架构（当前步骤）
3. ⏳ 重写塔罗牌后端逻辑（集成 TAROT_PROMPT）
4. ⏳ 重写前端 UI（参考源项目设计）
5. ⏳ 测试和验证
6. ⏳ 逐步集成其他占卜类型

## 注意事项

- 源项目使用 MIT License，可以免费使用和修改
- 需要适配 N.E.K.O 插件架构，不能直接照搬代码
- 保持塔罗牌的神秘浪漫风格（粉、蓝、白、橙等明亮色调）
