---
project: 朱雀投研智能体
register: product
aesthetic_direction: technical / utilitarian
color_strategy: restrained
design_system: Element Plus
design_variance: 6
motion_intensity: 3
visual_density: 7
---

# 朱雀投研设计语言

## Design Read

像一张正在工作的政策案卷台：可信、清醒、资料密集，但不压迫。

## Signature

**证据脊线**：政策研究页的提问、分析状态与结论共享一条青蓝色竖向基准线，像案卷装订线，也像研究证据的追踪路径。大胆只花在这一处，其余界面使用平面、克制的边界与排版。

### 地图页签名变体

**制图基准网格**：空间数据页可以把证据脊线延展为低对比度的经纬网格，并以青蓝色精确描边标记当前选择对象。网格只出现在地图主舞台，透明度不高于 12%；选中描边是地图页唯一高亮，不使用外发光、玻璃面板或装饰光斑。该变体与证据脊线共享颜色、线宽与技术制图语义，不构成第二套设计语言。

## 系统选择

继续使用现有 Element Plus 作为 Popover 等基础交互系统，主题绑定本规范令牌，不重做其行为模型。图标统一使用现有 `@lucide/vue`。

## Color（锁定）

| 角色 | OKLCH | Hex | 用途与对比 |
|---|---|---|---|
| background | 0.18 0.012 220 | `#20272A` | 页面底色 |
| surface | 0.215 0.013 220 | `#283034` | 工作栏、次级区域 |
| elevated | 0.255 0.014 220 | `#323B3F` | 输入框、浮层 |
| text | 0.95 0.008 210 | `#EEF2F1` | 正文，对 background 约 13:1 |
| muted | 0.72 0.012 215 | `#A8B3B3` | 说明，对 background 约 6.3:1 |
| subtle | 0.58 0.012 215 | `#7F8B8C` | 元数据，仅用于 12px 以上 |
| border | 0.36 0.014 215 | `#485458` | 分隔与输入边界 |
| accent | 0.76 0.125 205 | `#54C6D6` | 唯一品牌强调色，UI 对 background 超过 3:1 |
| success | 0.72 0.14 145 | `#66C48A` | 成功与在线 |
| warning | 0.78 0.13 80 | `#D9B35A` | 时效风险 |
| danger | 0.68 0.16 25 | `#E37A70` | 错误 |
| info | 0.76 0.125 205 | `#54C6D6` | 信息状态，复用 accent |

实现优先复用现有 `--xc-*` 语义令牌，政策页局部令牌映射到以上角色。禁止紫蓝渐变、渐变字、玻璃卡片、装饰光球。

## Type（锁定）

| 角色 | 字体 | 用途 | 说明 |
|---|---|---|---|
| display | `HarmonyOS Sans SC` 600 | 页面标题、结果标题 | 30-42px，字距 0 |
| body | `HarmonyOS Sans SC` 400/500 | 正文与控件 | 13-16px，阅读宽度 68ch |
| utility | `JetBrains Mono` | 日期、计数、状态、英文 | 11-12px，等宽数字 |

不新增网络字体，避免演示环境加载抖动。所有字距为 0，只有英文全大写工具标签允许 `0.04em`。

## Scales（锁定）

- spacing: `0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64`
- radius: `sm 4, md 8, lg 12, full 9999`；政策页主要使用 4 与 8
- motion: `fast 120ms, base 240ms, emphasis 420ms`
- easing: `cubic-bezier(0.16, 1, 0.3, 1)`
- breakpoint: `sm 640, lg 1024, xl 1280`
- shadow: 仅浮层和主提问区使用，其他区域靠边界和底色分层
- `prefers-reduced-motion` 下关闭位移和自动视觉过渡

## Voice

- register: 简洁、专业、以任务为中心
- action vocabulary: `新建提问`、`提交研究`、`正在分析`、`分析完成`
- 不使用营销词、虚假精确数字或教程式可见文案

## Cross-session consistency

后续页面工作必须先阅读本文件。任何超出令牌、字体、圆角或动效的值都需要显式更新本文件，不允许自然漂移。

地图、政策研究及后续业务页共享本文件的色彩、字体、间距、圆角、动效和 Element Plus 主题。页面差异只能来自与任务相关的 Signature 变体，不能引入独立配色或组件外观。

Every screen must read as the same product if placed side by side.
