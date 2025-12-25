#!/bin/bash

###############################################################################
# AWS智能定价助手 - 一键部署脚本
# 
# 此脚本将自动完成所有部署步骤
# 使用方法: ./一键部署.sh
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 未安装，请先安装"
        exit 1
    fi
}

# 检查AWS凭证
check_aws_credentials() {
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS凭证未配置或无效，请运行 'aws configure'"
        exit 1
    fi
}

###############################################################################
# 主程序开始
###############################################################################

print_header "AWS智能定价助手 - 一键部署"

print_info "开始部署流程..."
echo ""

###############################################################################
# 步骤1: 环境检查
###############################################################################

print_header "步骤1: 环境检查"

print_info "检查必需工具..."
check_command aws
check_command python3
check_command git
print_success "所有必需工具已安装"

print_info "检查AWS凭证..."
check_aws_credentials
print_success "AWS凭证有效"

print_info "检查Python版本..."
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    print_error "Python版本需要 >= 3.11，当前版本: $PYTHON_VERSION"
    exit 1
fi
print_success "Python版本符合要求: $PYTHON_VERSION"

###############################################################################
# 步骤2: 配置参数
###############################################################################

print_header "步骤2: 配置部署参数"

# 读取或设置默认值
read -p "请输入AWS区域 [默认: us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}
export AWS_REGION

read -p "请输入CloudFormation堆栈名称 [默认: aws-pricing-assistant]: " STACK_NAME
STACK_NAME=${STACK_NAME:-aws-pricing-assistant}
export STACK_NAME

read -p "请输入环境名称 [默认: production]: " ENVIRONMENT
ENVIRONMENT=${ENVIRONMENT:-production}
export ENVIRONMENT

read -p "请输入EC2实例类型 [默认: t3.medium]: " INSTANCE_TYPE
INSTANCE_TYPE=${INSTANCE_TYPE:-t3.medium}
export INSTANCE_TYPE

read -p "请输入EC2密钥对名称 [默认: aws-pricing-assistant-key]: " KEY_PAIR_NAME
KEY_PAIR_NAME=${KEY_PAIR_NAME:-aws-pricing-assistant-key}
export KEY_PAIR_NAME

print_success "配置参数已设置"
echo ""
echo "部署配置:"
echo "  AWS区域: $AWS_REGION"
echo "  堆栈名称: $STACK_NAME"
echo "  环境: $ENVIRONMENT"
echo "  实例类型: $INSTANCE_TYPE"
echo "  密钥对: $KEY_PAIR_NAME"
echo ""

read -p "确认以上配置并继续部署? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    print_warning "部署已取消"
    exit 0
fi

###############################################################################
# 步骤3: 检查EC2密钥对
###############################################################################

print_header "步骤3: 检查EC2密钥对"

if aws ec2 describe-key-pairs --key-names $KEY_PAIR_NAME &> /dev/null; then
    print_success "密钥对 $KEY_PAIR_NAME 已存在"
else
    print_warning "密钥对 $KEY_PAIR_NAME 不存在，正在创建..."
    aws ec2 create-key-pair \
        --key-name $KEY_PAIR_NAME \
        --query 'KeyMaterial' \
        --output text > ~/.ssh/${KEY_PAIR_NAME}.pem
    chmod 400 ~/.ssh/${KEY_PAIR_NAME}.pem
    print_success "密钥对已创建并保存到 ~/.ssh/${KEY_PAIR_NAME}.pem"
fi

###############################################################################
# 步骤4: 检查Bedrock访问权限
###############################################################################

print_header "步骤4: 检查Bedrock访问权限"

print_info "检查Bedrock模型访问权限..."
if aws bedrock list-foundation-models --region $AWS_REGION &> /dev/null; then
    print_success "Bedrock访问权限正常"
else
    print_error "无法访问Bedrock服务"
    print_warning "请确保:"
    print_warning "1. 您的AWS账户已启用Bedrock服务"
    print_warning "2. 已申请Claude 3.5 Sonnet模型访问权限"
    print_warning "3. 在AWS控制台 → Bedrock → Model access 中申请"
    exit 1
fi

###############################################################################
# 步骤5: 部署基础设施
###############################################################################

print_header "步骤5: 部署AWS基础设施 (预计10-15分钟)"

