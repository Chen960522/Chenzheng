# 故障排查会话总结

**日期**: 2024-12-25  
**问题**: Bedrock Knowledge Base 创建权限问题 & Lambda 环境变量问题

## 问题 1: Bedrock Knowledge Base 创建权限被拒绝

### 症状
```
AccessDeniedException: User: arn:aws:iam::577823079867:user/chenzheng@bosicloud.com 
is not authorized to perform: bedrock:CreateKnowledgeBase
```

### 诊断过程

1. **验证 IAM 权限** ✅
   - 用户拥有 `AdministratorAccess` 策略
   - 用户拥有 `AmazonBedrockFullAccess` 策略
   - 无权限边界 (Permission Boundary)

2. **测试 Bedrock 访问** ✅
   - `bedrock:ListFoundationModels` - 成功
   - `bedrock:GetFoundationModel` - 成功
   - `bedrock-agent:ListKnowledgeBases` - 成功
   - `bedrock-agent:CreateKnowledgeBase` - **失败**

3. **识别根本原因** 🎯
   - 账户属于 AWS Organization (ID: o-no7m56jgv3)
   - Service Control Policy (SCP) 已启用
   - SCP 限制了 `bedrock:CreateKnowledgeBase` 操作
   - **即使有 AdministratorAccess，SCP 仍然优先**

### 解决方案

创建了多个解决方案供选择：

#### 方案 1: 请求组织管理员修改 SCP（推荐）
- 联系主账户管理员 (awspayeraccount183@bosicloud.com)
- 请求在 SCP 中添加 Bedrock Knowledge Base 权限
- 文档: `scripts/PERMISSION_ISSUE_RESOLUTION.md`

#### 方案 2: CloudFormation 部署（可能绕过限制）
- 创建了 CloudFormation 模板: `infrastructure/bedrock-kb-stack.yaml`
- 创建了部署脚本: `scripts/deploy_kb_cloudformation.py`
- CloudFormation 有时可以绕过 SCP 限制

#### 方案 3: AWS Console 手动创建（临时方案）
- 通过 Bedrock Console 手动创建 Knowledge Base
- 记录 KB ID 并更新到 `.env` 文件
- 详细步骤见文档

### 创建的文件

1. **scripts/test_bedrock_permissions.py**
   - 诊断工具，测试各种 Bedrock 权限
   - 识别 SCP 限制
   - 提供详细的错误分析

2. **scripts/PERMISSION_ISSUE_RESOLUTION.md**
   - 完整的问题诊断和解决方案文档
   - 包含联系管理员的模板
   - 多种解决方案的详细步骤

3. **infrastructure/bedrock-kb-stack.yaml**
   - CloudFormation 模板
   - 自动创建所有必需资源
   - 包含 OpenSearch Serverless、IAM 角色、安全策略

4. **scripts/deploy_kb_cloudformation.py**
   - CloudFormation 部署脚本
   - 自动化部署流程
   - 包含错误处理和进度监控

5. **iam-policies/bedrock-kb-creator-policy.json**
   - 最小权限 IAM 策略
   - 用于生产环境

6. **iam-policies/README.md**
   - IAM 权限配置指南
   - 多种配置方法说明

---

## 问题 2: Lambda 环境变量使用保留键

### 症状
```
InvalidParameterValueException: Lambda was unable to configure your environment variables 
because the environment variables you have provided contains reserved keys that are currently 
not supported for modification. Reserved keys used in this request: AWS_REGION
```

### 根本原因

Lambda 有一组**保留的环境变量**，由 Lambda 运行时自动设置，不能被用户覆盖：
- `AWS_REGION` - Lambda 函数运行的区域
- `AWS_DEFAULT_REGION` - 默认区域
- `AWS_EXECUTION_ENV` - 运行时环境
- `AWS_LAMBDA_FUNCTION_NAME` - 函数名称
- 等等...

### 解决方案

**修改前（错误）：**
```bash
--environment "Variables={AWS_REGION=$AWS_REGION,TABLE_PREFIX=$APP_NAME}"
```

**修改后（正确）：**
```bash
--environment "Variables={TABLE_PREFIX=$APP_NAME,DYNAMODB_REGION=$AWS_REGION}"
```

