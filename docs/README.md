# AWS智能定价助手 - 文档中心

欢迎来到AWS智能定价助手文档中心！这里包含了所有您需要的文档。

---

## 📖 文档导航

### 🚀 部署文档（推荐从这里开始）

| 文档 | 描述 | 适合人群 |
|------|------|----------|
| **[部署说明](../部署说明.md)** | 部署入口文档，帮助您选择合适的部署方式 | 所有用户 |
| **[快速部署检查清单](快速部署检查清单.md)** | 逐步部署指导，包含所有步骤的详细说明 | 新手用户 |
| **[部署指南（中文）](部署指南.md)** | 完整的部署指南，包含详细说明和故障排除 | 所有用户 |
| **[Deployment Guide (English)](DEPLOYMENT_GUIDE.md)** | Complete deployment guide in English | English speakers |

### 🔧 配置和维护

| 文档 | 描述 |
|------|------|
| **[配置说明](CONFIGURATION.md)** | 环境变量、AWS服务配置详解 |
| **[故障排除](TROUBLESHOOTING.md)** | 常见问题和解决方案 |
| **[开发文档](DEVELOPMENT.md)** | 本地开发环境设置 |

### 📋 项目文档

| 文档 | 描述 |
|------|------|
| **[项目结构](../PROJECT_STRUCTURE.md)** | 代码组织和目录结构 |
| **[项目完成总结](../PROJECT_COMPLETION_SUMMARY.md)** | 开发状态和已完成功能 |
| **[生产就绪检查清单](../PRODUCTION_READINESS_CHECKLIST.md)** | 部署前检查清单 |
| **[快速开始](../QUICKSTART.md)** | 快速开始指南 |

---

## 🎯 根据您的需求选择文档

### 我想快速部署

1. 阅读 **[部署说明](../部署说明.md)**
2. 运行一键部署脚本：
   ```bash
   ./一键部署.sh  # Linux/Mac
   # 或
   一键部署.bat   # Windows
   ```

### 我想了解每个步骤

1. 打开 **[快速部署检查清单](快速部署检查清单.md)**
2. 按照检查清单逐步操作

### 我想深入了解部署细节

1. 阅读 **[部署指南](部署指南.md)**
2. 参考 **[配置说明](CONFIGURATION.md)**

### 我遇到了问题

1. 查看 **[故障排除](TROUBLESHOOTING.md)**
2. 检查日志和错误信息
3. 参考部署指南中的故障排除部分

### 我想进行本地开发

1. 阅读 **[开发文档](DEVELOPMENT.md)**
2. 参考 **[配置说明](CONFIGURATION.md)**
3. 查看 **[项目结构](../PROJECT_STRUCTURE.md)**

---

## 📚 文档层次结构

```
docs/
├── README.md                      # 本文件 - 文档导航
├── 部署指南.md                    # 完整部署指南（中文）
├── 快速部署检查清单.md            # 部署检查清单（中文）
├── DEPLOYMENT_GUIDE.md            # Deployment guide (English)
├── CONFIGURATION.md               # 配置说明
├── TROUBLESHOOTING.md             # 故障排除
└── DEVELOPMENT.md                 # 开发文档

根目录/
├── 部署说明.md                    # 部署入口文档
├── 一键部署.sh                    # Linux/Mac一键部署脚本
├── 一键部署.bat                   # Windows一键部署脚本
├── README.md                      # 项目主README
├── PROJECT_STRUCTURE.md           # 项目结构
├── PROJECT_COMPLETION_SUMMARY.md  # 项目完成总结
├── PRODUCTION_READINESS_CHECKLIST.md  # 生产就绪检查清单
└── QUICKSTART.md                  # 快速开始
```

---

## 🔍 快速查找

### 部署相关
- **如何开始部署？** → [部署说明](../部署说明.md)
- **部署需要多长时间？** → 约30-40分钟
- **部署需要什么前置条件？** → [部署指南 - 前置要求](部署指南.md#前置要求)
- **如何验证部署成功？** → [快速部署检查清单 - 部署验证](快速部署检查清单.md#部署验证)

### 配置相关
- **如何配置环境变量？** → [配置说明](CONFIGURATION.md)
- **如何生成安全密钥？** → [部署指南 - 配置说明](部署指南.md#配置说明)
- **如何配置Bedrock？** → [配置说明 - Bedrock配置](CONFIGURATION.md)

### 故障排除
- **Bedrock访问被拒绝？** → [故障排除 - Bedrock问题](TROUBLESHOOTING.md)
- **DynamoDB表已存在？** → [故障排除 - DynamoDB问题](TROUBLESHOOTING.md)
- **前端无法加载？** → [故障排除 - 前端问题](TROUBLESHOOTING.md)

### 开发相关
- **如何设置本地开发环境？** → [开发文档](DEVELOPMENT.md)
- **项目代码如何组织？** → [项目结构](../PROJECT_STRUCTURE.md)
- **如何运行测试？** → [开发文档 - 测试](DEVELOPMENT.md)

---

## 💡 文档使用建议

### 首次部署用户
1. 📖 阅读 [部署说明](../部署说明.md)（5分钟）
2. ✅ 准备前置条件（10分钟）
3. 🚀 运行一键部署（30-40分钟）
4. ✓ 验证部署成功（5分钟）

### 有经验的用户
1. 📋 查看 [快速部署检查清单](快速部署检查清单.md)
2. 🔧 根据需要自定义配置
3. 🚀 手动执行部署步骤

### 开发人员
1. 💻 阅读 [开发文档](DEVELOPMENT.md)
2. 📂 了解 [项目结构](../PROJECT_STRUCTURE.md)
3. 🧪 运行测试和开发

---

## 📞 获取帮助

如果您在文档中找不到答案：

1. **检查故障排除文档** - [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. **查看项目日志** - CloudWatch Logs
3. **联系支持团队** - 在项目仓库提交issue
4. **AWS支持** - https://console.aws.amazon.com/support/

---

## 🔄 文档更新

本文档会持续更新。如果您发现任何问题或有改进建议，欢迎：

- 📝 提交issue
- 🔧 提交pull request
- 💬 联系维护团队

---

## ⭐ 推荐阅读顺序

### 对于部署人员
1. [部署说明](../部署说明.md)
2. [快速部署检查清单](快速部署检查清单.md)
3. [配置说明](CONFIGURATION.md)
4. [故障排除](TROUBLESHOOTING.md)

### 对于开发人员
1. [开发文档](DEVELOPMENT.md)
2. [项目结构](../PROJECT_STRUCTURE.md)
3. [配置说明](CONFIGURATION.md)
4. [部署指南](部署指南.md)

### 对于管理员
1. [项目完成总结](../PROJECT_COMPLETION_SUMMARY.md)
2. [生产就绪检查清单](../PRODUCTION_READINESS_CHECKLIST.md)
3. [部署指南](部署指南.md)
4. [配置说明](CONFIGURATION.md)

---

**文档版本**: 1.0  
**最后更新**: 2024年12月23日  
**维护者**: AWS智能定价助手团队