print_info "开始部署CloudFormation堆栈..."
if [ -f "./scripts/deploy_infrastructure.sh" ]; then
    ./scripts/deploy_infrastructure.sh
    print_success "基础设施部署完成"
else
    print_error "部署脚本不存在: ./scripts/deploy_infrastructure.sh"
    exit 1
fi

# 获取CloudFormation输出
print_info "获取部署输出..."
ALB_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerURL`].OutputValue' \
    --output text)
FRONTEND_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucket`].OutputValue' \
    --output text)
EC2_INSTANCE_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`EC2InstanceId`].OutputValue' \
    --output text)

print_success "基础设施部署完成"
echo "  ALB URL: $ALB_URL"
echo "  前端存储桶: $FRONTEND_BUCKET"
echo "  EC2实例ID: $EC2_INSTANCE_ID"

###############################################################################
# 步骤6: 创建DynamoDB表
###############################################################################

print_header "步骤6: 创建DynamoDB表 (预计2-3分钟)"

if [ -f "./scripts/setup_dynamodb.sh" ]; then
    ./scripts/setup_dynamodb.sh
    print_success "DynamoDB表创建完成"
else
    print_error "脚本不存在: ./scripts/setup_dynamodb.sh"
    exit 1
fi

###############################################################################
# 步骤7: 设置Bedrock Knowledge Base
###############################################################################

print_header "步骤7: 设置Bedrock Knowledge Base (预计5-10分钟)"

print_info "上传知识库数据到S3..."
if [ -f "./scripts/setup_knowledge_base_s3.py" ]; then
    python3 ./scripts/setup_knowledge_base_s3.py
    print_success "知识库数据上传完成"
else
    print_error "脚本不存在: ./scripts/setup_knowledge_base_s3.py"
    exit 1
fi

print_info "创建Bedrock Knowledge Base..."
if [ -f "./scripts/create_bedrock_knowledge_base.py" ]; then
    KB_OUTPUT=$(python3 ./scripts/create_bedrock_knowledge_base.py)
    KB_ID=$(echo "$KB_OUTPUT" | grep "Knowledge Base ID:" | cut -d':' -f2 | tr -d ' ')
    
    if [ -n "$KB_ID" ]; then
        print_success "Knowledge Base创建完成"
        echo "  Knowledge Base ID: $KB_ID"
        
        # 更新.env文件
        if [ -f ".env" ]; then
            sed -i.bak "s/BEDROCK_KNOWLEDGE_BASE_ID=.*/BEDROCK_KNOWLEDGE_BASE_ID=$KB_ID/" .env
            print_success ".env文件已更新"
        fi
    else
        print_warning "无法获取Knowledge Base ID，请手动更新.env文件"
    fi
else
    print_error "脚本不存在: ./scripts/create_bedrock_knowledge_base.py"
    exit 1
fi

###############################################################################
# 步骤8: 配置EventBridge爬虫
###############################################################################

print_header "步骤8: 配置EventBridge爬虫定时任务 (预计3-5分钟)"

if [ -f "./scripts/setup_eventbridge_crawler.sh" ]; then
    ./scripts/setup_eventbridge_crawler.sh
    print_success "EventBridge爬虫配置完成"
else
    print_error "脚本不存在: ./scripts/setup_eventbridge_crawler.sh"
    exit 1
fi

###############################################################################
# 步骤9: 生成安全密钥
###############################################################################

print_header "步骤9: 生成安全密钥"

print_info "生成JWT密钥..."
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
print_success "JWT密钥已生成"

print_info "生成加密密钥..."
if [ -f "./scripts/generate_encryption_key.py" ]; then
    ENCRYPTION_KEY=$(python3 ./scripts/generate_encryption_key.py)
    print_success "加密密钥已生成"
else
    print_warning "加密密钥生成脚本不存在，使用随机密钥"
    ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
fi

print_info "更新Secrets Manager..."
aws secretsmanager update-secret \
    --secret-id aws-pricing-assistant-secrets \
    --secret-string "{\"JWT_SECRET_KEY\":\"$JWT_SECRET\",\"ENCRYPTION_KEY\":\"$ENCRYPTION_KEY\"}" \
    --region $AWS_REGION &> /dev/null || \
