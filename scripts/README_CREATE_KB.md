# Bedrock Knowledge Base Creation Script

## 概述

`create_bedrock_knowledge_base.py` 脚本用于自动创建和配置 Amazon Bedrock Knowledge Base，包括 OpenSearch Serverless 集合、IAM 角色、数据源和数据同步。

## Python 版本兼容性

- ✅ Python 3.12+
- ✅ Python 3.13
- ✅ Python 3.14 (已优化)

此脚本已优化为独立运行，不依赖项目的其他模块。

## 前置要求

### 1. 完成 S3 设置

在运行此脚本之前，必须先运行 S3 设置脚本：

```bash
python scripts/setup_knowledge_base_s3.py
```

### 2. 安装依赖

```bash
pip install boto3 opensearch-py requests-aws4auth
```

或者安装完整的项目依赖：

```bash
cd aws-pricing-assistant
pip install -r requirements.txt
```

### 3. 配置 AWS 凭证

需要具有以下权限的 AWS 凭证：

- IAM 角色创建和管理
- OpenSearch Serverless 管理
- Bedrock Knowledge Base 管理
- S3 访问权限

配置方式（选择一种）：

#### 方式 A: AWS CLI
```bash
aws configure
```

#### 方式 B: 环境变量
```bash
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-east-1
```

#### 方式 C: .env 文件
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_KNOWLEDGE_BASE_BUCKET=aws-pricing-assistant-kb-data
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
```

### 4. 确认 Bedrock 模型访问

在 AWS Console 中启用 Bedrock 模型访问：

1. 打开 Amazon Bedrock 控制台
2. 导航到 "Model access"
3. 请求访问以下模型：
   - Amazon Titan Embeddings G1 - Text v2.0
   - Anthropic Claude 3.5 Sonnet

## 使用方法

### 基本用法

```bash
cd aws-pricing-assistant
python scripts/create_bedrock_knowledge_base.py
```

脚本会提示确认后再创建资源。

### 自定义配置

通过环境变量自定义：

```bash
export AWS_REGION=ap-southeast-1
export S3_KNOWLEDGE_BASE_BUCKET=my-kb-bucket
export BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
python scripts/create_bedrock_knowledge_base.py
```

## 脚本功能

### 1. 创建 IAM 角色

创建名为 `AWSPricingAssistantKBRole` 的 IAM 角色，包含以下权限：

- **Bedrock 权限**: 调用嵌入模型
- **S3 权限**: 读取知识库数据
- **OpenSearch 权限**: 访问向量存储

### 2. 创建 OpenSearch Serverless 安全策略

在创建集合之前，必须先创建三种安全策略：

#### 加密策略 (Encryption Policy)
- 策略名称: `aws-pricing-kb-encrypt` (≤32 字符)
- 使用 AWS 托管密钥加密数据

#### 网络策略 (Network Policy)
- 策略名称: `aws-pricing-kb-network` (≤32 字符)
- 允许公共访问（可根据需要调整为 VPC 访问）

#### 数据访问策略 (Data Access Policy)
- 策略名称: `aws-pricing-kb-data` (≤32 字符)
- 授予 IAM 角色对集合和索引的完整访问权限

### 3. 创建 OpenSearch Serverless 集合

### 3. 创建 OpenSearch Serverless 集合

- 集合名称: `aws-pricing-kb-collection`
- 类型: VECTORSEARCH
- 用途: 存储文档向量嵌入

等待时间: 约 3-5 分钟

### 4. 创建 Knowledge Base

### 4. 创建 Knowledge Base

- 名称: `aws-pricing-assistant-kb`
- 向量索引: `aws-pricing-kb-index`
- 嵌入模型: Amazon Titan Embeddings v2
- 字段映射:
  - `embedding`: 向量字段
  - `text`: 文本字段
  - `metadata`: 元数据字段

### 5. 配置 S3 数据源

### 5. 配置 S3 数据源

- 数据源类型: S3
- 分块策略: 固定大小
- 最大 Token 数: 512
- 重叠百分比: 20%

### 6. 启动数据同步

自动启动数据摄取作业，将 S3 中的文档索引到 Knowledge Base。

等待时间: 约 5-10 分钟（取决于数据量）

## 输出示例

```
============================================================
AWS Pricing Assistant - Bedrock Knowledge Base Setup
============================================================

