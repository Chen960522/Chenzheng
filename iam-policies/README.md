# IAM 权限配置

## 问题

运行 Knowledge Base 创建脚本时遇到权限错误：

```
AccessDeniedException: User: arn:aws:iam::577823079867:user/chenzheng@bosicloud.com 
is not authorized to perform: bedrock:CreateKnowledgeBase
```

## 解决方案

需要 AWS 管理员为你的 IAM 用户添加必要的权限。

## 方法 1: 附加托管策略（推荐用于测试）

让管理员为你的用户附加以下 AWS 托管策略：

```bash
aws iam attach-user-policy \
  --user-name chenzheng@bosicloud.com \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam attach-user-policy \
  --user-name chenzheng@bosicloud.com \
  --policy-arn arn:aws:iam::aws:policy/IAMFullAccess
```

**注意**: 这些是完全访问权限，仅用于开发/测试环境。

## 方法 2: 使用自定义策略（推荐用于生产）

### 步骤 1: 创建 IAM 策略

让管理员使用 `bedrock-kb-creator-policy.json` 文件创建策略：

```bash
aws iam create-policy \
  --policy-name BedrockKnowledgeBaseCreator \
  --policy-document file://iam-policies/bedrock-kb-creator-policy.json \
  --description "允许创建和管理 Bedrock Knowledge Base"
```

### 步骤 2: 附加策略到用户

```bash
aws iam attach-user-policy \
  --user-name chenzheng@bosicloud.com \
  --policy-arn arn:aws:iam::577823079867:policy/BedrockKnowledgeBaseCreator
```

## 方法 3: 通过 AWS Console 配置

### 步骤 1: 打开 IAM 控制台

1. 登录 AWS Console
2. 导航到 IAM 服务
3. 选择 "Users"
4. 找到用户 `chenzheng@bosicloud.com`

### 步骤 2: 附加策略

1. 点击 "Add permissions"
2. 选择 "Attach policies directly"
3. 搜索并选择以下策略：
   - `AmazonBedrockFullAccess`
   - `IAMFullAccess` (或创建自定义策略)
4. 点击 "Next" 和 "Add permissions"

## 所需权限说明

### Bedrock 权限
- `bedrock:CreateKnowledgeBase` - 创建知识库
- `bedrock:GetKnowledgeBase` - 查询知识库状态
- `bedrock:CreateDataSource` - 创建数据源
- `bedrock:StartIngestionJob` - 启动数据摄取

### IAM 权限
- `iam:CreateRole` - 创建服务角色
- `iam:PassRole` - 传递角色给 Bedrock
- `iam:AttachRolePolicy` - 附加策略到角色

### OpenSearch Serverless 权限
- `aoss:CreateCollection` - 创建集合
- `aoss:CreateSecurityPolicy` - 创建安全策略
- `aoss:CreateAccessPolicy` - 创建访问策略

### S3 权限
- `s3:GetObject` - 读取数据
- `s3:ListBucket` - 列出对象
- `s3:CreateBucket` - 创建存储桶

## 验证权限

配置完成后，验证权限：

```bash
# 测试 Bedrock 权限
aws bedrock list-knowledge-bases --region us-east-1

# 测试 IAM 权限
aws iam list-roles --max-items 1

# 测试 OpenSearch 权限
aws opensearchserverless list-collections --region us-east-1
```

## 最小权限原则

对于生产环境，建议使用 `bedrock-kb-creator-policy.json` 中定义的最小权限集，而不是完全访问权限。

## 临时解决方案

如果无法立即获得权限，可以：

1. **使用 AWS Console 手动创建**
   - 在 Bedrock Console 中手动创建 Knowledge Base
   - 让 Bedrock 自动创建所有资源
   - 记录 Knowledge Base ID 并更新到 `.env` 文件

2. **请求管理员代为创建**
   - 提供 `bedrock-kb-creator-policy.json` 给管理员
   - 管理员使用管理员权限运行脚本
   - 创建完成后将 Knowledge Base ID 提供给你

## 联系管理员

将以下信息发送给 AWS 管理员：

```
主题: 请求 Bedrock Knowledge Base 创建权限

您好，

我需要创建 Amazon Bedrock Knowledge Base 来开发 AWS Pricing Assistant 项目。

请为我的 IAM 用户添加以下权限：
- 用户: chenzheng@bosicloud.com
- 账户: 577823079867
- 区域: us-east-1

推荐方案：
1. 使用附件中的 bedrock-kb-creator-policy.json 创建自定义策略
2. 将策略附加到我的用户

或者临时方案（仅用于开发）：
- 附加 AmazonBedrockFullAccess 托管策略

详细说明请参考: iam-policies/README.md

谢谢！
```

## 相关文档

- [AWS Bedrock IAM 权限](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html)
- [OpenSearch Serverless 权限](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-iam.html)
- [IAM 最佳实践](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