aws secretsmanager create-secret \
    --name aws-pricing-assistant-secrets \
    --secret-string "{\"JWT_SECRET_KEY\":\"$JWT_SECRET\",\"ENCRYPTION_KEY\":\"$ENCRYPTION_KEY\"}" \
    --region $AWS_REGION &> /dev/null

print_success "安全密钥已保存到Secrets Manager"

###############################################################################
# 步骤10: 部署后端
###############################################################################

print_header "步骤10: 部署后端应用 (预计5-10分钟)"

export DEPLOYMENT_TYPE=ec2
export EC2_INSTANCE_ID=$EC2_INSTANCE_ID

if [ -f "./scripts/deploy_backend.sh" ]; then
    ./scripts/deploy_backend.sh
    print_success "后端部署完成"
else
    print_error "脚本不存在: ./scripts/deploy_backend.sh"
    exit 1
fi

###############################################################################
# 步骤11: 部署前端
###############################################################################

print_header "步骤11: 部署前端应用 (预计3-5分钟)"

export BACKEND_API_URL=$ALB_URL
export S3_BUCKET=$FRONTEND_BUCKET
export CLOUDFRONT_ENABLED=true

if [ -f "./scripts/deploy_frontend.sh" ]; then
    ./scripts/deploy_frontend.sh
    print_success "前端部署完成"
else
    print_error "脚本不存在: ./scripts/deploy_frontend.sh"
    exit 1
fi

# 获取CloudFront URL
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
    --output text)

###############################################################################
# 步骤12: 配置CloudWatch日志
###############################################################################

print_header "步骤12: 配置CloudWatch日志 (预计1-2分钟)"

if [ -f "./scripts/setup_cloudwatch_logs.py" ]; then
    python3 ./scripts/setup_cloudwatch_logs.py
    print_success "CloudWatch日志配置完成"
else
    print_warning "CloudWatch日志配置脚本不存在，跳过"
fi

###############################################################################
# 步骤13: 验证部署
###############################################################################

print_header "步骤13: 验证部署"

print_info "等待服务启动 (30秒)..."
sleep 30

print_info "测试后端健康检查..."
if curl -s -f "http://$ALB_URL/health" > /dev/null; then
    print_success "后端健康检查通过"
else
    print_warning "后端健康检查失败，可能需要更多时间启动"
fi

print_info "测试前端访问..."
if [ -n "$CLOUDFRONT_URL" ]; then
    if curl -s -f "http://$CLOUDFRONT_URL" > /dev/null; then
        print_success "前端访问正常"
    else
        print_warning "前端访问失败，CloudFront可能需要15-20分钟完成分发"
    fi
else
    print_warning "无法获取CloudFront URL"
fi

###############################################################################
# 部署完成
###############################################################################

print_header "🎉 部署完成！"

echo ""
echo "部署信息汇总:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 访问地址:"
echo "   前端URL: http://$CLOUDFRONT_URL"
echo "   后端API: http://$ALB_URL"
echo ""
echo "🔑 AWS资源:"
echo "   区域: $AWS_REGION"
echo "   堆栈名称: $STACK_NAME"
echo "   EC2实例ID: $EC2_INSTANCE_ID"
echo "   Knowledge Base ID: $KB_ID"
echo ""
echo "📝 下一步操作:"
echo "   1. 访问前端URL并登录"
echo "   2. 创建初始管理员用户"
echo "   3. 测试报价生成功能"
echo "   4. 查看部署文档: docs/部署指南.md"
echo "   5. 查看检查清单: docs/快速部署检查清单.md"
echo ""
echo "⚠️  注意事项:"
echo "   - CloudFront分发可能需要15-20分钟完全生效"
echo "   - 首次使用前请修改默认管理员密码"
echo "   - 建议配置HTTPS证书（生产环境）"
echo "   - 定期备份DynamoDB数据"
echo ""
echo "📚 文档位置:"
echo "   - 部署指南: docs/部署指南.md"
echo "   - 配置说明: docs/CONFIGURATION.md"
echo "   - 故障排除: docs/TROUBLESHOOTING.md"
echo "   - 开发文档: docs/DEVELOPMENT.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

print_success "感谢使用AWS智能定价助手！"
echo ""
