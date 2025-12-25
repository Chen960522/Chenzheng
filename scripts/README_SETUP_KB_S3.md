# Knowledge Base S3 Setup Script

## 概述

`setup_knowledge_base_s3.py` 脚本用于创建和配置 Amazon Bedrock Knowledge Base 所需的 S3 存储桶，并上传知识库内容。

## Python 版本兼容性

- ✅ Python 3.12+
- ✅ Python 3.13
- ✅ Python 3.14 (已优化)

此脚本已优化为独立运行，不依赖项目的其他模块，可在任何 Python 3.12+ 环境中使用。

## 前置要求

### 1. 安装依赖

```bash
pip install boto3
```

### 2. 配置 AWS 凭证

选择以下任一方式：

#### 方式 A: 使用 AWS CLI 配置（推荐）

```bash
aws configure
```

#### 方式 B: 设置环境变量

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-east-1
```

Windows PowerShell:
```powershell
$env:AWS_ACCESS_KEY_ID="your-access-key"
$env:AWS_SECRET_ACCESS_KEY="your-secret-key"
$env:AWS_REGION="us-east-1"
```

#### 方式 C: 使用 .env 文件

1. 复制示例配置文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的 AWS 凭证：
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-actual-access-key
AWS_SECRET_ACCESS_KEY=your-actual-secret-key
S3_KNOWLEDGE_BASE_BUCKET=aws-pricing-assistant-kb-data
```

## 使用方法

### 基本用法

```bash
cd aws-pricing-assistant
python scripts/setup_knowledge_base_s3.py
```

### 自定义配置

通过环境变量覆盖默认配置：

```bash
export AWS_REGION=ap-southeast-1
export S3_KNOWLEDGE_BASE_BUCKET=my-custom-kb-bucket
python scripts/setup_knowledge_base_s3.py
```

## 脚本功能

### 1. 创建 S3 存储桶

- 自动创建指定名称的 S3 存储桶
- 根据区域自动配置 LocationConstraint
- 如果存储桶已存在，跳过创建步骤

### 2. 配置存储桶安全性

- ✅ 启用版本控制
- ✅ 启用服务器端加密 (AES256)
- ✅ 启用 Bucket Key（降低加密成本）
- ✅ 阻止所有公共访问

### 3. 上传知识库内容

自动上传以下目录中的所有文件：

```
knowledge_base/
├── aws_services/          # AWS 服务定义
│   ├── compute_services.json
│   ├── storage_services.json
│   ├── database_services.json
│   ├── network_services.json
│   ├── analytics_services.json
│   ├── ml_services.json
│   └── container_serverless_services.json
├── pricing_data/          # 定价数据
│   ├── compute_pricing.json
│   ├── storage_pricing.json
│   ├── database_pricing.json
│   └── data_transfer_pricing.json
├── service_mappings/      # 云服务映射
│   ├── alibaba_mappings.json
│   ├── huawei_mappings.json
│   ├── tencent_mappings.json
│   ├── gcp_mappings.json
│   └── azure_mappings.json
└── README.md
```

### 4. 验证上传

脚本会列出所有已上传的文件，确认上传成功。

## 输出示例

```
============================================================
AWS Pricing Assistant - Knowledge Base S3 Setup
============================================================

Configuration:
  AWS Region: us-east-1
  S3 Bucket: aws-pricing-assistant-kb-data

AWS Identity:
  Account: 123456789012
  User/Role: admin

2024-12-25 10:30:00 - __main__ - INFO - Starting Knowledge Base S3 setup...
2024-12-25 10:30:01 - __main__ - INFO - Created bucket: aws-pricing-assistant-kb-data
2024-12-25 10:30:02 - __main__ - INFO - Enabled versioning for bucket
2024-12-25 10:30:03 - __main__ - INFO - Enabled encryption for bucket
2024-12-25 10:30:04 - __main__ - INFO - Blocked public access for bucket
2024-12-25 10:30:05 - __main__ - INFO - Uploaded: aws_services/compute_services.json
2024-12-25 10:30:06 - __main__ - INFO - Uploaded: aws_services/storage_services.json
...
2024-12-25 10:30:20 - __main__ - INFO - Upload complete: 17 files uploaded, 0 failed
2024-12-25 10:30:21 - __main__ - INFO - Found 17 files in bucket

============================================================
✅ Knowledge Base S3 setup completed successfully!
============================================================

Bucket name: aws-pricing-assistant-kb-data
Region: us-east-1

Next steps:
1. Create Bedrock Knowledge Base in AWS Console
2. Configure Knowledge Base to use this S3 bucket as data source
3. Run sync to index the content
```

## 故障排除

### 错误: 无法验证 AWS 凭证

**原因**: AWS 凭证未配置或无效

**解决方案**:
1. 检查 AWS CLI 配置: `aws sts get-caller-identity`
2. 确认环境变量已设置
3. 检查 `.env` 文件内容

### 错误: 存储桶名称已被占用

**原因**: S3 存储桶名称全局唯一，可能已被其他账户使用

**解决方案**:
```bash
export S3_KNOWLEDGE_BASE_BUCKET=your-unique-bucket-name-12345
python scripts/setup_knowledge_base_s3.py
```

### 错误: 权限不足

**原因**: IAM 用户/角色缺少必要权限

**所需权限**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutObject",
        "s3:PutBucketVersioning",
        "s3:PutEncryptionConfiguration",
        "s3:PutBucketPublicAccessBlock",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::aws-pricing-assistant-*",
        "arn:aws:s3:::aws-pricing-assistant-*/*"
      ]
    }
  ]
}
```

### 错误: 知识库目录不存在

**原因**: 脚本在错误的目录运行

**解决方案**:
```bash
cd aws-pricing-assistant
python scripts/setup_knowledge_base_s3.py
```

## 配置选项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `AWS_REGION` | `us-east-1` | AWS 区域 |
| `S3_KNOWLEDGE_BASE_BUCKET` | `aws-pricing-assistant-kb-data` | S3 存储桶名称 |

## 后续步骤

完成 S3 设置后，继续配置 Bedrock Knowledge Base：

1. **创建 Knowledge Base**:
   ```bash
   python scripts/create_bedrock_knowledge_base.py
   ```

2. **在 AWS Console 中配置**:
   - 打开 Amazon Bedrock 控制台
   - 创建新的 Knowledge Base
   - 选择 S3 作为数据源
   - 指定存储桶: `aws-pricing-assistant-kb-data`
   - 选择嵌入模型: `amazon.titan-embed-text-v2:0`
   - 启动同步

3. **更新配置**:
   将 Knowledge Base ID 添加到 `.env`:
   ```bash
   BEDROCK_KNOWLEDGE_BASE_ID=your-kb-id-here
   ```

## 技术细节

### Python 3.14 兼容性优化

- 移除了对 `pydantic-settings` 的依赖
- 使用标准库实现配置加载
- 简化的日志配置
- 独立运行，无需项目其他模块

### 安全最佳实践

- 默认启用加密
- 阻止公共访问
- 启用版本控制
- 使用 Bucket Key 优化成本

## 相关文档

- [AWS Bedrock Knowledge Base 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [S3 安全最佳实践](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [项目部署指南](../docs/部署指南.md)
