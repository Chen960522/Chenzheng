# 简化的 Bedrock Knowledge Base 创建脚本

## 概述

这是一个根据 AWS Bedrock 官方文档最佳实践创建的简化脚本，让 Bedrock 自动管理所有底层资源。

## 与原脚本的区别

### 原脚本 (create_bedrock_knowledge_base.py)
- ❌ 手动创建 OpenSearch Serverless 集合
- ❌ 手动创建安全策略（加密、网络、数据访问）
- ❌ 手动创建 IAM 角色和策略
- ❌ 手动创建 OpenSearch 索引
- ❌ 复杂的权限配置
- ❌ 容易出错

### 新脚本 (create_kb_simple.py) ✅
- ✅ Bedrock 自动创建 OpenSearch 集合
- ✅ Bedrock 自动管理安全策略
- ✅ Bedrock 自动创建 IAM 角色
- ✅ Bedrock 自动创建索引
- ✅ 简单配置
- ✅ 更可靠

## 前置要求

### 1. 完成 S3 设置

```bash
python scripts/setup_knowledge_base_s3.py
```

### 2. 安装依赖

```bash
pip install boto3
```

### 3. 配置 AWS 凭证

```bash
aws configure
```

或设置环境变量：
```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-east-1
```

### 4. 启用 Bedrock 模型访问

在 AWS Console 中：
1. 打开 Amazon Bedrock 控制台
2. 导航到 "Model access"
3. 请求访问 Amazon Titan Embeddings v2

## 使用方法

### 基本用法

```bash
cd aws-pricing-assistant
python scripts/create_kb_simple.py
```

### 自定义配置

通过环境变量：
```bash
export AWS_REGION=ap-southeast-1
export S3_KNOWLEDGE_BASE_BUCKET=my-kb-bucket
python scripts/create_kb_simple.py
```

或通过 .env 文件：
```bash
AWS_REGION=us-east-1
S3_KNOWLEDGE_BASE_BUCKET=aws-pricing-assistant-kb-data
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
```

## 脚本执行流程

### 1. 创建 Knowledge Base
- Bedrock 自动创建 OpenSearch Serverless 集合
- Bedrock 自动创建 IAM 服务角色
- Bedrock 自动配置所有安全策略
- 等待 Knowledge Base 变为 ACTIVE 状态

### 2. 创建数据源
- 配置 S3 作为数据源
- 设置分块策略（512 tokens，20% 重叠）

### 3. 启动数据摄取
- 开始索引 S3 中的文档
- 监控摄取进度
- 显示处理统计信息

## 输出示例

```
======================================================================
AWS Pricing Assistant - Bedrock Knowledge Base Setup (Simplified)
======================================================================

Configuration:
  AWS Region: us-east-1
  S3 Bucket: aws-pricing-assistant-kb-data
  Embedding Model: amazon.titan-embed-text-v2:0

AWS Identity:
  Account: 123456789012
  User/Role: admin

⚠️  This script will:
  - Create a Bedrock Knowledge Base
  - Auto-create OpenSearch Serverless collection (managed by Bedrock)
  - Auto-create IAM service role (managed by Bedrock)
  - Create S3 data source
  - Start data ingestion

💰 Estimated cost: $50-100/month for OpenSearch Serverless

Continue? (yes/no): yes

Starting setup...

2024-12-25 10:00:00 - INFO - Creating Knowledge Base...
2024-12-25 10:00:05 - INFO - ✅ Knowledge Base created: KB123ABC
2024-12-25 10:00:05 - INFO -    ARN: arn:aws:bedrock:us-east-1:123456789012:knowledge-base/KB123ABC
2024-12-25 10:00:05 - INFO -    Service Role: arn:aws:iam::123456789012:role/AmazonBedrockExecutionRoleForKnowledgeBase_KB123ABC
2024-12-25 10:00:05 - INFO - Waiting for Knowledge Base to be ready...
2024-12-25 10:00:15 - INFO -    Status: CREATING, waiting... (10s)
2024-12-25 10:00:25 - INFO - ✅ Knowledge Base is ACTIVE

2024-12-25 10:00:26 - INFO - Creating S3 data source...
2024-12-25 10:00:27 - INFO - ✅ Data source created: DS456DEF

2024-12-25 10:00:28 - INFO - Starting data ingestion...
2024-12-25 10:00:29 - INFO - ✅ Ingestion job started: JOB789GHI
2024-12-25 10:00:29 - INFO - Monitoring ingestion progress...
2024-12-25 10:00:44 - INFO -    Status: IN_PROGRESS, waiting... (15s)
2024-12-25 10:05:00 - INFO - ✅ Ingestion completed successfully
2024-12-25 10:05:00 - INFO -    Documents processed: 17
2024-12-25 10:05:00 - INFO -    Documents indexed: 17

======================================================================
✅ Setup completed successfully!
======================================================================

Knowledge Base ID: KB123ABC
Data Source ID: DS456DEF
Ingestion Job ID: JOB789GHI

Next steps:
1. Update .env file:
   BEDROCK_KNOWLEDGE_BASE_ID=KB123ABC
2. Test Knowledge Base queries
3. Integrate with your application
```