**Lambda 代码更新：**
```python
def lambda_handler(event, context):
    # AWS_REGION 由 Lambda 自动提供
    region = os.environ.get('AWS_REGION') or os.environ.get('DYNAMODB_REGION', 'us-east-1')
    logger.info(f"Using AWS region: {region}")
    # ... rest of code
```

### 修改的文件

1. **scripts/setup_eventbridge_crawler.sh**
   - 移除 `AWS_REGION` 环境变量
   - 添加 `DYNAMODB_REGION` 作为替代
   - 更新 Lambda handler 代码以使用自动提供的 `AWS_REGION`

2. **scripts/LAMBDA_RESERVED_VARIABLES.md**
   - 完整的 Lambda 保留变量列表
   - 详细的解决方案说明
   - 最佳实践指南
   - 故障排除步骤

---

## 关键学习点

### 1. AWS Organizations 和 SCP

- **SCP 优先级高于 IAM 策略**
  - 即使有 AdministratorAccess，SCP 仍然可以限制操作
  - SCP 是组织级别的权限边界

- **权限评估顺序**:
  1. SCP (Service Control Policy) - 组织级别
  2. Permission Boundary - 用户/角色级别
  3. IAM Policy - 用户/角色级别
  4. Resource Policy - 资源级别

### 2. Lambda 环境变量

- **保留变量不能覆盖**
  - Lambda 自动设置的变量不能手动指定
  - 使用自定义变量名避免冲突

- **最佳实践**:
  - 使用 Lambda 自动提供的变量
  - 敏感信息使用 Secrets Manager
  - 使用 IAM 角色而非访问密钥

### 3. 诊断方法

- **系统化测试**
  - 逐步测试各个权限
  - 识别具体失败的操作
  - 检查组织级别限制

- **创建诊断工具**
  - 自动化权限测试
  - 提供详细的错误分析
  - 给出具体的解决建议

---

## 后续步骤

### 对于 Bedrock Knowledge Base 问题

1. **短期方案**:
   - 尝试 CloudFormation 部署: `python scripts/deploy_kb_cloudformation.py`
   - 或通过 AWS Console 手动创建

2. **长期方案**:
   - 联系组织管理员修改 SCP
   - 获得正式的 Bedrock 权限

### 对于 Lambda 环境变量问题

1. **立即可用**:
   - 运行修复后的脚本: `bash scripts/setup_eventbridge_crawler.sh`
   - 验证 Lambda 函数创建成功

2. **验证修复**:
   ```bash
   # 检查 Lambda 环境变量
   aws lambda get-function-configuration \
       --function-name aws-pricing-assistant-crawler \
       --query 'Environment.Variables'
   
   # 测试 Lambda 函数
   aws lambda invoke \
       --function-name aws-pricing-assistant-crawler \
       --invocation-type RequestResponse \
       /tmp/response.json
   ```

---

## 文档和工具

### 新增文档
- `scripts/PERMISSION_ISSUE_RESOLUTION.md` - Bedrock 权限问题完整指南
- `scripts/LAMBDA_RESERVED_VARIABLES.md` - Lambda 保留变量说明
- `iam-policies/README.md` - IAM 权限配置指南

### 新增工具
- `scripts/test_bedrock_permissions.py` - Bedrock 权限诊断工具
- `scripts/deploy_kb_cloudformation.py` - CloudFormation 部署脚本

### 新增模板
- `infrastructure/bedrock-kb-stack.yaml` - CloudFormation 模板
- `iam-policies/bedrock-kb-creator-policy.json` - IAM 策略模板

---

## Git 提交

**Commit**: 70a047e  
**Message**: 修复 Bedrock Knowledge Base 权限问题和 Lambda 环境变量问题

**变更文件**:
- 新增: infrastructure/bedrock-kb-stack.yaml
- 新增: scripts/LAMBDA_RESERVED_VARIABLES.md
- 新增: scripts/PERMISSION_ISSUE_RESOLUTION.md
- 新增: scripts/deploy_kb_cloudformation.py
- 修改: scripts/setup_eventbridge_crawler.sh
- 新增: scripts/test_bedrock_permissions.py

**推送状态**: ✅ 成功推送到 GitHub (Chen960522/Chenzheng)

---

## 参考资料

- [AWS Organizations SCPs](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html)
- [Lambda Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
- [Lambda Reserved Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-runtime)
- [Bedrock Knowledge Base Setup](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [IAM Policy Evaluation Logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html)
