# 🚀 AI 功能快速启动指南 (DeepSeek)

## 📦 第一步：无需安装额外依赖

DeepSeek 使用标准的 HTTP API，项目已经包含了 `requests` 库，无需额外安装！

## 🔑 第二步：获取 API Key（2 分钟）

### 1. 注册 DeepSeek
访问：https://platform.deepseek.com/signup

### 2. 获取 API Key
登录后访问：https://platform.deepseek.com/api_keys
点击 "创建 API Key"，复制生成的 key

### 3. 设置环境变量（Windows PowerShell）
```powershell
# 临时设置（当前终端有效）
$env:DEEPSEEK_API_KEY = "sk-your-key-here"

# 或永久设置（推荐）
[System.Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY', 'sk-your-key-here', 'User')
```

**注意**：永久设置需要重启终端

## ▶️ 第三步：启动服务

### 启动后端
```bash
cd GOmapping-backend
python manage.py runserver
```

### 启动前端（新终端）
```bash
cd GOmapping-frontend
npm run dev
```

## ✨ 第四步：使用 AI

1. 打开浏览器：http://localhost:5173
2. 进入 **GO Summary** 页面
3. 找到任意 **Duplicate Group**
4. 点击右上角 **"🤖 Ask AI"** 按钮
5. 等待 2-3 秒查看推荐！

## 🎯 效果展示

```
┌─────────────────────────────────────────────────────┐
│ ▼ Save The Children Group        100.0% similar    │
│   2 members | 50 instances                          │
│   ⭐ Recommended: #123 - ...      [🤖 Ask AI] ← 点这里│
└─────────────────────────────────────────────────────┘

点击后显示：

🤖 AI Analysis & Recommendation
┌──────────────────────────────────────────────────┐
│ 💡 Recommended to Keep:                          │
│ #123 - Save the Children International           │
│                                                   │
│ 📊 Key Factors:                                   │
│ ✓ 使用频率更高（50 vs 20 实例）                    │
│ ✓ 匹配已验证的知识库条目                           │
│ ✓ 国际范围优于区域变体                             │
│                                                   │
│ 🔍 Detailed Analysis:                            │
│ 应保留 Save the Children International...        │
└──────────────────────────────────────────────────┘
```

## 💰 费用说明

### DeepSeek 超便宜！
- 每次推荐成本：**约 ¥0.001（0.1 分）**
- 新用户赠送：**¥5 免费额度**
- 可免费使用：**约 5000 次推荐**

### 对比其他 AI
| AI 服务 | 每次成本 | 免费额度 |
|---------|----------|----------|
| DeepSeek | ¥0.001 | ¥5 |
| GPT-4 | ¥0.05 | 无 |
| Claude | ¥0.08 | 无 |

**DeepSeek 便宜 50-80 倍！** 🎉

## ⚡ 快速测试

启动服务后，在终端测试 API：

```bash
curl -X POST http://localhost:8000/api/ai-recommendation/ \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 1,
    "group_name": "Test Group",
    "members": [
      {
        "global_org_id": 1,
        "global_org_name": "UNHCR",
        "usage_count": 100,
        "is_recommended": true,
        "kb_match": true
      },
      {
        "global_org_id": 2,
        "global_org_name": "UNHCR International",
        "usage_count": 50,
        "is_recommended": false,
        "kb_match": false
      }
    ]
  }'
```

## ❌ 常见问题

### 问题 1：提示 API Key 未配置
```powershell
# 检查环境变量
echo $env:DEEPSEEK_API_KEY

# 如果为空，重新设置
$env:DEEPSEEK_API_KEY = "sk-your-key-here"

# 重启后端服务
```

### 问题 2：点击按钮没反应
- 检查浏览器控制台（F12）是否有错误
- 确保后端服务正在运行（http://localhost:8000）
- 检查网络是否可以访问 api.deepseek.com

### 问题 3：AI 返回错误
- 检查 API Key 是否正确
- 检查余额是否充足（新用户有 ¥5 免费额度）
- 查看后端终端的错误日志

## 📚 更多信息

- **详细配置**：查看 `AI_SETUP_GUIDE.md`
- **功能演示**：查看前端 `AI_FEATURE_DEMO.md`
- **DeepSeek 文档**：https://platform.deepseek.com/api-docs/

## 🎉 开始使用！

现在你已经准备好了！去 GO Summary 页面体验 AI 推荐功能吧！

**记住：每次推荐只要 0.1 分钱，放心使用！** 💰