Configuration:
  AWS Region: us-east-1
  S3 Bucket: aws-pricing-assistant-kb-data
  Embedding Model: amazon.titan-embed-text-v2:0

AWS Identity:
  Account: 123456789012
  User/Role: admin

⚠️  This script will create the following AWS resources:
  - IAM Role (AWSPricingAssistantKBRole)
  - OpenSearch Serverless Collection
  - Bedrock Knowledge Base
  - S3 Data Source

These resources may incur AWS charges.

Do you want to proceed? (yes/no): yes

Starting setup...

2024-12-25 10:30:00 - __main__ - INFO - Starting Bedrock Knowledge Base setup...
2024-12-25 10:30:01 - __main__ - INFO - Created IAM role: arn:aws:iam::123456789012:role/AWSPricingAssistantKBRole
2024-12-25 10:30:02 - __main__ - INFO - Attached policy: KBBedrockPolicy
2024-12-25 10:30:03 - __main__ - INFO - Attached policy: KBS3Policy
2024-12-25 10:30:04 - __main__ - INFO - Attached policy: KBOpenSearchPolicy
2024-12-25 10:30:15 - __main__ - INFO - Creating OpenSearch Serverless security policies...
2024-12-25 10:30:16 - __main__ - INFO - Created encryption policy: aws-pricing-kb-encrypt
2024-12-25 10:30:17 - __main__ - INFO - Created network policy: aws-pricing-kb-network
2024-12-25 10:30:18 - __main__ - INFO - Created data access policy: aws-pricing-kb-data
2024-12-25 10:30:23 - __main__ - INFO - Creating OpenSearch collection: abc123
2024-12-25 10:33:00 - __main__ - INFO - OpenSearch collection is active
2024-12-25 10:33:05 - __main__ - INFO - Created Knowledge Base: KB123ABC
2024-12-25 10:33:10 - __main__ - INFO - Created data source: DS456DEF
2024-12-25 10:33:15 - __main__ - INFO - Started ingestion job: JOB789GHI
2024-12-25 10:38:00 - __main__ - INFO - Ingestion job completed successfully
2024-12-25 10:38:01 - __main__ - INFO - Bedrock Knowledge Base setup complete!

============================================================
✅ Bedrock Knowledge Base setup completed successfully!
============================================================

Knowledge Base ID: KB123ABC
Data Source ID: DS456DEF
Ingestion Job ID: JOB789GHI

Next steps:
1. Update .env file with:
   BEDROCK_KNOWLEDGE_BASE_ID=KB123ABC
2. Test Knowledge Base queries
3. Integrate with Service Mapper
```

## 创建的资源

### IAM 角色
- **名称**: AWSPricingAssistantKBRole
- **用途**: Bedrock Knowledge Base 服务角色
- **权限**: Bedrock、S3、OpenSearch

### OpenSearch Serverless 集合
- **名称**: aws-pricing-kb-collection
- **类型**: VECTORSEARCH
- **用途**: 向量存储

### Bedrock Knowledge Base
- **名称**: aws-pricing-assistant-kb
- **嵌入模型**: Amazon Titan Embeddings v2
- **数据源**: S3

## 成本估算

使用此脚本创建的资源会产生以下费用：

### OpenSearch Serverless
- OCU (OpenSearch Compute Units): 按小时计费
- 存储: 按 GB/月计费
- 估算: $50-100/月（取决于使用量）

### Bedrock Knowledge Base
- 数据摄取: 按文档数量计费
- 查询: 按请求数量计费
- 估算: $10-50/月（取决于使用量）

### S3 存储
- 标准存储: 按 GB/月计费
- 估算: $1-5/月

**总计**: 约 $60-150/月

## 故障排除

### 错误: OpenSearch 安全策略缺失

**症状**: 
```
Error: No matching security policy of encryption type found for collection
```

**原因**: OpenSearch Serverless 需要先创建安全策略才能创建集合

**解决方案**: 
脚本已自动处理此问题。如果仍然出错：

1. 手动删除可能存在的不完整策略：
```bash
aws opensearchserverless delete-security-policy \
  --name aws-pricing-kb-encrypt \
  --type encryption \
  --region us-east-1

aws opensearchserverless delete-security-policy \
  --name aws-pricing-kb-network \
  --type network \
  --region us-east-1

aws opensearchserverless delete-access-policy \
  --name aws-pricing-kb-data \
  --type data \
  --region us-east-1
