# Lambda 保留环境变量说明

## 问题

在创建 Lambda 函数时遇到错误：

```
InvalidParameterValueException: Lambda was unable to configure your environment variables 
because the environment variables you have provided contains reserved keys that are currently 
not supported for modification. Reserved keys used in this request: AWS_REGION
```

## 原因

AWS Lambda 有一些**保留的环境变量**，这些变量由 Lambda 运行时自动设置，不能被用户覆盖。

### Lambda 保留的环境变量

以下环境变量由 Lambda 自动设置，**不能在创建函数时指定**：

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `AWS_REGION` | Lambda 函数运行的 AWS 区域 | `us-east-1` |
| `AWS_DEFAULT_REGION` | 默认 AWS 区域（同 AWS_REGION） | `us-east-1` |
| `AWS_EXECUTION_ENV` | Lambda 运行时环境 | `AWS_Lambda_python3.11` |
| `AWS_LAMBDA_FUNCTION_NAME` | Lambda 函数名称 | `my-function` |
| `AWS_LAMBDA_FUNCTION_VERSION` | 函数版本 | `$LATEST` |
| `AWS_LAMBDA_FUNCTION_MEMORY_SIZE` | 分配的内存大小（MB） | `512` |
| `AWS_LAMBDA_LOG_GROUP_NAME` | CloudWatch 日志组名称 | `/aws/lambda/my-function` |
| `AWS_LAMBDA_LOG_STREAM_NAME` | CloudWatch 日志流名称 | `2024/01/01/[$LATEST]abc123` |
| `LAMBDA_TASK_ROOT` | Lambda 函数代码目录 | `/var/task` |
| `LAMBDA_RUNTIME_DIR` | Lambda 运行时目录 | `/var/runtime` |
| `_HANDLER` | 函数处理器 | `lambda_handler.handler` |
| `_X_AMZN_TRACE_ID` | AWS X-Ray 追踪 ID | `Root=1-...` |

## 解决方案

### 方案 1: 使用 Lambda 自动提供的变量（推荐）

在 Lambda 函数代码中直接使用 `AWS_REGION`，不需要手动设置：

```python
import os

def lambda_handler(event, context):
    # AWS_REGION 由 Lambda 自动设置
    region = os.environ['AWS_REGION']
    print(f"Running in region: {region}")
```

### 方案 2: 使用自定义变量名

如果需要传递区域信息，使用不同的变量名：

```bash
# 错误的做法 ❌
aws lambda create-function \
    --environment "Variables={AWS_REGION=us-east-1}" \
    ...

# 正确的做法 ✅
aws lambda create-function \
    --environment "Variables={DYNAMODB_REGION=us-east-1,TABLE_PREFIX=myapp}" \
    ...
```

在代码中使用：

```python
import os

def lambda_handler(event, context):
    # 优先使用 Lambda 自动设置的 AWS_REGION
    region = os.environ.get('AWS_REGION') or os.environ.get('DYNAMODB_REGION', 'us-east-1')
    print(f"Using region: {region}")
```

### 方案 3: 从 Lambda Context 获取

Lambda context 对象也包含区域信息：

```python
def lambda_handler(event, context):
    # 从 context 获取函数 ARN，解析出区域
    function_arn = context.invoked_function_arn
    # ARN 格式: arn:aws:lambda:us-east-1:123456789012:function:my-function
    region = function_arn.split(':')[3]
    print(f"Region from ARN: {region}")
```

## 修复后的脚本

已修复 `scripts/setup_eventbridge_crawler.sh`：

**修改前（错误）：**
```bash
--environment "Variables={AWS_REGION=$AWS_REGION,TABLE_PREFIX=$APP_NAME}"
```

**修改后（正确）：**
```bash
--environment "Variables={TABLE_PREFIX=$APP_NAME,DYNAMODB_REGION=$AWS_REGION}"
```

**Lambda handler 代码：**
```python
def lambda_handler(event, context):
    # AWS_REGION 由 Lambda 自动提供
    region = os.environ.get('AWS_REGION') or os.environ.get('DYNAMODB_REGION', 'us-east-1')
    logger.info(f"Using AWS region: {region}")
    # ... rest of code
```

## 其他注意事项

### 1. 不要覆盖其他保留变量

除了 `AWS_REGION`，也不要尝试设置其他 AWS 保留变量：
- `AWS_ACCESS_KEY_ID` - 使用 IAM 角色代替
- `AWS_SECRET_ACCESS_KEY` - 使用 IAM 角色代替
- `AWS_SESSION_TOKEN` - 使用 IAM 角色代替

### 2. 使用 IAM 角色而非访问密钥

Lambda 函数应该使用 IAM 角色获取权限，而不是在环境变量中存储访问密钥：

```bash
# 创建 Lambda 时指定角色
aws lambda create-function \
    --role arn:aws:iam::123456789012:role/lambda-execution-role \
    ...
```

### 3. 敏感信息使用 Secrets Manager

对于敏感配置（如数据库密码、API 密钥），使用 AWS Secrets Manager：

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

def lambda_handler(event, context):
    secrets = get_secret('my-app/config')
    db_password = secrets['db_password']
    # ... use password
```

## 验证修复

运行修复后的脚本：

```bash
cd aws-pricing-assistant
bash scripts/setup_eventbridge_crawler.sh
```

应该成功创建 Lambda 函数，不再报错。

## 相关文档

- [Lambda Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
- [Lambda Reserved Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html#configuration-envvars-runtime)
- [Lambda Execution Role](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html)
- [AWS Secrets Manager with Lambda](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_lambda.html)

## 故障排除

### 如果仍然遇到问题

1. **检查现有 Lambda 函数**：
   ```bash
   aws lambda get-function --function-name aws-pricing-assistant-crawler
   ```

2. **删除并重新创建**：
   ```bash
   aws lambda delete-function --function-name aws-pricing-assistant-crawler
   bash scripts/setup_eventbridge_crawler.sh
   ```

3. **查看 Lambda 环境变量**：
   ```bash
   aws lambda get-function-configuration \
       --function-name aws-pricing-assistant-crawler \
       --query 'Environment.Variables'
   ```

4. **测试 Lambda 函数**：
   ```bash
   aws lambda invoke \
       --function-name aws-pricing-assistant-crawler \
       --invocation-type RequestResponse \
       /tmp/response.json
   
   cat /tmp/response.json | python -m json.tool
   ```
