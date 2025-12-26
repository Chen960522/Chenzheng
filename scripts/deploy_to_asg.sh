#!/bin/bash

# AWS Pricing Assistant - Deploy to Auto Scaling Group
# 将后端应用部署到 ASG 中的所有实例

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
AWS_REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${STACK_NAME:-aws-pricing-assistant}"
REPO_URL="${REPO_URL:-https://github.com/your-repo/aws-pricing-assistant.git}"

echo -e "${GREEN}=== 部署后端应用到 Auto Scaling Group ===${NC}"
echo "AWS Region: $AWS_REGION"
echo "Stack Name: $STACK_NAME"
echo ""

# 打印信息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI 未安装"
    exit 1
fi

# 获取 ASG 名称
print_info "获取 Auto Scaling Group 名称..."
ASG_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`AutoScalingGroupName`].OutputValue' \
    --output text \
    --region "$AWS_REGION" 2>/dev/null || echo "")

if [ -z "$ASG_NAME" ]; then
    ASG_NAME="${STACK_NAME}-asg"
    print_warning "无法从 CloudFormation 获取 ASG 名称，使用默认值: $ASG_NAME"
fi

print_info "Auto Scaling Group: $ASG_NAME"

# 获取 ASG 中的所有健康实例
print_info "获取 ASG 中的健康实例..."
INSTANCE_IDS=$(aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names "$ASG_NAME" \
    --query 'AutoScalingGroups[0].Instances[?HealthStatus==`Healthy`].InstanceId' \
    --output text \
    --region "$AWS_REGION")

if [ -z "$INSTANCE_IDS" ]; then
    print_error "未找到健康的实例"
    exit 1
fi

INSTANCE_COUNT=$(echo "$INSTANCE_IDS" | wc -w)
print_info "找到 $INSTANCE_COUNT 个健康实例: $INSTANCE_IDS"

# 获取实例的公网 IP
print_info "获取实例 IP 地址..."
INSTANCE_IPS=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_IDS \
    --query 'Reservations[].Instances[].PublicIpAddress' \
    --output text \
    --region "$AWS_REGION")

if [ -z "$INSTANCE_IPS" ]; then
    print_error "无法获取实例 IP 地址"
    exit 1
fi

print_info "实例 IP: $INSTANCE_IPS"

# 部署到每个实例
print_info "开始部署到所有实例..."
FAILED_COUNT=0
SUCCESS_COUNT=0

for IP in $INSTANCE_IPS; do
    echo ""
    print_info "========================================="
    print_info "部署到实例: $IP"
    print_info "========================================="
    
    # SSH 部署
    if ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 ec2-user@$IP << 'ENDSSH'
        set -e
        
        echo "1. 创建应用目录..."
        sudo mkdir -p /opt/aws-pricing-assistant
        sudo chown ec2-user:ec2-user /opt/aws-pricing-assistant
        
        echo "2. 克隆或更新代码..."
        cd /opt/aws-pricing-assistant
        if [ -d ".git" ]; then
            echo "   更新现有代码..."
            git pull origin main || git pull
        else
            echo "   克隆代码仓库..."
            git clone https://github.com/Chen960522/Chenzheng.git . || {
                echo "   克隆失败，尝试初始化..."
                git init
                git remote add origin https://github.com/Chen960522/Chenzheng.git
                git pull origin main
            }
        fi
        
        echo "3. 安装 Python 依赖..."
        python3 -m pip install --user -r requirements.txt || echo "   依赖安装可能有警告，继续..."
        
        echo "4. 配置环境变量..."
        if [ ! -f ".env" ]; then
            cp .env.example .env 2>/dev/null || echo "   .env.example 不存在，跳过"
        fi
        
        echo "5. 创建 systemd 服务..."
        sudo tee /etc/systemd/system/pricing-assistant.service > /dev/null << 'EOF'
[Unit]
Description=AWS Pricing Assistant Backend API
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/aws-pricing-assistant
Environment="PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/ec2-user/.local/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        echo "6. 启动服务..."
        sudo systemctl daemon-reload
        sudo systemctl enable pricing-assistant
        sudo systemctl restart pricing-assistant
        
        echo "7. 等待服务启动..."
        sleep 5
        
        echo "8. 检查服务状态..."
        sudo systemctl status pricing-assistant --no-pager || true
        
        echo ""
        echo "✓ 部署完成！"
ENDSSH
    then
        print_info "✓ 实例 $IP 部署成功"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        print_error "✗ 实例 $IP 部署失败"
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

echo ""
print_info "========================================="
print_info "部署总结"
print_info "========================================="
print_info "总实例数: $INSTANCE_COUNT"
print_info "成功: $SUCCESS_COUNT"
print_info "失败: $FAILED_COUNT"

# 验证部署
echo ""
print_info "验证部署..."

# 获取 ALB DNS
ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text \
    --region "$AWS_REGION" 2>/dev/null || echo "")

if [ -n "$ALB_DNS" ]; then
    print_info "等待 5 秒让服务完全启动..."
    sleep 5
    
    print_info "测试 ALB 健康检查: http://$ALB_DNS/health"
    if curl -f -s "http://$ALB_DNS/health" > /dev/null 2>&1; then
        print_info "✓ 健康检查通过！"
        echo ""
        print_info "========================================="
        print_info "部署成功！"
        print_info "========================================="
        print_info "API URL: http://$ALB_DNS"
        print_info "API 文档: http://$ALB_DNS/docs"
        print_info "健康检查: http://$ALB_DNS/health"
    else
        print_warning "健康检查失败，服务可能还在启动中..."
        print_info "请稍后手动检查: curl http://$ALB_DNS/health"
    fi
else
    print_warning "无法获取 ALB DNS，请手动验证"
fi

# 检查目标组健康状态
print_info ""
print_info "检查目标组健康状态..."
TG_ARN=$(aws elbv2 describe-target-groups \
    --names "${STACK_NAME}-tg" \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text \
    --region "$AWS_REGION" 2>/dev/null || echo "")

if [ -n "$TG_ARN" ]; then
    aws elbv2 describe-target-health \
        --target-group-arn "$TG_ARN" \
        --query 'TargetHealthDescriptions[].[Target.Id,TargetHealth.State,TargetHealth.Reason]' \
        --output table \
        --region "$AWS_REGION"
fi

if [ $FAILED_COUNT -gt 0 ]; then
    print_warning "部分实例部署失败，请检查日志"
    exit 1
fi

print_info ""
print_info "所有实例部署成功！"
