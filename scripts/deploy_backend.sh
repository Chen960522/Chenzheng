#!/bin/bash

# AWS Pricing Assistant - Backend Deployment Script
# This script deploys the FastAPI backend to AWS EC2/ECS

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-ec2}"  # ec2 or ecs
AWS_REGION="${AWS_REGION:-us-east-1}"
APP_NAME="aws-pricing-assistant"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo -e "${GREEN}=== AWS Pricing Assistant Backend Deployment ===${NC}"
echo "Deployment Type: $DEPLOYMENT_TYPE"
echo "AWS Region: $AWS_REGION"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi
    
    # Check Docker (for ECS deployment)
    if [ "$DEPLOYMENT_TYPE" = "ecs" ]; then
        if ! command -v docker &> /dev/null; then
            print_error "Docker not found. Please install it first."
            exit 1
        fi
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    print_info "Prerequisites check passed!"
}

# Deploy to EC2
deploy_to_ec2() {
    print_info "Deploying to EC2..."
    
    # Get EC2 instance ID from environment or prompt
    if [ -z "$EC2_INSTANCE_ID" ]; then
        print_error "EC2_INSTANCE_ID environment variable not set."
        echo "Please set it to your target EC2 instance ID:"
        echo "export EC2_INSTANCE_ID=i-xxxxxxxxxxxxxxxxx"
        exit 1
    fi
    
    print_info "Target EC2 Instance: $EC2_INSTANCE_ID"
    
    # Create deployment package
    print_info "Creating deployment package..."
    rm -rf dist/
    mkdir -p dist/
    
    # Copy application files
    cp -r src/ dist/
    cp -r frontend/ dist/
    cp -r scripts/ dist/
    cp requirements.txt dist/
    cp .env dist/ 2>/dev/null || print_warning ".env file not found, using .env.example"
    [ ! -f dist/.env ] && cp .env.example dist/.env
    
    # Create deployment archive
    cd dist/
    tar -czf ../backend-deployment.tar.gz .
    cd ..
    
    print_info "Deployment package created: backend-deployment.tar.gz"
    
    # Upload to EC2
    print_info "Uploading to EC2 instance..."
    aws ec2-instance-connect send-ssh-public-key \
        --instance-id "$EC2_INSTANCE_ID" \
        --instance-os-user ec2-user \
        --ssh-public-key file://~/.ssh/id_rsa.pub \
        --region "$AWS_REGION" || print_warning "EC2 Instance Connect not available, using standard SSH"
    
    # Get EC2 public IP
    EC2_IP=$(aws ec2 describe-instances \
        --instance-ids "$EC2_INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region "$AWS_REGION")
    
    print_info "EC2 Instance IP: $EC2_IP"
    
    # Copy deployment package
    scp -o StrictHostKeyChecking=no backend-deployment.tar.gz ec2-user@$EC2_IP:/tmp/
    
    # Deploy on EC2
    ssh -o StrictHostKeyChecking=no ec2-user@$EC2_IP << 'ENDSSH'
        set -e
        
        # Create application directory
        sudo mkdir -p /opt/aws-pricing-assistant
        sudo chown ec2-user:ec2-user /opt/aws-pricing-assistant
        
        # Extract deployment package
        cd /opt/aws-pricing-assistant
        tar -xzf /tmp/backend-deployment.tar.gz
        rm /tmp/backend-deployment.tar.gz
        
        # Install Python dependencies
        python3 -m pip install --user -r requirements.txt
        
        # Create systemd service
        sudo tee /etc/systemd/system/pricing-assistant.service > /dev/null << 'EOF'
[Unit]
Description=AWS Pricing Assistant API
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
        
        # Reload systemd and start service
        sudo systemctl daemon-reload
        sudo systemctl enable pricing-assistant
        sudo systemctl restart pricing-assistant
        
        echo "Backend deployed successfully!"
        sudo systemctl status pricing-assistant --no-pager
ENDSSH
    
    print_info "Backend deployed to EC2 successfully!"
    print_info "API URL: http://$EC2_IP:$BACKEND_PORT"
    print_info "API Docs: http://$EC2_IP:$BACKEND_PORT/docs"
}

# Deploy to ECS
deploy_to_ecs() {
    print_info "Deploying to ECS..."
    
    # Get or create ECR repository
    ECR_REPO_NAME="$APP_NAME-backend"
    print_info "Checking ECR repository: $ECR_REPO_NAME"
    
    ECR_REPO_URI=$(aws ecr describe-repositories \
        --repository-names "$ECR_REPO_NAME" \
        --region "$AWS_REGION" \
        --query 'repositories[0].repositoryUri' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$ECR_REPO_URI" ]; then
        print_info "Creating ECR repository..."
        ECR_REPO_URI=$(aws ecr create-repository \
            --repository-name "$ECR_REPO_NAME" \
            --region "$AWS_REGION" \
            --query 'repository.repositoryUri' \
            --output text)
    fi
    
    print_info "ECR Repository: $ECR_REPO_URI"
    
    # Login to ECR
    print_info "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "${ECR_REPO_URI%%/*}"
    
    # Build Docker image
    print_info "Building Docker image..."
    docker build -t "$APP_NAME-backend" -f Dockerfile .
    
    # Tag and push image
    IMAGE_TAG="latest"
    docker tag "$APP_NAME-backend:latest" "$ECR_REPO_URI:$IMAGE_TAG"
    
    print_info "Pushing image to ECR..."
    docker push "$ECR_REPO_URI:$IMAGE_TAG"
    
    # Create or update ECS task definition
    print_info "Creating ECS task definition..."
    
    TASK_FAMILY="$APP_NAME-backend"
    TASK_DEFINITION=$(cat <<EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "$ECR_REPO_URI:$IMAGE_TAG",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "AWS_REGION", "value": "$AWS_REGION"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$APP_NAME-backend",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF
)
    
    echo "$TASK_DEFINITION" > /tmp/task-definition.json
    
    aws ecs register-task-definition \
        --cli-input-json file:///tmp/task-definition.json \
        --region "$AWS_REGION" > /dev/null
    
    print_info "Task definition registered: $TASK_FAMILY"
    
    # Check if ECS cluster exists
    ECS_CLUSTER="${ECS_CLUSTER:-$APP_NAME-cluster}"
    if ! aws ecs describe-clusters --clusters "$ECS_CLUSTER" --region "$AWS_REGION" | grep -q "ACTIVE"; then
        print_info "Creating ECS cluster: $ECS_CLUSTER"
        aws ecs create-cluster --cluster-name "$ECS_CLUSTER" --region "$AWS_REGION" > /dev/null
    fi
    
    print_info "ECS deployment prepared!"
    print_info "Next steps:"
    print_info "1. Create ECS service with ALB"
    print_info "2. Configure target group and health checks"
    print_info "3. Update service to use new task definition"
    print_info ""
    print_info "Example command to create service:"
    echo "aws ecs create-service \\"
    echo "  --cluster $ECS_CLUSTER \\"
    echo "  --service-name $APP_NAME-backend-service \\"
    echo "  --task-definition $TASK_FAMILY \\"
    echo "  --desired-count 2 \\"
    echo "  --launch-type FARGATE \\"
    echo "  --network-configuration \"awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}\" \\"
    echo "  --load-balancers \"targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=backend,containerPort=8000\""
}

# Main deployment flow
main() {
    check_prerequisites
    
    case "$DEPLOYMENT_TYPE" in
        ec2)
            deploy_to_ec2
            ;;
        ecs)
            deploy_to_ecs
            ;;
        *)
            print_error "Invalid deployment type: $DEPLOYMENT_TYPE"
            print_error "Supported types: ec2, ecs"
            exit 1
            ;;
    esac
    
    print_info "Deployment completed successfully!"
}

# Run main function
main
