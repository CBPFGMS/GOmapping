# 🤖 AI 推荐功能演示 (DeepSeek)

## 🎯 功能概览

在每个 Duplicate Group 右上角新增了 **"Ask AI"** 按钮，点击后 DeepSeek AI 会智能分析该组内所有成员，推荐应该保留哪一个 Global Organization。

**为什么选择 DeepSeek？**
- 💰 **超级便宜** - 每次推荐只要 0.1 分钱
- 🚀 **响应快速** - 2-3 秒完成分析
- 🇨🇳 **国内稳定** - 无需特殊网络
- 🎁 **免费额度** - 新用户赠送 ¥5

## 📸 界面展示

### 1. 初始状态 - Ask AI 按钮
```
┌──────────────────────────────────────────────────────┐
│ ▼ Save The Children Group          100.0% similar   │
│   2 members | 50 instances                           │
│   ⭐ Recommended: #123 - Save...        [🤖 Ask AI] │ ← 点击这里
└──────────────────────────────────────────────────────┘
```

### 2. 加载状态（2-3秒）
```
┌──────────────────────────────────────────────────────┐
│ ▼ Save The Children Group          100.0% similar   │
│   2 members | 50 instances                           │
│   ⭐ Recommended: #123 - Save...  [🤔 AI Thinking...]│ ← AI 分析中
└──────────────────────────────────────────────────────┘
```

### 3. 结果显示
```
┌─────────────────────────────────────────────────────┐
│ ▼ Save The Children Group        100.0% similar    │
│   2 members | 50 instances                          │
│   ⭐ Recommended: #123 - ...    [✨ View AI Insight]│ ← 已有结果
├─────────────────────────────────────────────────────┤
│ 🤖 AI Analysis & Recommendation                     │
│ ┌───────────────────────────────────────────────┐  │
│ │ 💡 Recommended to Keep:                       │  │
│ │ #123 - Save the Children International        │  │
│ │                                                │  │
│ │ 📊 Key Factors:                                │  │
│ │ ✓ 使用频率显著更高（50 vs 20 实例）            │  │
│ │ ✓ 匹配已验证的知识库条目                       │  │
│ │ ✓ 国际组织优于区域分支                         │  │
│ │                                                │  │
│ │ 🔍 Detailed Analysis:                         │  │
│ │ 建议保留 Save the Children International      │  │
│ │ 作为主记录。它的使用频率明显更高（50个        │  │
│ │ 实例 vs 20个），匹配我们验证过的知识库...     │  │
│ └───────────────────────────────────────────────┘  │
│                                                     │
│ Tree Structure:                                     │
│ ⭐ KEEP  #123  Save the Children International      │
│   └─ #1001  Partner Org 1              [95%]       │
│   └─ #1002  Partner Org 2              [88%]       │
│   └─ ... and 48 more                                │
│                                                     │
│ MERGE  #124  Save the Children UK                   │
│   └─ #2001  Partner Org 3              [92%]       │
│   └─ ... and 18 more                                │
└─────────────────────────────────────────────────────┘
```

## 🎨 设计特点

### 按钮状态
- **🤖 Ask AI** - 初始状态，蓝紫色渐变
- **🤔 AI Thinking...** - 加载中，脉冲动画
- **✨ View AI Insight** - 已有结果，绿色渐变

### 推荐面板
- **渐变背景** - 淡蓝色渐变，清新舒适
- **清晰分区** - 推荐、理由、分析三个部分
- **图标引导** - 💡 推荐、📊 因素、🔍 分析
- **绿色勾选** - ✓ 每个理由前的勾选标记

### 动画效果
- 按钮悬停：向上浮动 + 阴影增强
- 加载状态：脉冲动画
- 面板展开：淡入动画

## 💡 使用场景

### ✅ 推荐使用 AI 的情况

1. **使用频率相近**
   ```
   ├─ UNHCR (45 instances)
   └─ UNHCR International (42 instances)
   ```
   难以判断哪个更标准

2. **名称变体复杂**
   ```
   ├─ International Rescue Committee
   ├─ IRC International
   ├─ IRC
   └─ The International Rescue Committee
   ```
   有多种写法，需要专业判断

3. **新手使用**
   对人道主义组织不熟悉，需要智能建议

4. **存在争议**
   团队成员对应该保留哪个有不同意见

### ⚠️ 不需要 AI 的情况

1. **明显的重复**
   ```
   ├─ UNHCR (100 instances)
   └─ UNHCR (duplicate) (2 instances)
   ```
   一眼就能看出应该保留哪个

2. **已有经验**
   对该组织非常熟悉，知道标准名称

