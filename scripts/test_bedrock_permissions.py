"""
Test Bedrock permissions to diagnose the CreateKnowledgeBase issue.
"""

import boto3
from botocore.exceptions import ClientError

def test_permissions():
    """Test various Bedrock permissions."""
    region = 'us-east-1'
    
    print("Testing Bedrock Permissions")
    print("=" * 70)
    print()
    
    # Test 1: STS Identity
    print("1. Testing AWS Identity...")
    try:
        sts = boto3.client('sts', region_name=region)
        identity = sts.get_caller_identity()
        print(f"   ✅ Account: {identity['Account']}")
        print(f"   ✅ User: {identity['Arn']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 2: List Knowledge Bases
    print("2. Testing bedrock-agent:ListKnowledgeBases...")
    try:
        bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        response = bedrock_agent.list_knowledge_bases()
        print(f"   ✅ Success! Found {len(response['knowledgeBaseSummaries'])} knowledge bases")
    except ClientError as e:
        print(f"   ❌ Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
    print()
    
    # Test 3: List Foundation Models
    print("3. Testing bedrock:ListFoundationModels...")
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        response = bedrock.list_foundation_models()
        print(f"   ✅ Success! Found {len(response['modelSummaries'])} models")
    except ClientError as e:
        print(f"   ❌ Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
    print()
    
    # Test 4: Get specific model
    print("4. Testing bedrock:GetFoundationModel...")
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        response = bedrock.get_foundation_model(
            modelIdentifier='amazon.titan-embed-text-v2:0'
        )
        print(f"   ✅ Success! Model: {response['modelDetails']['modelName']}")
    except ClientError as e:
        print(f"   ❌ Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
    print()
    
    # Test 5: Try to create Knowledge Base (the failing operation)
    print("5. Testing bedrock-agent:CreateKnowledgeBase...")
    try:
        bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        
        # Try with minimal parameters
        response = bedrock_agent.create_knowledge_base(
            name='test-kb-permissions-check',
            description='Test KB to check permissions',
            roleArn='',  # Let Bedrock create
            knowledgeBaseConfiguration={
                'type': 'VECTOR',
                'vectorKnowledgeBaseConfiguration': {
                    'embeddingModelArn': f'arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0'
                }
            },
            storageConfiguration={
                'type': 'OPENSEARCH_SERVERLESS',
                'opensearchServerlessConfiguration': {
                    'collectionArn': '',  # Let Bedrock create
                    'vectorIndexName': 'test-index',
                    'fieldMapping': {
                        'vectorField': 'vector',
                        'textField': 'text',
                        'metadataField': 'metadata'
                    }
                }
            }
        )
        
        kb_id = response['knowledgeBase']['knowledgeBaseId']
        print(f"   ✅ Success! Created KB: {kb_id}")
        print(f"   ⚠️  Remember to delete this test KB!")
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"   ❌ Error: {error_code}")
        print(f"   Message: {error_msg}")
        
        # Provide specific guidance based on error
        if error_code == 'AccessDeniedException':
            print()
            print("   🔍 Diagnosis:")
            print("   - You have AdministratorAccess but CreateKnowledgeBase is denied")
            print("   - This might be due to:")
            print("     1. Service Control Policy (SCP) restriction")
            print("     2. Permission boundary on your user")
            print("     3. Bedrock service not fully enabled in this region")
            print()
            print("   💡 Next steps:")
            print("   1. Check for SCPs: aws organizations list-policies-for-target")
            print("   2. Check permission boundary: aws iam get-user --user-name <your-user>")
            print("   3. Try creating KB via AWS Console to see if it works there")
    print()
    
    # Test 6: Check IAM permissions
    print("6. Testing IAM permissions...")
    try:
        iam = boto3.client('iam', region_name=region)
        user_name = identity['Arn'].split('/')[-1]
        
        # Get user details
        user = iam.get_user(UserName=user_name)
        if 'PermissionsBoundary' in user['User']:
            print(f"   ⚠️  Permission Boundary detected: {user['User']['PermissionsBoundary']['PermissionsBoundaryArn']}")
        else:
            print(f"   ✅ No permission boundary")
        
        # List attached policies
        policies = iam.list_attached_user_policies(UserName=user_name)
        print(f"   ✅ Attached policies:")
        for policy in policies['AttachedPolicies']:
            print(f"      - {policy['PolicyName']}")
            
    except ClientError as e:
        print(f"   ❌ Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
    print()
    
    print("=" * 70)
    print("Test completed!")
    print()

if __name__ == "__main__":
    test_permissions()
