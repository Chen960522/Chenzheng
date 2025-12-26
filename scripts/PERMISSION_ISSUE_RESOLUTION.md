# Bedrock Knowledge Base 权限问题解决方案

## 问题诊断

✅ **已确认问题根源**: Service Control Policy (SCP) 限制

### 诊断结果

```
测试结果:
✅ AWS 身份验证成功
✅ bedrock-agent:ListKnowledgeBases - 成功
✅ bedrock:ListFoundationModels - 成功  
✅ bedrock:GetFoundationModel - 成功
❌ bedrock:CreateKnowledgeBase - 拒绝访问

IAM 权限:
✅ AdministratorAccess (AWS 托管策略)
✅ AmazonBedrockFullAccess (AWS 托管策略)
✅ 无权限边界 (Permission Boundary)

组织配置:
⚠️  账户属于 AWS Organization (ID: o-no7m56jgv3)
⚠️  Service Control Policy (SCP) 已启用
⚠️  主账户: 524022421975 (awspayeraccount183@bosicloud.com)
```

### 问题原因

即使你有 **AdministratorAccess**，AWS Organizations 的 **Service Control Policy (SCP)** 仍然可以限制某些操作。SCP 是组织级别的权限边界，优先级高于 IAM 策略。

## 解决方案

### 方案 1: 请求组织管理员修改 SCP（推荐）

联系 AWS 组织管理员（主账户: awspayeraccount183@bosicloud.com），请求添加 Bedrock Knowledge Base 权限。

**发送给管理员的信息模板:**

```
主题: 请求添加 Bedrock Knowledge Base 创建权限

您好，

我在开发 AWS Pricing Assistant 项目时遇到权限问题。虽然我的账户有 AdministratorAccess，
但由于 SCP 限制，无法创建 Bedrock Knowledge Base。

账户信息:
- 账户 ID: 577823079867
- 用户: chenzheng@bosicloud.com
- 区域: us-east-1

需要的权限:
- bedrock:CreateKnowledgeBase
- bedrock:GetKnowledgeBase
- bedrock:CreateDataSource
- bedrock:StartIngestionJob
- bedrock:GetIngestionJob
- aoss:* (OpenSearch Serverless)
- iam:CreateRole (用于 Bedrock 服务角色)
- iam:PassRole

请在 SCP 中添加这些权限，或者将我的账户移到允许使用 Bedrock 的 OU。

参考文档: scripts/PERMISSION_ISSUE_RESOLUTION.md

谢谢！
```

### 方案 2: 使用 AWS Console 手动创建（临时方案）

如果 SCP 只限制 API 调用而不限制 Console 操作，可以尝试通过 Console 创建。

#### 步骤:

1. **打开 Bedrock Console**
   ```
   https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/knowledge-bases
   ```

2. **创建 Knowledge Base**
   - 点击 "Create knowledge base"
   - Name: `aws-pricing-assistant-kb`
   - Description: `Knowledge Base for AWS Pricing Assistant`
   - 选择 "Create and use a new service role"

3. **配置数据源**
   - Data source type: Amazon S3
   - S3 URI: `s3://aws-pricing-assistant-kb-data/`
   - Chunking strategy: Fixed-size chunking
   - Max tokens: 512
   - Overlap percentage: 20%

4. **配置向量存储**
   - Vector database: Amazon OpenSearch Serverless
   - 选择 "Quick create a new vector store"
   - Embedding model: Titan Text Embeddings V2

5. **记录 Knowledge Base ID**
   - 创建完成后，复制 Knowledge Base ID
   - 更新到 `.env` 文件:
     ```
     BEDROCK_KNOWLEDGE_BASE_ID=<your-kb-id>
     ```

### 方案 3: 使用其他 AWS 账户（开发测试）

如果有其他没有 SCP 限制的 AWS 账户，可以在那里创建 Knowledge Base 用于开发测试。

### 方案 4: 使用 CloudFormation（可能绕过限制）

有时 SCP 只限制直接 API 调用，但允许通过 CloudFormation 创建资源。

创建 CloudFormation 模板:

```yaml
# bedrock-kb-stack.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Bedrock Knowledge Base for AWS Pricing Assistant'

Parameters:
  S3BucketName:
    Type: String
    Default: aws-pricing-assistant-kb-data
    Description: S3 bucket containing knowledge base data

Resources:
  KnowledgeBase:
    Type: AWS::Bedrock::KnowledgeBase
    Properties:
      Name: aws-pricing-assistant-kb
      Description: Knowledge Base for AWS Pricing Assistant
      RoleArn: !GetAtt KnowledgeBaseRole.Arn
      KnowledgeBaseConfiguration:
        Type: VECTOR
        VectorKnowledgeBaseConfiguration:
          EmbeddingModelArn: !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/amazon.titan-embed-text-v2:0'
      StorageConfiguration:
        Type: OPENSEARCH_SERVERLESS
        OpensearchServerlessConfiguration:
          CollectionArn: !GetAtt OpenSearchCollection.Arn
          VectorIndexName: bedrock-knowledge-base-default-index
          FieldMapping:
            VectorField: bedrock-knowledge-base-default-vector
            TextField: AMAZON_BEDROCK_TEXT_CHUNK
            MetadataField: AMAZON_BEDROCK_METADATA

  KnowledgeBaseRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: bedrock.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AmazonBedrockFullAccess
        - arn:aws:iam::aws:policy/AmazonOpenSearchServiceFullAccess

  OpenSearchCollection:
    Type: AWS::OpenSearchServerless::Collection
    Properties:
      Name: aws-pricing-kb-collection
      Type: VECTORSEARCH
      Description: Vector store for AWS Pricing Assistant

Outputs:
  KnowledgeBaseId:
    Description: Knowledge Base ID
    Value: !Ref KnowledgeBase
    Export:
      Name: !Sub '${AWS::StackName}-KnowledgeBaseId'
```

部署:
```bash
aws cloudformation create-stack \
  --stack-name aws-pricing-kb \
  --template-body file://bedrock-kb-stack.yaml \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

## 验证解决方案

解决权限问题后，运行验证脚本:

```bash
python scripts/test_bedrock_permissions.py
```

应该看到:
```
5. Testing bedrock-agent:CreateKnowledgeBase...
   ✅ Success! Created KB: <kb-id>
```

## 后续步骤

1. **如果通过方案 1 解决**:
   - 等待管理员修改 SCP
   - 运行 `python scripts/create_kb_simple.py`

2. **如果通过方案 2 解决**:
   - 在 Console 创建 Knowledge Base
   - 记录 KB ID 并更新 `.env`
   - 运行 `python scripts/setup_knowledge_base_s3.py` 上传数据

3. **如果通过方案 3 解决**:
   - 在其他账户创建 KB
   - 配置跨账户访问（如需要）

4. **如果通过方案 4 解决**:
   - 部署 CloudFormation stack
   - 获取 KB ID 并更新 `.env`

## 相关文档

- [AWS Organizations SCPs](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- [Bedrock Knowledge Base Setup](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [IAM vs SCP 权限评估](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)

## 技术支持

如果以上方案都无法解决，可以:
1. 联系 AWS Support
2. 在项目 GitHub 提 Issue
3. 联系项目维护者
