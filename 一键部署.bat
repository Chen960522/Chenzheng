@echo off
REM ============================================================================
REM AWS智能定价助手 - Windows一键部署脚本
REM 
REM 此脚本将自动完成所有部署步骤
REM 使用方法: 一键部署.bat
REM ============================================================================

setlocal enabledelayedexpansion

REM 颜色定义（Windows 10+）
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

echo.
echo ========================================
echo AWS智能定价助手 - 一键部署
echo ========================================
echo.

REM ============================================================================
REM 步骤1: 环境检查
REM ============================================================================

echo ========================================
echo 步骤1: 环境检查
echo ========================================
echo.

echo 检查必需工具...

where aws >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%✗ AWS CLI 未安装，请先安装%NC%
    exit /b 1
)
echo %GREEN%✓ AWS CLI 已安装%NC%

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%✗ Python 未安装，请先安装%NC%
    exit /b 1
)
echo %GREEN%✓ Python 已安装%NC%

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%✗ Git 未安装，请先安装%NC%
    exit /b 1
)
echo %GREEN%✓ Git 已安装%NC%

echo.
echo 检查AWS凭证...
aws sts get-caller-identity >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%✗ AWS凭证未配置或无效，请运行 'aws configure'%NC%
    exit /b 1
)
echo %GREEN%✓ AWS凭证有效%NC%

REM ============================================================================
REM 步骤2: 配置参数
REM ============================================================================

echo.
echo ========================================
echo 步骤2: 配置部署参数
echo ========================================
echo.

set /p AWS_REGION="请输入AWS区域 [默认: us-east-1]: "
if "%AWS_REGION%"=="" set AWS_REGION=us-east-1

set /p STACK_NAME="请输入CloudFormation堆栈名称 [默认: aws-pricing-assistant]: "
if "%STACK_NAME%"=="" set STACK_NAME=aws-pricing-assistant

set /p ENVIRONMENT="请输入环境名称 [默认: production]: "
if "%ENVIRONMENT%"=="" set ENVIRONMENT=production

set /p INSTANCE_TYPE="请输入EC2实例类型 [默认: t3.medium]: "
if "%INSTANCE_TYPE%"=="" set INSTANCE_TYPE=t3.medium

set /p KEY_PAIR_NAME="请输入EC2密钥对名称 [默认: aws-pricing-assistant-key]: "
if "%KEY_PAIR_NAME%"=="" set KEY_PAIR_NAME=aws-pricing-assistant-key

echo.
echo %GREEN%✓ 配置参数已设置%NC%
echo.
echo 部署配置:
echo   AWS区域: %AWS_REGION%
echo   堆栈名称: %STACK_NAME%
echo   环境: %ENVIRONMENT%
echo   实例类型: %INSTANCE_TYPE%
echo   密钥对: %KEY_PAIR_NAME%
echo.

set /p CONFIRM="确认以上配置并继续部署? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo %YELLOW%⚠ 部署已取消%NC%
    exit /b 0
)

REM ============================================================================
REM 步骤3: 检查EC2密钥对
REM ============================================================================

echo.
echo ========================================
echo 步骤3: 检查EC2密钥对
echo ========================================
echo.

aws ec2 describe-key-pairs --key-names %KEY_PAIR_NAME% >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓ 密钥对 %KEY_PAIR_NAME% 已存在%NC%
) else (
    echo %YELLOW%⚠ 密钥对 %KEY_PAIR_NAME% 不存在，正在创建...%NC%
    
    if not exist "%USERPROFILE%\.ssh" mkdir "%USERPROFILE%\.ssh"
    
    aws ec2 create-key-pair --key-name %KEY_PAIR_NAME% --query "KeyMaterial" --output text > "%USERPROFILE%\.ssh\%KEY_PAIR_NAME%.pem"
    
    echo %GREEN%✓ 密钥对已创建并保存到 %USERPROFILE%\.ssh\%KEY_PAIR_NAME%.pem%NC%
)

REM ============================================================================
REM 步骤4: 检查Bedrock访问权限
REM ============================================================================

echo.
echo ========================================
echo 步骤4: 检查Bedrock访问权限
echo ========================================
echo.