## 优势

### 1. 简单可靠
- 只需 3 个 API 调用
- Bedrock 处理所有复杂配置
- 遵循 AWS 最佳实践

### 2. 自动管理
- OpenSearch 集合由 Bedrock 管理
- IAM 角色由 Bedrock 管理
- 安全策略由 Bedrock 管理
- 索引由 Bedrock 管理

### 3. 更少错误
- 无需手动配置安全策略
- 无需担心权限问题
- 无需手动创建索引
- 无需处理策略名称长度限制

### 4. 易于维护
- Bedrock 自动更新配置
- 无需手动管理资源
- 简化的故障排除

## 成本估算

### OpenSearch Serverless（Bedrock 管理）
- OCU (OpenSearch Compute Units): 按小时计费
- 存储: 按 GB/月计费
- 估算: $50-100/月

### Bedrock Knowledge Base
- 数据摄取: 按文档数量计费
- 查询: 按请求数量计费
- 估算: $10-50/月

**总计**: 约 $60-150/月

## 故障排除

### 错误: 模型访问未启用

**解决方案**:
1. 打开 Amazon Bedrock 控制台
2. 导航到 "Model access"
3. 请求访问 Amazon Titan Embeddings v2

### 错误: S3 存储桶不存在

**解决方案**:
```bash
python scripts/setup_knowledge_base_s3.py
```

### 错误: 权限不足

**所需权限**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateKnowledgeBase",
        "bedrock:CreateDataSource",
        "bedrock:StartIngestionJob",
        "bedrock:GetKnowledgeBase",
        "bedrock:GetIngestionJob",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "aoss:CreateCollection",
        "aoss:CreateSecurityPolicy",
        "aoss:CreateAccessPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

## 清理资源

如果需要删除创建的资源：

### 1. 删除 Knowledge Base

```bash
aws bedrock-agent delete-knowledge-base \
  --knowledge-base-id KB123ABC \
  --region us-east-1
```

这会自动删除：
- OpenSearch Serverless 集合
- IAM 服务角色
- 所有安全策略

## 与原脚本对比

| 功能 | 原脚本 | 新脚本 |
|------|--------|--------|
| 代码行数 | ~600 行 | ~300 行 |
| API 调用 | ~15 次 | 3 次 |
| 手动配置 | 多 | 少 |
| 错误概率 | 高 | 低 |
| 维护成本 | 高 | 低 |
| 推荐使用 | ❌ | ✅ |

## 推荐

**强烈推荐使用这个简化脚本**，除非你有特殊需求需要完全控制所有资源配置。

## 相关文档

- [AWS Bedrock Knowledge Base 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-create.html)
- [S3 设置脚本文档](./README_SETUP_KB_S3.md)
- [项目部署指南](../docs/部署指南.md)