```

2. 重新运行脚本

### 错误: 模型访问未启用

**症状**: 
```
Error: Could not access bedrock model
```

**解决方案**:
1. 打开 Amazon Bedrock 控制台
2. 导航到 "Model access"
3. 请求访问 Amazon Titan Embeddings v2
4. 等待批准（通常立即批准）

### 错误: IAM 权限不足

**症状**:
```
Error: User is not authorized to perform: iam:CreateRole
```

**所需权限**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:PutRolePolicy",
        "iam:GetRole",
        "iam:PassRole",
        "aoss:CreateCollection",
        "aoss:BatchGetCollection",
        "bedrock:CreateKnowledgeBase",
        "bedrock:CreateDataSource",
        "bedrock:StartIngestionJob",
        "bedrock:GetIngestionJob"
      ],
      "Resource": "*"
    }
  ]
}
```

### 错误: OpenSearch 集合创建超时

**症状**:
```
Error: Timeout waiting for OpenSearch collection to be active
```

**解决方案**:
1. 检查 AWS Console 中的集合状态
2. 如果状态为 CREATING，等待完成
3. 如果状态为 FAILED，检查错误日志
4. 删除失败的集合后重试

### 错误: S3 存储桶不存在

**症状**:
```
Error: The specified bucket does not exist
```

**解决方案**:
```bash
# 先运行 S3 设置脚本
python scripts/setup_knowledge_base_s3.py
```

### 错误: 数据摄取失败

**症状**:
```
Error: Ingestion job failed
```

**解决方案**:
1. 检查 S3 存储桶中是否有数据
2. 验证 IAM 角色权限
3. 检查文档格式（JSON/Markdown）
4. 查看 Bedrock 控制台中的详细错误

## 验证安装

### 1. 检查 Knowledge Base

```bash
aws bedrock-agent list-knowledge-bases --region us-east-1
```

### 2. 检查数据源

```bash
aws bedrock-agent list-data-sources \
  --knowledge-base-id KB123ABC \
  --region us-east-1
```

### 3. 测试查询

```python
import boto3

bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = bedrock_agent.retrieve(
    knowledgeBaseId='KB123ABC',
    retrievalQuery={
        'text': 'What is Amazon EC2?'
    }
)

print(response['retrievalResults'])
```

## 清理资源

如果需要删除创建的资源：

### 1. 删除 Knowledge Base

```bash
aws bedrock-agent delete-knowledge-base \
  --knowledge-base-id KB123ABC \
  --region us-east-1
```

### 2. 删除 OpenSearch 集合

```bash
aws opensearchserverless delete-collection \
  --id abc123 \
  --region us-east-1
```

### 3. 删除 IAM 角色

```bash
# 先删除内联策略
aws iam delete-role-policy \
  --role-name AWSPricingAssistantKBRole \
  --policy-name KBBedrockPolicy

aws iam delete-role-policy \
  --role-name AWSPricingAssistantKBRole \
  --policy-name KBS3Policy

aws iam delete-role-policy \
  --role-name AWSPricingAssistantKBRole \
  --policy-name KBOpenSearchPolicy

# 删除角色
aws iam delete-role \
  --role-name AWSPricingAssistantKBRole
```

## 后续步骤

完成 Knowledge Base 创建后：

1. **更新配置文件**:
   ```bash
   echo "BEDROCK_KNOWLEDGE_BASE_ID=KB123ABC" >> .env
   ```

2. **测试 Knowledge Base**:
   ```bash
   python scripts/test_knowledge_base.py
   ```

3. **集成到应用**:
   - 更新 Service Mapper 配置
   - 测试服务映射查询
   - 验证定价数据检索

## 相关文档

- [S3 设置脚本文档](./README_SETUP_KB_S3.md)
- [Amazon Bedrock Knowledge Base 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [OpenSearch Serverless 文档](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)
- [项目部署指南](../docs/部署指南.md)

## 技术细节

### Python 3.14 兼容性优化

- 移除了对 `pydantic-settings` 的依赖
- 使用标准库实现配置加载
- 独立运行，无需项目其他模块
- 改进的错误处理和用户交互

### 安全最佳实践

- IAM 角色使用最小权限原则
- OpenSearch 集合默认私有
- 数据传输加密
- 访问日志记录

### 性能优化

- 异步等待资源创建
- 智能重试机制
- 进度显示
- 超时保护