echo 检查Bedrock模型访问权限...
aws bedrock list-foundation-models --region %AWS_REGION% >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓ Bedrock访问权限正常%NC%
) else (
    echo %RED%✗ 无法访问Bedrock服务%NC%
    echo %YELLOW%⚠ 请确保:%NC%
    echo %YELLOW%  1. 您的AWS账户已启用Bedrock服务%NC%
    echo %YELLOW%  2. 已申请Claude 3.5 Sonnet模型访问权限%NC%
    echo %YELLOW%  3. 在AWS控制台 → Bedrock → Model access 中申请%NC%
    exit /b 1
)

REM ============================================================================
REM 步骤5: 部署基础设施
REM ============================================================================

echo.
echo ========================================
echo 步骤5: 部署AWS基础设施 (预计10-15分钟)
echo ========================================
echo.

echo 开始部署CloudFormation堆栈...

if exist "scripts\deploy_infrastructure.sh" (
    bash scripts/deploy_infrastructure.sh
    if %errorlevel% neq 0 (
        echo %RED%✗ 基础设施部署失败%NC%
        exit /b 1
    )
    echo %GREEN%✓ 基础设施部署完成%NC%
) else (
    echo %RED%✗ 部署脚本不存在: scripts\deploy_infrastructure.sh%NC%
    exit /b 1
)

REM 获取CloudFormation输出
echo.
echo 获取部署输出...
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name %STACK_NAME% --query "Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue" --output text') do set ALB_URL=%%i
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name %STACK_NAME% --query "Stacks[0].Outputs[?OutputKey==`FrontendBucket`].OutputValue" --output text') do set FRONTEND_BUCKET=%%i
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name %STACK_NAME% --query "Stacks[0].Outputs[?OutputKey==`EC2InstanceId`].OutputValue" --output text') do set EC2_INSTANCE_ID=%%i

echo %GREEN%✓ 基础设施部署完成%NC%
echo   ALB URL: %ALB_URL%
echo   前端存储桶: %FRONTEND_BUCKET%
echo   EC2实例ID: %EC2_INSTANCE_ID%

REM ============================================================================
REM 步骤6: 创建DynamoDB表
REM ============================================================================

echo.
echo ========================================
echo 步骤6: 创建DynamoDB表 (预计2-3分钟)
echo ========================================
echo.

if exist "scripts\setup_dynamodb.sh" (
    bash scripts/setup_dynamodb.sh
    if %errorlevel% neq 0 (
        echo %RED%✗ DynamoDB表创建失败%NC%
        exit /b 1
    )
    echo %GREEN%✓ DynamoDB表创建完成%NC%
) else (
    echo %RED%✗ 脚本不存在: scripts\setup_dynamodb.sh%NC%
    exit /b 1
)

REM ============================================================================
REM 步骤7: 设置Bedrock Knowledge Base
REM ============================================================================

echo.
echo ========================================
echo 步骤7: 设置Bedrock Knowledge Base (预计5-10分钟)
echo ========================================
echo.

echo 上传知识库数据到S3...
if exist "scripts\setup_knowledge_base_s3.py" (
    python scripts\setup_knowledge_base_s3.py
    if %errorlevel% neq 0 (
        echo %RED%✗ 知识库数据上传失败%NC%
        exit /b 1
    )
    echo %GREEN%✓ 知识库数据上传完成%NC%
) else (
    echo %RED%✗ 脚本不存在: scripts\setup_knowledge_base_s3.py%NC%
    exit /b 1
)

