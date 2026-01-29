# 🤖 AI 推荐功能配置指南 (DeepSeek)

## 📋 概述

本系统集成了 DeepSeek AI，可以智能分析重复的 Global Organizations 并推荐应该保留哪一个。

**为什么选择 DeepSeek？**
- ✅ 价格更便宜（比 GPT-4 便宜 90%+）
- ✅ 国内访问稳定
- ✅ 支持中文和英文
- ✅ 性能优秀

## 🔑 获取 DeepSeek API Key

### Step 1: 注册账号
访问 [DeepSeek 官网](https://platform.deepseek.com/)，注册账号

### Step 2: 获取 API Key
1. 登录后进入 [API Keys 页面](https://platform.deepseek.com/api_keys)
2. 点击 "创建 API Key"
3. 复制生成的 API Key（格式：`sk-xxxxxxxxxxxxxxxxxxxxxxxx`）

### Step 3: 充值（可选）
- DeepSeek 新用户有免费额度
- 如需更多额度，可以在 [充值页面](https://platform.deepseek.com/top_up) 充值
- 价格参考：
  - DeepSeek-Chat: ¥1/百万tokens（输入），¥2/百万tokens（输出）
  - 每次推荐约消耗 500-1000 tokens，成本不到 ¥0.01

## ⚙️ 配置步骤

### Windows 配置（PowerShell）

#### 方法 1：临时设置（当前终端有效）
```powershell
$env:DEEPSEEK_API_KEY = "sk-your-actual-key-here"
```

#### 方法 2：永久设置（推荐）
```powershell
# 设置用户级环境变量
[System.Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-your-actual-key-here', 'User')

# 需要重启终端使其生效
```

### 验证配置

```powershell
# 检查环境变量是否设置成功
echo $env:DEEPSEEK_API_KEY
```

## 🚀 使用方法

### 1. 启动后端服务

```bash
cd GOmapping-backend
python manage.py runserver
```

### 2. 启动前端服务

```bash
cd GOmapping-frontend
npm run dev
```

### 3. 使用 AI 推荐

1. 打开 GO Summary 页面
2. 找到任意 Duplicate Group
3. 点击该组右上角的 **"🤖 Ask AI"** 按钮
4. 等待 AI 分析（通常 2-3 秒）
5. 查看 AI 的推荐结果和详细分析

## 📊 AI 分析考虑的因素

AI 会基于以下因素进行分析并推荐：

1. **标准化程度** - 名称是否符合官方标准格式
2. **使用频率** - 使用次数越多越可信
3. **知识库匹配** - 是否匹配已验证的组织
4. **名称完整性** - 完整官方名称优于缩写或地区变体
5. **地理范围** - 国际/全球版本优于特定国家版本

## 💰 费用说明

### DeepSeek 价格（人民币）
- **输入**: ¥1 / 百万 tokens
- **输出**: ¥2 / 百万 tokens

### 使用成本估算
- 每次 AI 推荐大约消耗：
  - 输入：400-600 tokens（约 ¥0.0005）
  - 输出：200-400 tokens（约 ¥0.0006）
  - **总成本：约 ¥0.001（0.1 分）**

### 新用户福利
- 注册即送 ¥5 免费额度
- 可以免费使用约 5000 次推荐

## 🔧 故障排查

### 问题：点击 "Ask AI" 后显示错误

**可能原因 1**：未配置 API Key
```
错误信息: "DEEPSEEK_API_KEY not configured"
解决方案: 按照上述步骤配置环境变量
```

**可能原因 2**：API Key 无效
```
错误信息: "DeepSeek API error: 401"
解决方案: 检查 API Key 是否正确，前往官网重新生成
```

**可能原因 3**：余额不足
```
错误信息: "DeepSeek API error: insufficient balance"
解决方案: 前往 DeepSeek 平台充值
```

**可能原因 4**：网络问题
```
错误信息: "Connection timeout"
解决方案: 检查网络连接，确保可以访问 api.deepseek.com
```

### 问题：环境变量设置后仍然无效

1. 确保重启了终端/命令行
2. 确保重启了后端服务（Django）
3. 使用 `echo $env:DEEPSEEK_API_KEY` 验证环境变量
4. 检查是否有拼写错误（是 `DEEPSEEK_API_KEY`，不是 `DEEPSEEK_API_KEY`）

## 📝 API 使用示例

### 请求格式

```json
POST http://localhost:8000/api/ai-recommendation/

{
  "group_id": 1,
  "group_name": "Save the Children Group",
  "members": [
    {
      "global_org_id": 123,
      "global_org_name": "Save the Children International",
      "usage_count": 50,
      "is_recommended": true,
      "kb_match": true
    },
    {
      "global_org_id": 124,
      "global_org_name": "Save the Children UK",
      "usage_count": 20,
      "is_recommended": false,
      "kb_match": false
    }
  ]
}
```

### 响应格式

```json
{
  "recommended_id": 123,
  "recommended_name": "Save the Children International",
  "reasoning": [
    "使用频率更高（50 vs 20 实例）",
    "匹配已验证的知识库条目",
    "国际范围优于区域变体"
  ],
  "analysis": "应保留 Save the Children International 作为主记录。它的使用频率明显更高（50个实例），匹配我们验证过的知识库，且代表国际组织而非特定国家分支。"
}
```

## 🎯 最佳实践

1. **选择性使用**：不是所有 duplicate group 都需要 AI 推荐，对于明显的重复可以直接判断
2. **验证结果**：AI 的推荐仅供参考，最终决策应结合业务知识
3. **缓存结果**：同一个组的 AI 推荐会被缓存，避免重复调用
4. **批量处理**：虽然成本很低，但建议按需使用，避免不必要的消耗

## 🆚 DeepSeek vs Claude 对比

| 特性 | DeepSeek | Claude |
|------|----------|--------|
| 价格 | ¥1-2/百万tokens | $3-15/百万tokens |
| 国内访问 | ✅ 稳定 | ⚠️ 需要特殊网络 |
| 响应速度 | 2-3秒 | 3-5秒 |
| 中文支持 | ✅ 优秀 | ✅ 良好 |
| API 兼容性 | OpenAI 格式 | 独立 API |
| 免费额度 | ¥5 | 无 |

## 🔗 相关链接

- [DeepSeek 官网](https://www.deepseek.com/)
- [DeepSeek 开放平台](https://platform.deepseek.com/)
- [API 文档](https://platform.deepseek.com/api-docs/)
- [价格说明](https://platform.deepseek.com/api-docs/pricing/)

## 📞 技术支持

如有问题，可以：
1. 查看 [DeepSeek 文档](https://platform.deepseek.com/api-docs/)
2. 联系 DeepSeek 客服（平台右下角）
3. 查看本项目的 `QUICK_START_AI.md`