3. **系统推荐明确**
   算法推荐已经很明确，无需额外确认

## 🧠 AI 分析逻辑

### 1. 标准化程度（权重：30%）
- 是否符合国际组织标准命名格式
- 是否包含不必要的地理标识
- 是否使用完整正式名称

### 2. 使用频率（权重：25%）
- 使用次数越多，越可能是标准名称
- 大量使用表明业界认可度高

### 3. 知识库匹配（权重：20%）
- 是否匹配系统内置的标准组织库
- 已验证的组织优先级更高

### 4. 名称完整性（权重：15%）
- 完整名称 > 缩写
- 正式名称 > 昵称/俗称

### 5. 地理范围（权重：10%）
- 国际组织 > 区域组织
- 总部 > 分支机构

## 💰 费用优化

### 智能缓存机制
```javascript
// 前端缓存 AI 结果
const [aiRecommendations, setAiRecommendations] = useState({});

// 同一个组不会重复调用
if (aiRecommendations[group_id]) {
  return; // 直接显示缓存结果
}
```

### 按需调用
- ✅ 只有点击按钮才调用 AI
- ✅ 不会在页面加载时自动调用
- ✅ 用户完全控制何时使用

### 成本对比

| 场景 | 每次成本 | 100次成本 | 1000次成本 |
|------|----------|-----------|------------|
| DeepSeek | ¥0.001 | ¥0.1 | ¥1 |
| GPT-4 | ¥0.05 | ¥5 | ¥50 |
| Claude | ¥0.08 | ¥8 | ¥80 |

**DeepSeek 便宜 50-80 倍！** 即使分析 1000 个组，也只要 1 元钱！

## 🔒 隐私与安全

### 发送的数据
AI 仅接收：
- ✅ 组织 ID（数字）
- ✅ 组织名称（文本）
- ✅ 使用次数（数字）
- ✅ 是否匹配知识库（布尔值）

### 不会发送
- ❌ 项目详细信息
- ❌ 资金数据
- ❌ 敏感的合作伙伴信息
- ❌ 个人身份信息

### 数据安全
- 所有通信通过 HTTPS 加密
- DeepSeek 不会存储或训练用户数据
- 符合数据保护要求

## 🎯 使用建议

### 最佳实践

1. **先查看系统推荐**
   系统算法推荐（⭐ KEEP 标记）已经考虑了使用频率和知识库匹配

2. **对不确定的组使用 AI**
   当系统推荐不够明确时，使用 AI 获取第二意见

3. **结合业务知识**
   AI 推荐仅供参考，最终决策应结合实际业务需求

4. **批量分析**
   虽然成本很低，但建议重点分析高优先级的 duplicate groups

### 工作流程建议

```
1. 查看 Duplicate Groups 列表
   ↓
2. 对于明显的重复，直接处理
   ↓
3. 对于不确定的，点击 "Ask AI"
   ↓
4. 查看 AI 分析和理由
   ↓
5. 结合业务知识做最终决策
   ↓
6. 执行合并操作
```

## 📊 效果示例

### 示例 1：国际组织 vs 区域分支

**输入：**
```json
{
  "members": [
    {
      "id": 123,
      "name": "Save the Children International",
      "usage": 50,
      "kb_match": true
    },
    {
      "id": 124,
      "name": "Save the Children UK",
      "usage": 20,
      "kb_match": false
    }
  ]
}
```

**AI 推荐：**
```
💡 Keep: #123 - Save the Children International

📊 Reasons:
✓ Higher usage frequency (50 vs 20)
✓ Matches knowledge base
✓ International scope preferred

🔍 Analysis:
Save the Children International represents 
the global organization and should be kept...
```

### 示例 2：完整名称 vs 缩写

**输入：**
```json
{
  "members": [
    {
      "id": 456,
      "name": "IRC",
      "usage": 30,
      "kb_match": false
    },
    {
      "id": 457,
      "name": "International Rescue Committee",
      "usage": 35,
      "kb_match": true
    }
  ]
}
```

**AI 推荐：**
```
💡 Keep: #457 - International Rescue Committee

📊 Reasons:
✓ Full official name vs abbreviation
✓ Matches verified knowledge base
✓ Slightly higher usage (35 vs 30)

🔍 Analysis:
The complete name should be retained as the
master record for clarity and standardization...
```

## 🚀 开始使用

1. **配置 API Key** - 查看 `QUICK_START_AI.md`
2. **启动服务** - 后端 + 前端
3. **打开页面** - GO Summary
4. **点击按钮** - 🤖 Ask AI
5. **查看推荐** - 智能分析结果

**每次只要 0.1 分钱，放心使用！** 💰✨