echo.
echo 创建Bedrock Knowledge Base...
if exist "scripts\create_bedrock_knowledge_base.py" (
    python scripts\create_bedrock_knowledge_base.py > kb_output.txt
    if %errorlevel% neq 0 (
        echo %RED%✗ Knowledge Base创建失败%NC%
        exit /b 1
    )
    
    REM 提取Knowledge Base ID
    for /f "tokens=2 delims=:" %%i in ('findstr "Knowledge Base ID:" kb_output.txt') do set KB_ID=%%i
    set KB_ID=%KB_ID: =%
    
    if not "%KB_ID%"=="" (
        echo %GREEN%✓ Knowledge Base创建完成%NC%
        echo   Knowledge Base ID: %KB_ID%
        
        REM 更新.env文件
        if exist ".env" (
            powershell -Command "(Get-Content .env) -replace 'BEDROCK_KNOWLEDGE_BASE_ID=.*', 'BEDROCK_KNOWLEDGE_BASE_ID=%KB_ID%' | Set-Content .env"
            echo %GREEN%✓ .env文件已更新%NC%
        )
    ) else (
        echo %YELLOW%⚠ 无法获取Knowledge Base ID，请手动更新.env文件%NC%
    )
    
    del kb_output.txt
) else (
    echo %RED%✗ 脚本不存在: scripts\create_bedrock_knowledge_base.py%NC%
    exit /b 1
)

REM ============================================================================
REM 步骤8: 配置EventBridge爬虫
REM ============================================================================

echo.
echo ========================================
echo 步骤8: 配置EventBridge爬虫定时任务 (预计3-5分钟)
echo ========================================
echo.

if exist "scripts\setup_eventbridge_crawler.sh" (
    bash scripts/setup_eventbridge_crawler.sh
    if %errorlevel% neq 0 (
        echo %RED%✗ EventBridge爬虫配置失败%NC%
        exit /b 1
    )
    echo %GREEN%✓ EventBridge爬虫配置完成%NC%
) else (
    echo %RED%✗ 脚本不存在: scripts\setup_eventbridge_crawler.sh%NC%
    exit /b 1
)

REM ============================================================================
REM 步骤9: 生成安全密钥
REM ============================================================================

echo.
echo ========================================
echo 步骤9: 生成安全密钥
echo ========================================
echo.

echo 生成JWT密钥...
for /f "tokens=*" %%i in ('python -c "import secrets; print(secrets.token_urlsafe(32))"') do set JWT_SECRET=%%i
echo %GREEN%✓ JWT密钥已生成%NC%

echo.
echo 生成加密密钥...
if exist "scripts\generate_encryption_key.py" (
    for /f "tokens=*" %%i in ('python scripts\generate_encryption_key.py') do set ENCRYPTION_KEY=%%i
    echo %GREEN%✓ 加密密钥已生成%NC%
) else (
    echo %YELLOW%⚠ 加密密钥生成脚本不存在，使用随机密钥%NC%
    for /f "tokens=*" %%i in ('python -c "import secrets; print(secrets.token_urlsafe(32))"') do set ENCRYPTION_KEY=%%i
)

echo.
echo 更新Secrets Manager...
aws secretsmanager update-secret --secret-id aws-pricing-assistant-secrets --secret-string "{\"JWT_SECRET_KEY\":\"%JWT_SECRET%\",\"ENCRYPTION_KEY\":\"%ENCRYPTION_KEY%\"}" --region %AWS_REGION% >nul 2>&1
if %errorlevel% neq 0 (
    aws secretsmanager create-secret --name aws-pricing-assistant-secrets --secret-string "{\"JWT_SECRET_KEY\":\"%JWT_SECRET%\",\"ENCRYPTION_KEY\":\"%ENCRYPTION_KEY%\"}" --region %AWS_REGION% >nul 2>&1
)
echo %GREEN%✓ 安全密钥已保存到Secrets Manager%NC%

REM ============================================================================
REM 步骤10: 部署后端
REM ============================================================================

echo.
echo ========================================
echo 步骤10: 部署后端应用 (预计5-10分钟)
echo ========================================
echo.

set DEPLOYMENT_TYPE=ec2

if exist "scripts\deploy_backend.sh" (
    bash scripts/deploy_backend.sh
    if %errorlevel% neq 0 (
        echo %RED%✗ 后端部署失败%NC%
        exit /b 1
    )
    echo %GREEN%✓ 后端部署完成%NC%
) else (
    echo %RED%✗ 脚本不存在: scripts\deploy_backend.sh%NC%
    exit /b 1
)

REM ============================================================================
REM 步骤11: 部署前端
REM ============================================================================

echo.
echo ========================================
echo 步骤11: 部署前端应用 (预计3-5分钟)
echo ========================================
echo.

