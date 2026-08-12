"""
Tarot Reader Plugin

塔罗牌占卜插件 - 集成自 chatgpt-tarot-divination 项目
提供塔罗牌、生辰八字、姓名五格、周公解梦、起名取名、梅花易数、姻缘占卜、星座运势、抽签占卜等服务
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from plugin.sdk.plugin import (
    NekoPluginBase,
    neko_plugin,
    plugin_entry,
    lifecycle,
    Ok,
    Err,
    SdkError,
)

# 源项目的 TAROT_PROMPT
TAROT_PROMPT = """我请求你担任塔罗占卜师的角色。您将接受我的问题并使用虚拟塔罗牌进行塔罗牌阅读。不要忘记洗牌并介绍您在本套牌中使用的套牌。请帮我抽3张随机卡。拿到卡片后，请您仔细说明它们的意义，解释哪张卡片属于未来或现在或过去，结合我的问题来解释它们，并给我有用的建议或我现在应该做的事情。"""

# 22张大阿卡纳塔罗牌
_TAROT_CARDS = [
    {"id": 0, "name": "愚者", "name_en": "The Fool", "number": "0", "arcana": "major",
     "upright": ["新的开始", "冒险", "天真", "自发", "潜力", "自由"], "reversed": ["鲁莽", "冒险", "犹豫不决", "缺乏方向", "轻率"],
     "description": "代表新的开始、无限可能性和冒险精神。愚者提醒我们要相信直觉，勇敢踏出第一步，虽然看似天真，但蕴含着巨大的潜力。",
     "element": "风", "zodiac": "天王星"},
    {"id": 1, "name": "魔术师", "name_en": "The Magician", "number": "I", "arcana": "major",
     "upright": ["创造力", "技能", "意志力", "专注", "显化", "资源"], "reversed": ["欺骗", "操控", "缺乏自信", "浪费天赋", "负面意图"],
     "description": "象征创造力、技能和意志力。你拥有实现目标所需的一切资源。魔术师连接天地，表明你有能力将想法变为现实。",
     "element": "风", "zodiac": "水星"},
    {"id": 2, "name": "女祭司", "name_en": "The High Priestess", "number": "II", "arcana": "major",
     "upright": ["直觉", "潜意识", "神秘", "内在智慧", "神圣知识", "耐心"], "reversed": ["隐藏动机", "冷漠", "直觉受阻", "秘密暴露", "沟通中断"],
     "description": "代表深层的直觉和潜意识智慧。倾听内心的声音，答案就在你心中。女祭司守护着神圣的知识，提醒我们信任内在的智慧。",
     "element": "水", "zodiac": "月亮"},
    {"id": 3, "name": "女皇", "name_en": "The Empress", "number": "III", "arcana": "major",
     "upright": ["丰饶", "母性", "自然", "感官享受", "创造力", "美丽"], "reversed": ["依赖", "过度保护", "空虚", "创造性停滞", "忽视需求"],
     "description": "象征丰饶、母性和自然的力量。享受生活中的美好，滋养自己和他人。女皇代表生育力、创造力和大自然的慷慨馈赠。",
     "element": "土", "zodiac": "金星"},
    {"id": 4, "name": "皇帝", "name_en": "The Emperor", "number": "IV", "arcana": "major",
     "upright": ["权威", "稳定", "领导力", "结构", "控制", "保护"], "reversed": ["专制", "僵化", "缺乏纪律", "混乱", "暴政"],
     "description": "代表权威、稳定和领导力。建立秩序和结构，展现你的管理能力。皇帝象征父性原则和对秩序的需要。",
     "element": "火", "zodiac": "白羊座"},
    {"id": 5, "name": "教皇", "name_en": "The Hierophant", "number": "V", "arcana": "major",
     "upright": ["传统", "信仰", "指导", "教育", "精神指导", "道德"], "reversed": ["反叛", "打破常规", "新信仰", "非传统", "个人信念"],
     "description": "象征传统、信仰和精神指导。寻求智者的建议，遵循内心的信念。教皇代表传统的智慧和精神价值观。",
     "element": "土", "zodiac": "金牛座"},
    {"id": 6, "name": "恋人", "name_en": "The Lovers", "number": "VI", "arcana": "major",
     "upright": ["爱情", "和谐", "选择", "关系", "价值观整合", "吸引力"], "reversed": ["不和谐", "失衡", "错误选择", "冲突", "分离"],
     "description": "代表爱情、和谐和重要的人生选择。跟随你的心，做出正确的决定。这张牌更多关乎价值观的选择而非单纯的爱情。",
     "element": "风", "zodiac": "双子座"},
    {"id": 7, "name": "战车", "name_en": "The Chariot", "number": "VII", "arcana": "major",
     "upright": ["胜利", "决心", "控制", "意志力", "前进", "征服"], "reversed": ["失控", "侵略", "缺乏方向", "冲突", "挫败"],
     "description": "象征胜利、决心和自我控制。坚定目标，你将克服一切障碍。战车代表意志的力量和向前推进的决心。",
     "element": "水", "zodiac": "巨蟹座"},
    {"id": 8, "name": "力量", "name_en": "Strength", "number": "VIII", "arcana": "major",
     "upright": ["勇气", "耐心", "内在力量", "温柔", "自制", "同情"], "reversed": ["自我怀疑", "软弱", "不安全感", "暴力", "压迫"],
     "description": "代表内在的力量和勇气。真正的力量来自内心的平静与温柔。力量女神驯服猛兽，象征柔能克刚。",
     "element": "火", "zodiac": "狮子座"},
    {"id": 9, "name": "隐者", "name_en": "The Hermit", "number": "IX", "arcana": "major",
     "upright": ["内省", "寻求真理", "孤独", "智慧", "指导", "反思"], "reversed": ["孤立", "退缩", "迷失", "缺乏指导", "逃避"],
     "description": "象征内省和寻求真理。独处时你能找到内心真正的答案。隐者提灯照亮道路，代表智慧的引导。",
     "element": "土", "zodiac": "处女座"},
    {"id": 10, "name": "命运之轮", "name_en": "Wheel of Fortune", "number": "X", "arcana": "major",
     "upright": ["命运", "转折点", "好运", "循环", "机会", "变化"], "reversed": ["厄运", "抵抗改变", "停滞", "坏运气", "时机不对"],
     "description": "代表命运的转折点和生命的循环。接受变化，好运即将来临。命运之轮象征宇宙的自然循环和因果法则。",
     "element": "火", "zodiac": "木星"},
    {"id": 11, "name": "正义", "name_en": "Justice", "number": "XI", "arcana": "major",
     "upright": ["公正", "真相", "因果", "法律", "诚实", "平衡"], "reversed": ["不公", "欺骗", "逃避责任", "偏见", "失衡"],
     "description": "象征公正、真相和因果律。诚实面对自己和他人，正义终将到来。正义天平衡量因果，提醒我们承担后果。",
     "element": "风", "zodiac": "天秤座"},
    {"id": 12, "name": "倒吊人", "name_en": "The Hanged Man", "number": "XII", "arcana": "major",
     "upright": ["牺牲", "新视角", "等待", "放下", "灵性", "暂停"], "reversed": ["拖延", "无谓牺牲", "固执", "抗拒", "缺乏远见"],
     "description": "代表牺牲和新的视角。有时候需要换个角度看问题。倒吊人象征自愿的牺牲和通过暂停获得洞察。",
     "element": "水", "zodiac": "海王星"},
    {"id": 13, "name": "死神", "name_en": "Death", "number": "XIII", "arcana": "major",
     "upright": ["结束", "转变", "重生", "放下", "过渡", "转化"], "reversed": ["抗拒改变", "恐惧", "停滞", "延迟", "恢复"],
     "description": "象征结束和转变。旧事物的消逝为新生命腾出空间。死神代表必要的变革和生命阶段的转换。",
     "element": "水", "zodiac": "天蝎座"},
    {"id": 14, "name": "节制", "name_en": "Temperance", "number": "XIV", "arcana": "major",
     "upright": ["平衡", "耐心", "和谐", "中庸", "融合", "调和"], "reversed": ["失衡", "过度", "不协调", "极端", "冲突"],
     "description": "代表平衡、耐心和和谐。在两极之间找到中庸之道。节制天使调和水火，象征融合与和谐。",
     "element": "火", "zodiac": "射手座"},
    {"id": 15, "name": "恶魔", "name_en": "The Devil", "number": "XV", "arcana": "major",
     "upright": ["束缚", "诱惑", "执着", "阴影", "物质主义", "沉溺"], "reversed": ["解脱", "突破", "重获自由", "觉醒", "释放"],
     "description": "象征束缚和诱惑。认识到限制你的枷锁，你才能重获自由。恶魔提醒我们摆脱有害的依恋。",
     "element": "土", "zodiac": "摩羯座"},
    {"id": 16, "name": "塔", "name_en": "The Tower", "number": "XVI", "arcana": "major",
     "upright": ["突变", "启示", "觉醒", "崩解", "突然变化", "摧毁"], "reversed": ["避免灾难", "恐惧改变", "延迟", "抵抗", "渐进变化"],
     "description": "代表突变和启示。旧结构的崩塌是为了更好的重建。塔象征突然的觉醒和不可避免的变革。",
     "element": "火", "zodiac": "火星"},
    {"id": 17, "name": "星星", "name_en": "The Star", "number": "XVII", "arcana": "major",
     "upright": ["希望", "灵感", "宁静", "治愈", "指引", "愿景"], "reversed": ["绝望", "失去信心", "缺乏能量", "迷茫", "失望"],
     "description": "象征希望、灵感和宁静。黑暗之后必有光明，保持信心。星星洒下甘露，代表疗愈和精神滋养。",
     "element": "风", "zodiac": "水瓶座"},
    {"id": 18, "name": "月亮", "name_en": "The Moon", "number": "XVIII", "arcana": "major",
     "upright": ["幻象", "恐惧", "潜意识", "直觉", "梦境", "迷惑"], "reversed": ["释放恐惧", "真相浮现", "清晰", "直面恐惧", "觉醒"],
     "description": "代表幻象和潜意识。不要被表象迷惑，寻找隐藏的真相。月亮照亮潜意识，提醒我们面对恐惧。",
     "element": "水", "zodiac": "双鱼座"},
    {"id": 19, "name": "太阳", "name_en": "The Sun", "number": "XIX", "arcana": "major",
     "upright": ["快乐", "成功", "活力", "光明", "喜悦", "清晰"], "reversed": ["暂时的抑郁", "延迟的成功", "悲观", "缺乏活力", "挫折"],
     "description": "象征快乐、成功和光明。阳光灿烂的日子即将到来。太阳带来成功、快乐和精神的清晰。",
     "element": "火", "zodiac": "太阳"},
    {"id": 20, "name": "审判", "name_en": "Judgement", "number": "XX", "arcana": "major",
     "upright": ["觉醒", "重生", "召唤", "反思", "宽恕", "精神复苏"], "reversed": ["自我怀疑", "拒绝改变", "忽视召唤", "内疚", "评判"],
     "description": "代表觉醒和重生。听从内心的召唤，迎接新的生命阶段。审判象征精神的复苏和新的开始。",
     "element": "火", "zodiac": "冥王星"},
    {"id": 21, "name": "世界", "name_en": "The World", "number": "XXI", "arcana": "major",
     "upright": ["完成", "成就", "旅行", "圆满", "成功", "整合"], "reversed": ["未完成", "延迟", "缺乏成就", "不完整", "循环未闭"],
     "description": "象征完成和成就。一个循环的结束，你即将达到圆满。世界代表目标的达成和旅程的完成。",
     "element": "土", "zodiac": "土星"},
]

# 牌阵定义
_SPREADS = {
    "single": {"name": "单牌占卜", "description": "抽取一张牌，获得今日指引", "count": 1},
    "three_card": {"name": "三牌阵", "description": "过去、现在、未来", "count": 3},
    "love": {"name": "爱情牌阵", "description": "你的感情、对方的感情、关系未来", "count": 3},
    "celtic_cross": {"name": "凯尔特十字", "description": "全面的命运解析", "count": 6},
}

# 建议模板
_ADVICE_TEMPLATES = {
    "general": [
        "星辰为你指引方向，相信内心的声音。",
        "每一次选择都是新的开始，勇敢前行。",
        "宇宙的能量正在汇聚，好运即将来临。",
        "保持开放的心态，奇迹就在你身边。",
        "命运之轮已经开始转动，准备迎接变化。",
    ],
    "love": [
        "爱如春风，温柔而坚定，让心自然绽放。",
        "缘分的丝线正在悄然编织，静待花开。",
        "真诚的心能打动最坚硬的冰，勇敢表达。",
        "爱情需要耐心，如花朵般慢慢绽放。",
        "两颗心的距离，只差一次勇敢的靠近。",
    ],
    "career": [
        "努力的种子正在发芽，收获的季节不远。",
        "新的机遇如晨星般闪耀，准备好抓住它。",
        "专注与坚持是通往成功的金桥。",
        "你的才华如钻石，终会被人发现。",
        "职场如棋局，每一步都需要智慧与勇气。",
    ],
    "daily": [
        "今日宜：保持微笑，好运自然来。",
        "今日幸运色如彩虹般绚烂，让色彩点亮心情。",
        "宇宙在今天为你准备了小惊喜，留心观察。",
        "今天的你如同阳光般温暖，感染身边的每个人。",
        "放慢脚步，享受当下的每一刻美好。",
    ],
}

# 幸运元素
_LUCKY_ELEMENTS = {
    "colors": ["粉色", "天蓝色", "白色", "橙色", "紫色", "金色", "绿色", "红色"],
    "numbers": [1, 3, 5, 7, 8, 9, 11, 13, 15, 21],
    "directions": ["东方", "南方", "西方", "北方", "东南", "东北", "西南", "西北"],
    "times": ["清晨", "上午", "中午", "下午", "傍晚", "夜晚"],
}

# 十二星座数据
_ZODIAC_SIGNS = {
    "白羊座": {"dates": "3.21-4.19", "element": "火", "ruling": "火星", "traits": "热情、冲动、自信、勇敢", "compatibility": "狮子座、射手座"},
    "金牛座": {"dates": "4.20-5.20", "element": "土", "ruling": "金星", "traits": "稳重、踏实、固执、忠诚", "compatibility": "处女座、摩羯座"},
    "双子座": {"dates": "5.21-6.21", "element": "风", "ruling": "水星", "traits": "聪明、善变、好奇、社交", "compatibility": "天秤座、水瓶座"},
    "巨蟹座": {"dates": "6.22-7.22", "element": "水", "ruling": "月亮", "traits": "温柔、敏感、顾家、体贴", "compatibility": "天蝎座、双鱼座"},
    "狮子座": {"dates": "7.23-8.22", "element": "火", "ruling": "太阳", "traits": "自信、大方、慷慨、领导力", "compatibility": "白羊座、射手座"},
    "处女座": {"dates": "8.23-9.22", "element": "土", "ruling": "水星", "traits": "细心、完美主义、理性、务实", "compatibility": "金牛座、摩羯座"},
    "天秤座": {"dates": "9.23-10.23", "element": "风", "ruling": "金星", "traits": "优雅、公正、善交际、和平主义", "compatibility": "双子座、水瓶座"},
    "天蝎座": {"dates": "10.24-11.22", "element": "水", "ruling": "冥王星", "traits": "神秘、执着、洞察力强、感性", "compatibility": "巨蟹座、双鱼座"},
    "射手座": {"dates": "11.23-12.21", "element": "火", "ruling": "木星", "traits": "乐观、自由、冒险、幽默", "compatibility": "白羊座、狮子座"},
    "摩羯座": {"dates": "12.22-1.19", "element": "土", "ruling": "土星", "traits": "坚韧、负责任、自律、务实", "compatibility": "金牛座、处女座"},
    "水瓶座": {"dates": "1.20-2.18", "element": "风", "ruling": "天王星", "traits": "独立、创新、理性、博爱", "compatibility": "双子座、天秤座"},
    "双鱼座": {"dates": "2.19-3.20", "element": "水", "ruling": "海王星", "traits": "浪漫、敏感、想象力、同情心", "compatibility": "巨蟹座、天蝎座"},
}

_ZODIAC_ASPECTS = ["综合运势", "爱情运势", "事业学业", "财富运势", "健康运势"]
_ZODIAC_RATINGS = ["⭐⭐⭐⭐⭐", "⭐⭐⭐⭐✨", "⭐⭐⭐⭐", "⭐⭐⭐✨", "⭐⭐⭐"]
_ZODIAC_ADVICE_POOL = {
    "综合运势": [
        "今天整体运势平稳向上，适合按计划推进各项事务。",
        "宇宙能量正在汇聚，今天是个行动的好日子。",
        "今日宜静不宜动，适合反思和调整状态。",
        "贵人运旺盛，多与朋友交流会带来好运。",
        "灵感迸发的一天，适合创意和思考。",
    ],
    "爱情运势": [
        "单身者桃花运旺盛，有机会遇到心仪的对象。",
        "有伴侣者感情甜蜜，适合共度浪漫时光。",
        "感情方面需要多沟通，避免小误会。",
        "旧爱可能重新出现，理性面对内心感受。",
        "今天适合表达心意，勇敢说出你的爱。",
    ],
    "事业学业": [
        "工作效率高涨，重要项目有望取得突破。",
        "学习上专注力极强，适合攻克难题。",
        "职场人际关系和谐，团队合作顺利。",
        "新的学习机会即将到来，保持开放心态。",
        "今天适合制定长期目标，为未来打基础。",
    ],
    "财富运势": [
        "财运亨通，有意外收获的可能。",
        "适合理财规划，但不宜冲动投资。",
        "正财运稳定，偏财运一般。",
        "今天可能有小笔支出，注意预算管理。",
        "贵人带来赚钱机会，把握良机。",
    ],
    "健康运势": [
        "精力充沛，适合运动和户外活动。",
        "注意作息规律，避免熬夜。",
        "多喝水，注意饮食均衡。",
        "适合做瑜伽或冥想，放松身心。",
        "心情愉悦，保持积极心态最重要。",
    ],
}

# 签筒数据 - 100签（上上签10签、上签20签、中签40签、下签20签、下下签10签）
_LOTTERY_LEVELS = {
    "上上签": {"emoji": "🌟", "count": 10, "weight": 10},
    "上签": {"emoji": "✨", "count": 20, "weight": 20},
    "中签": {"emoji": "🔮", "count": 40, "weight": 40},
    "下签": {"emoji": "🌧️", "count": 20, "weight": 20},
    "下下签": {"emoji": "⚡", "count": 10, "weight": 10},
}

_LOTTERY_POEMS = {
    "上上签": [
        "大鹏一日同风起，扶摇直上九万里。",
        "春风得意马蹄疾，一日看尽长安花。",
        "长风破浪会有时，直挂云帆济沧海。",
        "山重水复疑无路，柳暗花明又一村。",
        "海阔凭鱼跃，天高任鸟飞。",
        "千磨万击还坚劲，任尔东西南北风。",
        "会当凌绝顶，一览众山小。",
        "天生我材必有用，千金散尽还复来。",
        "乘风破浪会有时，花重锦官城。",
        "青云直上凌霄汉，万事亨通达九重。",
    ],
    "上签": [
        "好雨知时节，当春乃发生。",
        "日出江花红胜火，春来江水绿如蓝。",
        "竹外桃花三两枝，春江水暖鸭先知。",
        "两岸猿声啼不住，轻舟已过万重山。",
        "桃花潭水深千尺，不及汪伦送我情。",
        "天街小雨润如酥，草色遥看近却无。",
        "春色满园关不住，一枝红杏出墙来。",
        "落红不是无情物，化作春泥更护花。",
        "劝君更尽一杯酒，西出阳关无故人。",
        "莫愁前路无知己，天下谁人不识君。",
        "但愿人长久，千里共婵娟。",
        "海内存知己，天涯若比邻。",
        "人间四月芳菲尽，山寺桃花始盛开。",
        "接天莲叶无穷碧，映日荷花别样红。",
        "欲穷千里目，更上一层楼。",
        "采菊东篱下，悠然见南山。",
        "不畏浮云遮望眼，自缘身在最高层。",
        "千里莺啼绿映红，水村山郭酒旗风。",
        "独在异乡为异客，每逢佳节倍思亲。",
        "此情可待成追忆，只是当时已惘然。",
    ],
    "中签": [
        "行到水穷处，坐看云起时。",
        "路漫漫其修远兮，吾将上下而求索。",
        "沉舟侧畔千帆过，病树前头万木春。",
        "山不在高，有仙则名。",
        "水不在深，有龙则灵。",
        "不经一番寒彻骨，怎得梅花扑鼻香。",
        "人生自古谁无死，留取丹心照汗青。",
        "世事洞明皆学问，人情练达即文章。",
        "纸上得来终觉浅，绝知此事要躬行。",
        "问渠哪得清如许，为有源头活水来。",
        "读书破万卷，下笔如有神。",
        "少壮不努力，老大徒伤悲。",
        "一寸光阴一寸金，寸金难买寸光阴。",
        "黑发不知勤学早，白首方悔读书迟。",
        "业精于勤荒于嬉，行成于思毁于随。",
        "学而不思则罔，思而不学则殆。",
        "知之为知之，不知为不知。",
        "三人行，必有我师焉。",
        "满招损，谦受益。",
        "工欲善其事，必先利其器。",
        "君子坦荡荡，小人长戚戚。",
        "知者不惑，仁者不忧，勇者不惧。",
        "岁寒，然后知松柏之后凋也。",
        "逝者如斯夫，不舍昼夜。",
        "己所不欲，勿施于人。",
        "见贤思齐焉，见不贤而内自省也。",
        "温故而知新，可以为师矣。",
        "学然后知不足，教然后知困。",
        "穷则变，变则通，通则久。",
        "天行健，君子以自强不息。",
        "地势坤，君子以厚德载物。",
        "二人同心，其利断金。",
        "言必信，行必果。",
        "言者无罪，闻者足戒。",
        "有则改之，无则加勉。",
        "流水不腐，户枢不蠹。",
        "千里之行，始于足下。",
        "知人者智，自知者明。",
        "胜人者有力，自胜者强。",
        "祸兮福之所倚，福兮祸之所伏。",
    ],
    "下签": [
        "抽刀断水水更流，举杯消愁愁更愁。",
        "寻寻觅觅，冷冷清清，凄凄惨惨戚戚。",
        "人生若只如初见，何事秋风悲画扇。",
        "问君能有几多愁，恰似一江春水向东流。",
        "剪不断，理还乱，是离愁。",
        "多情自古伤离别，更那堪冷落清秋节。",
        "衣带渐宽终不悔，为伊消得人憔悴。",
        "此情无计可消除，才下眉头，却上心头。",
        "无可奈何花落去，似曾相识燕归来。",
        "花自飘零水自流，一种相思两处闲愁。",
        "物是人非事事休，欲语泪先流。",
        "曾经沧海难为水，除却巫山不是云。",
        "春风又绿江南岸，明月何时照我还。",
        "夕阳无限好，只是近黄昏。",
        "自古多情空余恨，此恨绵绵无绝期。",
        "人生得意须尽欢，莫使金樽空对月。",
        "对酒当歌，人生几何。",
        "人有悲欢离合，月有阴晴圆缺。",
        "世间安得双全法，不负如来不负卿。",
        "人生自是有情痴，此恨不关风与月。",
    ],
    "下下签": [
        "大江东去，浪淘尽，千古风流人物。",
        "长太息以掩涕兮，哀民生之多艰。",
        "国破山河在，城春草木深。",
        "烽火连三月，家书抵万金。",
        "安得广厦千万间，大庇天下寒士俱欢颜。",
        "朱门酒肉臭，路有冻死骨。",
        "白骨露于野，千里无鸡鸣。",
        "念天地之悠悠，独怆然而涕下。",
        "出师未捷身先死，长使英雄泪满襟。",
        "力拔山兮气盖世，时不利兮骓不逝。",
    ],
}

_LOTTERY_INTERPRETATIONS = {
    "上上签": [
        "此签大吉大利，万事亨通。你所求之事皆能如愿，财运、事业、感情皆有好转。宜把握良机，积极行动。",
        "天降鸿福，贵人相助。近期将有喜事临门，事业上有望取得突破，感情和睦，家庭幸福。",
        "万事如意，心想事成。你所期盼的事情即将实现，只需保持信心，静待花开。",
        "福星高照，好运连连。此签主大吉，诸事顺遂，前程似锦。",
        "春风得意，事事顺心。贵人运旺盛，有机会获得重要帮助，事业和感情都将迈上新台阶。",
        "否极泰来，鸿运当头。过去的努力终于有了回报，现在是收获的季节。",
        "龙腾虎跃，气势如虹。你正处于人生最好的阶段之一，把握当下，未来可期。",
        "天赐良机，千载难逢。近期有重大机遇出现，务必抓住，不要错过。",
        "金玉满堂，富贵双全。财运极旺，事业有成，家庭和睦，万事皆宜。",
        "前程似锦，步步高升。此签主升迁、发财、姻缘美满，大吉之兆。",
    ],
    "上签": [
        "此签吉利，所求之事多有成就。宜稳扎稳打，循序渐进，不可急躁冒进。",
        "运势向上，好事将至。保持积极心态，耐心等待，机遇即将到来。",
        "贵人暗助，事半功倍。多与人交流合作，有助事业发展。",
        "顺风顺水，小有收获。虽然不是大富大贵，但安稳幸福。",
        "心想事成，所愿可期。只要脚踏实地，目标一定能实现。",
        "吉星高照，平安如意。此签主平安顺遂，虽无大起大落，但胜在安稳。",
        "运势渐佳，柳暗花明。之前的困境正在消散，好运即将到来。",
        "和气生财，以柔克刚。用温和的态度处事，自然会有好结果。",
        "稳中有进，步步为营。不急不躁，按照自己的节奏前行即可。",
        "花开富贵，好事将近。再坚持一下，就能看到希望。",
    ],
    "中签": [
        "此签平稳，不好不坏。所求之事需多加努力，不可懈怠。宜守不宜进。",
        "运势一般，需靠自己努力。没有太多外力帮助，但也没有太大阻碍。",
        "平淡是真，安稳度日。虽然没有惊喜，但也不会有大的波折。",
        "事在人为，机遇需等待。目前时机未到，不宜强求，耐心等待。",
        "中庸之道，不偏不倚。保持平常心，不过分乐观也不悲观。",
        "有得有失，平衡为上。凡事不可太执着，得失随缘。",
        "守正出奇，稳中求变。在保持稳定的基础上，适当尝试新的方向。",
        "时来运转，需要耐心。好运还在路上，不要急于求成。",
        "平平淡淡才是真。不必追求太多，珍惜当下就好。",
        "凡事预则立，不预则废。做好充分准备，机遇来时才不会错过。",
    ],
    "下签": [
        "此签欠佳，所求之事多有阻碍。宜韬光养晦，静待时机。",
        "运势低迷，不宜妄动。先调整状态，等待好转的时机。",
        "困难当前，不可气馁。每一次挫折都是成长的机会。",
        "事倍功半，需反省调整方向。不要一味坚持错误的方法。",
        "小人当道，注意防范。交友需谨慎，避免被连累。",
        "逆境之中，保持信心。黑夜过后就是黎明。",
        "此时不宜行动，宜静观其变。等待时机成熟再出手。",
        "遭遇挫折是常态，关键在于如何应对。调整心态，重新开始。",
        "运势不佳，宜低调行事。不要锋芒太露，以免惹来麻烦。",
        "风雨过后见彩虹。目前的困难只是暂时的，坚持下去就好。",
    ],
    "下下签": [
        "此签大凶，诸事不宜。宜韬光养晦，修心养性，等待运势好转。",
        "时运不济，命途多舛。此时最宜静守，不可妄动，免招祸患。",
        "困境重重，需极大的耐心和智慧。先保全自己，再图发展。",
        "大难临头，务必谨慎行事。凡事三思而后行，不可冲动。",
        "命运的低谷期，但也是成长的契机。在逆境中磨砺自己。",
        "万般皆是命，半点不由人。接受现实，调整心态，等待转机。",
        "此签警示你注意当前的问题。及时反省和改进，可以避免更大的损失。",
        "山穷水尽之时，也是转机开始之日。坚持住，不要放弃。",
        "大凶之签，宜退不宜进。先稳住阵脚，再图后计。",
        "祸福相依，吉凶难料。看似不好的签，也可能暗藏机遇。保持警惕，把握转机。",
    ],
}


def _iso(dt: datetime | None = None) -> str:
    val = dt or datetime.now(timezone.utc)
    return val.astimezone(timezone.utc).isoformat()


def _draw_cards(count: int) -> list[dict]:
    """抽牌，不重复"""
    drawn_ids = set()
    result = []
    for _ in range(count):
        available = [c for c in _TAROT_CARDS if c["id"] not in drawn_ids]
        if not available:
            break
        card = random.choice(available)
        drawn_ids.add(card["id"])
        is_reversed = random.random() < 0.3
        result.append({
            "card": card,
            "is_reversed": is_reversed,
            "position": None,
        })
    return result


def _build_reading(spread_type: str, question: str = "") -> dict[str, Any]:
    """构建完整的占卜结果"""
    spread = _SPREADS[spread_type]
    cards = _draw_cards(spread["count"])

    positions = {
        "single": ["今日指引"],
        "three_card": ["过去", "现在", "未来"],
        "love": ["你的感情", "对方的感情", "关系未来"],
        "celtic_cross": ["现状", "挑战", "潜意识", "过去", "未来", "建议"],
    }

    position_labels = positions.get(spread_type, [f"位置{i+1}" for i in range(spread["count"])])

    reading_cards = []
    for i, card_draw in enumerate(cards):
        card_draw["position"] = position_labels[i] if i < len(position_labels) else f"位置{i+1}"
        keywords = card_draw["card"]["reversed"] if card_draw["is_reversed"] else card_draw["card"]["upright"]
        reading_cards.append({
            "position": card_draw["position"],
            "card": card_draw["card"],
            "is_reversed": card_draw["is_reversed"],
            "orientation": "逆位" if card_draw["is_reversed"] else "正位",
            "keywords": keywords,
            "interpretation": _generate_interpretation(card_draw["card"], card_draw["is_reversed"], card_draw["position"]),
        })

    advice_category = spread_type if spread_type in _ADVICE_TEMPLATES else "general"
    advice = random.choice(_ADVICE_TEMPLATES[advice_category])

    lucky = {
        "color": random.choice(_LUCKY_ELEMENTS["colors"]),
        "number": random.choice(_LUCKY_ELEMENTS["numbers"]),
        "direction": random.choice(_LUCKY_ELEMENTS["directions"]),
        "time": random.choice(_LUCKY_ELEMENTS["times"]),
    }

    return {
        "spread": spread,
        "question": question,
        "cards": reading_cards,
        "advice": advice,
        "lucky": lucky,
        "timestamp": _iso(),
    }


def _generate_interpretation(card: dict, is_reversed: bool, position: str) -> str:
    """生成牌义解读"""
    orientation = "逆位" if is_reversed else "正位"
    base = f"{card['name']}({card['name_en']}){orientation}"

    # 根据正逆位选择关键词
    keywords = card['reversed'] if is_reversed else card['upright']
    keywords_str = "、".join(keywords)

    interpretations = {
        "今日指引": f"今日塔罗指引：{base}。{card['description']} 关键词：{keywords_str}",
        "过去": f"在过去的位置，{base}暗示着一段影响深远的经历。{card['description']} 关键词：{keywords_str}",
        "现在": f"在现在的位置，{base}提醒你关注当下。{card['description']} 关键词：{keywords_str}",
        "未来": f"在未来的位置，{base}预示着即将到来的变化。{card['description']} 关键词：{keywords_str}",
        "你的感情": f"关于你的感情，{base}揭示了你内心的真实感受。{card['description']} 关键词：{keywords_str}",
        "对方的感情": f"关于对方的感情，{base}暗示了TA可能的想法和感受。{card['description']} 关键词：{keywords_str}",
        "关系未来": f"关于关系的未来，{base}为你们的感情之路提供了启示。{card['description']} 关键词：{keywords_str}",
        "现状": f"你目前的处境由{base}所代表。{card['description']} 关键词：{keywords_str}",
        "挑战": f"你面临的挑战与{base}有关。{card['description']} 关键词：{keywords_str}",
        "潜意识": f"你的潜意识深处，{base}在默默影响着你的决定。{card['description']} 关键词：{keywords_str}",
        "建议": f"塔罗给你的建议：{base}。{card['description']} 关键词：{keywords_str}",
    }

    return interpretations.get(position, f"{base}。{card['description']} 关键词：{keywords_str}")


def _build_catgirl_message(reading: dict[str, Any]) -> str:
    """构建发送给猫娘的消息，让她能理解并回应塔罗牌结果"""
    spread_name = reading["spread"]["name"]
    question = reading.get("question", "")

    # 开场白 - 引起猫娘注意
    if question:
        intro = f"主人刚刚让我帮他占卜了「{question}」，用的是{spread_name}呢～"
    else:
        intro = f"主人刚刚做了{spread_name}的塔罗牌占卜～"

    lines = [intro]

    # 牌面信息 - 简洁明了
    for c in reading["cards"]:
        card = c["card"]
        pos = c["position"]
        orient = c["orientation"]

        if c["position"] == "今日指引":
            lines.append(f"抽到的是「{card['name']}」{orient}～")
        else:
            lines.append(f"「{pos}」的位置是「{card['name']}」{orient}")

    # 建议和幸运元素
    lines.append(f"\n塔罗牌给出的建议是：{reading['advice']}")

    lucky = reading.get("lucky", {})
    if lucky:
        lines.append(f"今天的幸运色是{lucky.get('color', '')}，幸运数字是{lucky.get('number', '')}～")

    # 引导猫娘回应
    lines.append("\n主人好像很在意这个结果呢，你觉得塔罗牌说得准不准呀？")

    return "\n".join(lines)


@neko_plugin
class TarotReaderPlugin(NekoPluginBase):
    """塔罗牌占卜插件 - 集成自 chatgpt-tarot-divination 项目"""

    def __init__(self, ctx: Any):
        super().__init__(ctx)
        self.logger = ctx.logger
        self._reading_count = 0
        self._readings: list[dict[str, Any]] = []

    @property
    def _state_file(self) -> Path:
        return self.data_path("tarot_state.json")

    async def _load_state(self) -> None:
        path = self._state_file
        self.logger.info(f"[塔罗牌] 尝试读取状态文件: {path}")
        if not path.exists():
            self.logger.info("[塔罗牌] 状态文件不存在，跳过加载")
            return

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._reading_count = data.get("reading_count", 0)
            self._readings = data.get("readings", [])[-50:]
            self.logger.info(f"[塔罗牌] 已加载 {len(self._readings)} 条占卜记录")
        except Exception as exc:
            self.logger.warning(f"[塔罗牌] 读取状态失败: {exc}")

    async def _save_state(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(
            json.dumps({
                "reading_count": self._reading_count,
                "readings": self._readings[-50:],
                "updated_at": _iso(),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def _notify_catgirl(self, reading: dict[str, Any]) -> None:
        """档2：给猫娘发，需要猫娘回应（给用户听）"""
        try:
            message = _build_catgirl_message(reading)
            self.ctx.push_message(
                source="tarot_reader",
                ai_behavior="respond",  # 档2：猫娘会回应给用户听
                parts=[{"type": "text", "text": message}],
                priority=5,  # 高优先级，确保猫娘能注意到
            )
            self.logger.info("[塔罗牌] 已将占卜结果推送给猫娘（档2：猫娘会回应）")
        except Exception as exc:
            self.logger.warning(f"[塔罗牌] 推送通知失败: {exc}")

    async def _do_reading(self, spread_type: str, question: str = "") -> dict:
        """执行占卜"""
        reading = _build_reading(spread_type, question)
        self._reading_count += 1
        self._readings.append(reading)
        await self._save_state()
        await self._notify_catgirl(reading)
        return reading

    @lifecycle(id="startup")
    async def on_start(self, **_):
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        await self._load_state()
        self.register_static_ui("static")
        self.logger.info("TarotReaderPlugin 已启动！Web UI: http://127.0.0.1:48916/plugin/tarot/ui/")
        return Ok("塔罗牌占卜插件已启动")

    @lifecycle(id="shutdown")
    async def on_shutdown(self, **_):
        await self._save_state()
        self.logger.info("TarotReaderPlugin 已停止！")
        return Ok("塔罗牌占卜插件已停止")

    @plugin_entry(
        id="daily_reading",
        name="每日占卜",
        description="抽取一张塔罗牌，获得今日运势指引",
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "default": ""},
            },
        },
        llm_result_fields=["cards", "advice", "lucky"],
    )
    async def daily_reading(self, question: str = "", **_):
        self.logger.info(f"[每日占卜] 问题: {question or '无'}")
        reading = await self._do_reading("single", question)
        return Ok({
            "success": True,
            "data": {
                "reading": reading,
                "reading_count": self._reading_count,
            }
        })

    @plugin_entry(
        id="three_card_reading",
        name="三牌阵占卜",
        description="过去、现在、未来三牌阵，解析命运轨迹",
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "default": ""},
            },
        },
        llm_result_fields=["cards", "advice"],
    )
    async def three_card_reading(self, question: str = "", **_):
        self.logger.info(f"[三牌阵] 问题: {question or '无'}")
        reading = await self._do_reading("three_card", question)
        return Ok({
            "success": True,
            "data": {
                "reading": reading,
                "reading_count": self._reading_count,
            }
        })

    @plugin_entry(
        id="love_reading",
        name="爱情占卜",
        description="专属爱情牌阵，揭示感情密码",
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "default": ""},
            },
        },
        llm_result_fields=["cards", "advice"],
    )
    async def love_reading(self, question: str = "", **_):
        self.logger.info(f"[爱情占卜] 问题: {question or '无'}")
        reading = await self._do_reading("love", question)
        return Ok({
            "success": True,
            "data": {
                "reading": reading,
                "reading_count": self._reading_count,
            }
        })

    @plugin_entry(
        id="celtic_cross_reading",
        name="凯尔特十字占卜",
        description="全面的凯尔特十字牌阵，深度解析命运",
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "default": ""},
            },
        },
        llm_result_fields=["cards", "advice"],
    )
    async def celtic_cross_reading(self, question: str = "", **_):
        self.logger.info(f"[凯尔特十字] 问题: {question or '无'}")
        reading = await self._do_reading("celtic_cross", question)
        return Ok({
            "success": True,
            "data": {
                "reading": reading,
                "reading_count": self._reading_count,
            }
        })

    @plugin_entry(
        id="get_card_info",
        name="查询牌义",
        description="查询指定塔罗牌的含义和解释",
        input_schema={
            "type": "object",
            "properties": {
                "card_name": {"type": "string"},
            },
            "required": ["card_name"],
        },
        llm_result_fields=["card"],
    )
    async def get_card_info(self, card_name: str, **_):
        name = str(card_name or "").strip()
        if not name:
            return Err(SdkError("请提供塔罗牌名称"))

        found = None
        for card in _TAROT_CARDS:
            if card["name"] == name or card["name_en"].lower() == name.lower():
                found = card
                break

        if not found:
            available = [c["name"] for c in _TAROT_CARDS]
            return Err(SdkError(f"未找到牌 '{name}'。可选: {', '.join(available)}"))

        return Ok({
            "success": True,
            "data": {
                "card": found,
            }
        })

    @plugin_entry(
        id="list_all_cards",
        name="列出所有牌",
        description="获取全部22张大阿卡纳塔罗牌列表",
        llm_result_fields=["total"],
    )
    async def list_all_cards(self, **_):
        cards_list = []
        for card in _TAROT_CARDS:
            cards_list.append({
                "id": card["id"],
                "number": card["number"],
                "name": card["name"],
                "name_en": card["name_en"],
                "arcana": card["arcana"],
            })

        return Ok({
            "success": True,
            "data": {
                "cards": cards_list,
                "total": len(cards_list),
            }
        })

    @plugin_entry(
        id="get_history",
        name="占卜历史",
        description="获取最近的占卜记录",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
            },
        },
        llm_result_fields=["total"],
    )
    async def get_history(self, limit: int = 10, **_):
        limit = max(1, min(int(limit or 10), 50))
        recent = self._readings[-limit:]
        recent.reverse()

        return Ok({
            "success": True,
            "data": {
                "readings": recent,
                "total_count": self._reading_count,
            }
        })

    @plugin_entry(
        id="get_stats",
        name="统计信息",
        description="获取占卜统计信息",
        llm_result_fields=["reading_count"],
    )
    async def get_stats(self, **_):
        return Ok({
            "success": True,
            "data": {
                "reading_count": self._reading_count,
                "total_cards": len(_TAROT_CARDS),
                "spread_types": list(_SPREADS.keys()),
            }
        })

    BIRTHDAY_PROMPT = "我请求你担任中国传统的生辰八字算命的角色。我将会给你我的生日，请你根据我的生日推算命盘，分析五行属性、吉凶祸福、财运、婚姻、健康、事业等方面的情况，并为其提供相应的指导和建议。"

    @plugin_entry(
        id="birthday_divination",
        name="生辰八字",
        description="根据生辰八字，解读命运轨迹",
        input_schema={
            "type": "object",
            "properties": {
                "birthday": {"type": "string"},
            },
            "required": ["birthday"],
        },
        llm_result_fields=["result"],
    )
    async def birthday_divination(self, birthday: str, **_):
        self.logger.info(f"[生辰八字] 生日: {birthday}")
        result_text = f"我的生日是{birthday}。\n\n{self.BIRTHDAY_PROMPT}"
        self._reading_count += 1
        self._readings.append({"type": "birthday", "birthday": birthday, "result": result_text, "timestamp": _iso()})
        await self._save_state()
        await self._notify_catgirl_birthday(result_text)
        return Ok({"success": True, "data": {"result": result_text}})

    DREAM_PROMPT = "我请求你担任中国传统的周公解梦师的角色。我将会给你我的梦境，请你解释我的梦境，并为其提供相应的指导和建议。"

    @plugin_entry(
        id="dream_interpretation",
        name="周公解梦",
        description="解读梦境含义，探索潜意识的秘密",
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
            },
            "required": ["prompt"],
        },
        llm_result_fields=["result"],
    )
    async def dream_interpretation(self, prompt: str, **_):
        self.logger.info(f"[周公解梦] 梦境: {prompt}")
        if len(prompt) > 40:
            return Err(SdkError("梦境描述不能超过40字"))
        result_text = f"我的梦境是: {prompt}\n\n{self.DREAM_PROMPT}"
        self._reading_count += 1
        self._readings.append({"type": "dream", "prompt": prompt, "result": result_text, "timestamp": _iso()})
        await self._save_state()
        self._notify_catgirl_divination("周公解梦", prompt, result_text)
        return Ok({"success": True, "data": {"result": result_text}})

    NAME_PROMPT = "我请求你担任中国传统的姓名五格算命师的角色。我将会给你我的名字，请你根据我的名字推算，分析姓氏格、名字格、和自己格。并为其提供相应的指导和建议。"

    @plugin_entry(
        id="name_analysis",
        name="姓名五格",
        description="分析姓名五格，了解姓名对运势的影响",
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        },
        llm_result_fields=["result"],
    )
    async def name_analysis(self, name: str, **_):
        self.logger.info(f"[姓名五格] 姓名: {name}")
        if len(name) < 1 or len(name) > 10:
            return Err(SdkError("姓名长度必须在1-10个字之间"))
        result_text = f"我的名字是{name}。\n\n{self.NAME_PROMPT}"
        self._reading_count += 1
        self._readings.append({"type": "name", "name": name, "result": result_text, "timestamp": _iso()})
        await self._save_state()
        self._notify_catgirl_divination("姓名五格", name, result_text)
        return Ok({"success": True, "data": {"result": result_text}})

    NEW_NAME_PROMPT = "我请求你担任起名师的角色，我将会给你我的姓氏、生日、性别等，请返回你认为最适合我的名字，请注意姓氏在前，名字在后。"

    @plugin_entry(
        id="new_name_generation",
        name="起名取名",
        description="结合五行八字，起个好名字",
        input_schema={
            "type": "object",
            "properties": {
                "surname": {"type": "string"},
                "birthday": {"type": "string"},
                "sex": {"type": "string"},
                "prompt": {"type": "string", "default": ""},
            },
            "required": ["surname", "birthday", "sex"],
        },
        llm_result_fields=["result"],
    )
    async def new_name_generation(self, surname: str, birthday: str, sex: str, prompt: str = "", **_):
        self.logger.info(f"[起名取名] 姓氏: {surname}, 生日: {birthday}, 性别: {sex}")
        if not surname or not birthday or not sex:
            return Err(SdkError("起名参数错误"))
        if len(prompt) > 20:
            return Err(SdkError("其他要求不能超过20字"))
        req_text = f"姓氏是{surname}, 生日是{birthday}, 性别是{sex}"
        if prompt:
            req_text += f", 我的要求是: {prompt}"
        result_text = f"{req_text}\n\n{self.NEW_NAME_PROMPT}"
        self._reading_count += 1
        self._readings.append({"type": "new_name", "surname": surname, "birthday": birthday, "sex": sex, "result": result_text, "timestamp": _iso()})
        await self._save_state()
        self._notify_catgirl_divination("起名取名", f"{surname}姓{sex}宝宝", result_text)
        return Ok({"success": True, "data": {"result": result_text}})

    PLUM_FLOWER_PROMPT = "我请求你担任中国传统的梅花易数占卜师的角色。我会随意说出两个数，第一个数取为上卦，第二个数取为下卦。请你直接以数起卦, 并向我解释结果"

    @plugin_entry(
        id="plum_flower_divination",
        name="梅花易数",
        description="古老的占卜术，预测吉凶祸福",
        input_schema={
            "type": "object",
            "properties": {
                "num1": {"type": "integer"},
                "num2": {"type": "integer"},
            },
            "required": ["num1", "num2"],
        },
        llm_result_fields=["result"],
    )
    async def plum_flower_divination(self, num1: int, num2: int, **_):
        self.logger.info(f"[梅花易数] 数字: {num1}, {num2}")
        result_text = f"我选择的数字是: {num1} 和 {num2}\n\n{self.PLUM_FLOWER_PROMPT}"
        self._reading_count += 1
        self._readings.append({"type": "plum_flower", "num1": num1, "num2": num2, "result": result_text, "timestamp": _iso()})
        await self._save_state()
        self._notify_catgirl_divination("梅花易数", f"{num1}和{num2}", result_text)
        return Ok({"success": True, "data": {"result": result_text}})

    FATE_PROMPT = (
        "你是一个姻缘助手，我给你发两个人的名字，用逗号隔开，"
        "你来 随机说一下，这两个人之间的缘分如何？"
        "不需要很真实，只需要娱乐化的说一下即可，"
        "你可以根据人名先判断一下这个人名的真实性，"
        "如果输入是一些类似张三李四之类的，就返回不合适，"
        "或者如果两个人的名字性别，都是同性，也最好返回不合适。"
        "然后基本主要围绕, 90%的概率 说二人很合适, 然后10%的概率，"
        "说对方不合适，并列出为啥这样的原因。"
    )

    @plugin_entry(
        id="fate_divination",
        name="姻缘占卜",
        description="测试你与TA的缘分指数，探寻命中注定",
        input_schema={
            "type": "object",
            "properties": {
                "name1": {"type": "string"},
                "name2": {"type": "string"},
            },
            "required": ["name1", "name2"],
        },
        llm_result_fields=["result"],
    )
    async def fate_divination(self, name1: str, name2: str, **_):
        self.logger.info(f"[姻缘占卜] {name1} 和 {name2}")
        if len(name1) > 40 or len(name2) > 40:
            return Err(SdkError("名字不能超过40字"))
        result_text = f"{name1}, {name2}\n\n{self.FATE_PROMPT}"
        self._reading_count += 1
        self._readings.append({"type": "fate", "name1": name1, "name2": name2, "result": result_text, "timestamp": _iso()})
        await self._save_state()
        self._notify_catgirl_divination("姻缘占卜", f"{name1}和{name2}", result_text)
        return Ok({"success": True, "data": {"result": result_text}})

    async def _notify_catgirl_birthday(self, result: str) -> None:
        try:
            self.ctx.push_message(
                source="divination_master",
                ai_behavior="respond",
                parts=[{"type": "text", "text": f"主人刚刚做了生辰八字占卜，请帮他解读一下：\n\n{result}"}],
                priority=5,
            )
            self.logger.info("[生辰八字] 已推送给猫娘")
        except Exception as exc:
            self.logger.warning(f"[生辰八字] 推送失败: {exc}")

    async def _notify_catgirl_divination(self, div_type: str, prompt: str, result: str) -> None:
        try:
            self.ctx.push_message(
                source="divination_master",
                ai_behavior="respond",
                parts=[{"type": "text", "text": f"主人刚刚做了{div_type}占卜（{prompt}），请帮他解读一下：\n\n{result}"}],
                priority=5,
            )
            self.logger.info(f"[{div_type}] 已推送给猫娘")
        except Exception as exc:
            self.logger.warning(f"[{div_type}] 推送失败: {exc}")

    HOROSCOPE_PROMPT = "你是一个专业的星座运势解读助手，请根据以下星座信息，用诗意浪漫的语言为对方解读今日运势。"

    @plugin_entry(
        id="zodiac_horoscope",
        name="星座运势",
        description="每日星座运势查询，解析今日吉凶祸福",
        input_schema={
            "type": "object",
            "properties": {
                "sign": {"type": "string"},
            },
            "required": ["sign"],
        },
        llm_result_fields=["result"],
    )
    async def zodiac_horoscope(self, sign: str, **_):
        self.logger.info(f"[星座运势] 星座: {sign}")
        sign = sign.strip()
        if sign not in _ZODIAC_SIGNS:
            available = "、".join(_ZODIAC_SIGNS.keys())
            return Err(SdkError(f"未知星座 '{sign}'。可选: {available}"))

        zodiac_info = _ZODIAC_SIGNS[sign]
        today = datetime.now().strftime("%Y年%m月%d日")
        
        result_parts = [f"## {today} · {sign}运势", ""]
        result_parts.append(f"**日期范围**: {zodiac_info['dates']} | **属性**: {zodiac_info['element']}象星座 | **守护星**: {zodiac_info['ruling']}")
        result_parts.append(f"**性格特质**: {zodiac_info['traits']}")
        result_parts.append(f"**最佳配对**: {zodiac_info['compatibility']}")
        result_parts.append("")
        result_parts.append("---")
        result_parts.append("")

        for aspect in _ZODIAC_ASPECTS:
            rating = random.choice(_ZODIAC_RATINGS)
            advice = random.choice(_ZODIAC_ADVICE_POOL[aspect])
            result_parts.append(f"### {aspect} {rating}")
            result_parts.append(advice)
            result_parts.append("")

        lucky_color = random.choice(_LUCKY_ELEMENTS["colors"])
        lucky_number = random.choice(_LUCKY_ELEMENTS["numbers"])
        lucky_direction = random.choice(_LUCKY_ELEMENTS["directions"])
        result_parts.append(f"**幸运元素**")
        result_parts.append(f"- 幸运色: {lucky_color}")
        result_parts.append(f"- 幸运数字: {lucky_number}")
        result_parts.append(f"- 幸运方向: {lucky_direction}")

        result_text = "\n".join(result_parts)
        self._reading_count += 1
        self._readings.append({"type": "horoscope", "sign": sign, "result": result_text, "timestamp": _iso()})
        await self._save_state()
        await self._notify_catgirl_divination("星座运势", sign, result_text)
        return Ok({"success": True, "data": {"result": result_text}})

    @plugin_entry(
        id="fortune_stick",
        name="抽签占卜",
        description="虔诚求签，解读签文，预测吉凶",
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "default": ""},
                "lottery_type": {"type": "string", "default": "关帝灵签"},
            },
        },
        llm_result_fields=["result"],
    )
    async def fortune_stick(self, question: str = "", lottery_type: str = "关帝灵签", **_):
        self.logger.info(f"[抽签占卜] 问题: {question or '无'}, 类型: {lottery_type}")
        
        lottery_level = _weighted_draw_lottery()
        level_info = _LOTTERY_LEVELS[lottery_level]
        emoji = level_info["emoji"]
        
        poems = _LOTTERY_POEMS[lottery_level]
        poem = random.choice(poems)
        
        interpretations = _LOTTERY_INTERPRETATIONS[lottery_level]
        interpretation = random.choice(interpretations)
        
        stick_number = random.randint(1, 100)
        
        today = datetime.now().strftime("%Y年%m月%d日")
        result_parts = [f"## {emoji} {lottery_type} · 第{stick_number}签", ""]
        result_parts.append(f"**占卜日期**: {today}")
        if question:
            result_parts.append(f"**所求之事**: {question}")
        result_parts.append("")
        result_parts.append("---")
        result_parts.append("")
        result_parts.append(f"### {emoji} {lottery_level}")
        result_parts.append("")
        result_parts.append(f"> {poem}")
        result_parts.append("")
        result_parts.append("---")
        result_parts.append("")
        result_parts.append(f"### 📜 签文解读")
        result_parts.append(interpretation)
        result_parts.append("")
        
        if lottery_level in ["上上签", "上签"]:
            result_parts.append("### 💡 建议")
            result_parts.append("把握良机，积极行动。好运当前，但也要保持谦逊，不可骄傲自满。")
        elif lottery_level == "中签":
            result_parts.append("### 💡 建议")
            result_parts.append("保持平常心，稳扎稳打。不急不躁，等待时机成熟。")
        else:
            result_parts.append("### 💡 建议")
            result_parts.append("韬光养晦，静待转机。困难只是暂时的，调整心态，积蓄力量。")
        
        result_parts.append("")
        result_parts.append("---")
        result_parts.append("")
        result_parts.append("*心诚则灵，但命运始终掌握在自己手中。*")

        result_text = "\n".join(result_parts)
        self._reading_count += 1
        self._readings.append({"type": "fortune_stick", "question": question, "level": lottery_level, "stick_number": stick_number, "result": result_text, "timestamp": _iso()})
        await self._save_state()
        await self._notify_catgirl_divination("抽签占卜", question or "无问题", result_text)
        return Ok({"success": True, "data": {"result": result_text}})


def _weighted_draw_lottery() -> str:
    """根据权重随机抽取签等"""
    levels = list(_LOTTERY_LEVELS.keys())
    weights = [_LOTTERY_LEVELS[l]["weight"] for l in levels]
    return random.choices(levels, weights=weights, k=1)[0]