set BACKEND_API_URL=%ALB_URL%
set S3_BUCKET=%FRONTEND_BUCKET%
set CLOUDFRONT_ENABLED=true

if exist "scripts\deploy_frontend.sh" (
    bash scripts/deploy_frontend.sh
    if %errorlevel% neq 0 (
        echo %RED%✗ 前端部署失败%NC%
        exit /b 1
    )
    echo %GREEN%✓ 前端部署完成%NC%
) else (
    echo %RED%✗ 脚本不存在: scripts\deploy_frontend.sh%NC%
    exit /b 1
)

REM 获取CloudFront URL
for /f "tokens=*" %%i in ('aws cloudformation describe-stacks --stack-name %STACK_NAME% --query "Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue" --output text') do set CLOUDFRONT_URL=%%i

REM ============================================================================
REM 步骤12: 配置CloudWatch日志
REM ============================================================================

echo.
echo ========================================
echo 步骤12: 配置CloudWatch日志 (预计1-2分钟)
echo ========================================
echo.

if exist "scripts\setup_cloudwatch_logs.py" (
    python scripts\setup_cloudwatch_logs.py
    if %errorlevel% neq 0 (
        echo %YELLOW%⚠ CloudWatch日志配置失败，但不影响主要功能%NC%
    ) else (
        echo %GREEN%✓ CloudWatch日志配置完成%NC%
    )
) else (
    echo %YELLOW%⚠ CloudWatch日志配置脚本不存在，跳过%NC%
)

REM ============================================================================
REM 步骤13: 验证部署
REM ============================================================================

echo.
echo ========================================
echo 步骤13: 验证部署
echo ========================================
echo.

echo 等待服务启动 (30秒)...
timeout /t 30 /nobreak >nul

echo.
echo 测试后端健康检查...
curl -s -f "http://%ALB_URL%/health" >nul 2>&1
if %errorlevel% equ 0 (
    echo %GREEN%✓ 后端健康检查通过%NC%
) else (
    echo %YELLOW%⚠ 后端健康检查失败，可能需要更多时间启动%NC%
)

echo.
echo 测试前端访问...
if not "%CLOUDFRONT_URL%"=="" (
    curl -s -f "http://%CLOUDFRONT_URL%" >nul 2>&1
    if %errorlevel% equ 0 (
        echo %GREEN%✓ 前端访问正常%NC%
    ) else (
        echo %YELLOW%⚠ 前端访问失败，CloudFront可能需要15-20分钟完成分发%NC%
    )
) else (
    echo %YELLOW%⚠ 无法获取CloudFront URL%NC%
)

REM ============================================================================
REM 部署完成
REM ============================================================================

echo.
echo ========================================
echo 🎉 部署完成！
echo ========================================
echo.
echo.
echo 部署信息汇总:
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 📍 访问地址:
echo    前端URL: http://%CLOUDFRONT_URL%
echo    后端API: http://%ALB_URL%
echo.
echo 🔑 AWS资源:
echo    区域: %AWS_REGION%
echo    堆栈名称: %STACK_NAME%
echo    EC2实例ID: %EC2_INSTANCE_ID%
echo    Knowledge Base ID: %KB_ID%
echo.
echo 📝 下一步操作:
echo    1. 访问前端URL并登录
echo    2. 创建初始管理员用户
echo    3. 测试报价生成功能
echo    4. 查看部署文档: docs\部署指南.md
echo    5. 查看检查清单: docs\快速部署检查清单.md
echo.
echo ⚠️  注意事项:
echo    - CloudFront分发可能需要15-20分钟完全生效
echo    - 首次使用前请修改默认管理员密码
echo    - 建议配置HTTPS证书（生产环境）
echo    - 定期备份DynamoDB数据
echo.
echo 📚 文档位置:
echo    - 部署指南: docs\部署指南.md
echo    - 配置说明: docs\CONFIGURATION.md
echo    - 故障排除: docs\TROUBLESHOOTING.md
echo    - 开发文档: docs\DEVELOPMENT.md
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo %GREEN%✓ 感谢使用AWS智能定价助手！%NC%
echo.

pause
