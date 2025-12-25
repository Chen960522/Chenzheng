#!/usr/bin/env python3
"""
Script to run crawler manually and verify checkpoint requirements.

This script:
1. Runs the web crawler to populate the database
2. Verifies data is stored correctly in DynamoDB
3. Tests Knowledge Base queries
4. Generates a verification report
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.crawlers.web_crawler import WebCrawler
from src.services.cloud_service_service import CloudServiceService
from src.services.knowledge_base_service import KnowledgeBaseService
from src.utils.logger import get_logger

logger = get_logger(__name__)


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def run_crawler() -> Dict[str, Any]:
    """Run the web crawler and return results."""
    print_section("STEP 1: Running Web Crawler")
    
    try:
        crawler = WebCrawler()
        results = crawler.crawl_all_providers()
        
        print("✓ Crawler completed successfully")
        print(f"\nCrawling Summary:")
        print(f"  - Duration: {results['report']['duration_seconds']:.2f} seconds")
        print(f"  - Successful providers: {results['report']['summary']['successful_providers']}/{results['report']['summary']['total_providers']}")
        print(f"  - New services: {results['report']['summary']['total_new_services']}")
        print(f"  - Updated services: {results['report']['summary']['total_updated_services']}")
        print(f"  - Total services crawled: {results['report']['summary']['total_services_crawled']}")
        print(f"  - Low quality services: {results['report']['summary']['total_low_quality_services']}")
        
        if results['report']['failed_providers']:
            print(f"\n⚠ Failed providers: {', '.join(results['report']['failed_providers'])}")
        
        return results
        
    except Exception as e:
        print(f"✗ Crawler failed: {e}")
        logger.error(f"Crawler failed: {e}", exc_info=True)
        return None


def verify_database_storage(crawler_results: Dict[str, Any]) -> bool:
    """Verify data is stored correctly in DynamoDB."""
    print_section("STEP 2: Verifying DynamoDB Storage")
    
    try:
        db_service = CloudServiceService()
        
        # Check each provider
        all_verified = True
        for provider in ['alibaba', 'huawei', 'tencent', 'gcp', 'azure']:
            print(f"\nVerifying {provider}...")
            
            # Get services for this provider
            services = db_service.list_cloud_services(provider=provider)
            
            if not services:
                print(f"  ⚠ No services found for {provider}")
                all_verified = False
                continue
            
            print(f"  ✓ Found {len(services)} services")
            
            # Verify first service has all required fields
            service = services[0]
            required_fields = [
                'service_id', 'provider', 'service_name', 'service_name_en',
                'service_category', 'description', 'specifications', 'features',
                'source_url', 'crawled_at', 'last_updated', 'data_quality_score'
            ]
            
            missing_fields = []
            for field in required_fields:
                if not hasattr(service, field) or getattr(service, field) is None:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"  ✗ Missing fields: {', '.join(missing_fields)}")
                all_verified = False
            else:
                print(f"  ✓ All required fields present")
            
            # Show sample service
            print(f"  Sample: {service.service_name_en} ({service.service_category})")
        
        if all_verified:
            print("\n✓ Database storage verification passed")
        else:
            print("\n⚠ Database storage verification completed with warnings")
        
        return all_verified
        
    except Exception as e:
        print(f"✗ Database verification failed: {e}")
        logger.error(f"Database verification failed: {e}", exc_info=True)
        return False


def test_knowledge_base() -> bool:
    """Test Knowledge Base queries."""
    print_section("STEP 3: Testing Knowledge Base Queries")
    
    try:
        kb_service = KnowledgeBaseService()
        
        # Test 1: Connection test
        print("Test 1: Connection test...")
        if kb_service.test_connection():
            print("  ✓ Connection successful")
        else:
            print("  ✗ Connection failed")
            return False
        
        # Test 2: Service mapping query
        print("\nTest 2: Service mapping query...")
        results = kb_service.query_service_mapping(
            provider='alibaba',
            service_name='ECS',
            specifications={'cpu': 2, 'memory': '4GB'}
        )
        
        if results:
            print(f"  ✓ Found {len(results)} mapping results")
            print(f"  Top result score: {results[0].score:.3f}")
            print(f"  Content preview: {results[0].content[:100]}...")
        else:
            print("  ⚠ No mapping results found")
        
        # Test 3: Pricing query
        print("\nTest 3: Pricing information query...")
        results = kb_service.query_pricing_info(
            aws_service='EC2',
            service_type='t3.micro',
            region='us-east-1'
        )
        
        if results:
            print(f"  ✓ Found {len(results)} pricing results")
            print(f"  Top result score: {results[0].score:.3f}")
            print(f"  Content preview: {results[0].content[:100]}...")
        else:
            print("  ⚠ No pricing results found")
        
        # Test 4: Service description query
        print("\nTest 4: Service description query...")
        results = kb_service.query_service_description('S3')
        
        if results:
            print(f"  ✓ Found {len(results)} description results")
            print(f"  Top result score: {results[0].score:.3f}")
            print(f"  Content preview: {results[0].content[:100]}...")
        else:
            print("  ⚠ No description results found")
        
        print("\n✓ Knowledge Base testing completed")
        return True
        
    except ValueError as e:
        print(f"✗ Knowledge Base not configured: {e}")
        print("  Please set BEDROCK_KNOWLEDGE_BASE_ID in .env file")
        return False
    except Exception as e:
        print(f"✗ Knowledge Base testing failed: {e}")
        logger.error(f"Knowledge Base testing failed: {e}", exc_info=True)
        return False


def run_all_tests() -> bool:
    """Run all tests and return overall status."""
    print_section("STEP 4: Running All Tests")
    
    try:
        import subprocess
        
        print("Running property tests...")
        result = subprocess.run(
            ['python', '-m', 'pytest', 'tests/property/test_crawler_properties.py', '-v'],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')),
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("✓ All property tests passed")
            return True
        else:
            print("✗ Some property tests failed")
            return False
            
    except Exception as e:
        print(f"✗ Test execution failed: {e}")
        logger.error(f"Test execution failed: {e}", exc_info=True)
        return False


def generate_report(
    crawler_results: Dict[str, Any],
    db_verified: bool,
    kb_tested: bool,
    tests_passed: bool
) -> Dict[str, Any]:
    """Generate final verification report."""
    print_section("CHECKPOINT VERIFICATION REPORT")
    
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'crawler': {
            'status': 'success' if crawler_results else 'failed',
            'results': crawler_results
        },
        'database': {
            'verified': db_verified,
            'status': 'passed' if db_verified else 'failed'
        },
        'knowledge_base': {
            'tested': kb_tested,
            'status': 'passed' if kb_tested else 'failed'
        },
        'tests': {
            'passed': tests_passed,
            'status': 'passed' if tests_passed else 'failed'
        },
        'overall_status': 'PASSED' if all([crawler_results, db_verified, kb_tested, tests_passed]) else 'FAILED'
    }
    
    # Print summary
    print("Checkpoint Status:")
    print(f"  1. Crawler execution: {'✓ PASSED' if crawler_results else '✗ FAILED'}")
    print(f"  2. Database verification: {'✓ PASSED' if db_verified else '✗ FAILED'}")
    print(f"  3. Knowledge Base testing: {'✓ PASSED' if kb_tested else '✗ FAILED'}")
    print(f"  4. All tests passing: {'✓ PASSED' if tests_passed else '✗ FAILED'}")
    print(f"\nOverall Status: {report['overall_status']}")
    
    # Save report to file
    report_file = f"checkpoint_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nReport saved to: {report_file}")
    
    return report


def main():
    """Main execution function."""
    print("\n" + "=" * 80)
    print("  AWS PRICING ASSISTANT - CHECKPOINT 6 VERIFICATION")
    print("  Task: Verify crawler and Knowledge Base")
    print("=" * 80)
    
    # Step 1: Run crawler
    crawler_results = run_crawler()
    
    # Step 2: Verify database storage
    db_verified = verify_database_storage(crawler_results) if crawler_results else False
    
    # Step 3: Test Knowledge Base
    kb_tested = test_knowledge_base()
    
    # Step 4: Run all tests
    tests_passed = run_all_tests()
    
    # Generate final report
    report = generate_report(crawler_results, db_verified, kb_tested, tests_passed)
    
    # Exit with appropriate code
    if report['overall_status'] == 'PASSED':
        print("\n✓ Checkpoint 6 verification PASSED")
        sys.exit(0)
    else:
        print("\n✗ Checkpoint 6 verification FAILED")
        print("\nPlease review the errors above and address any issues.")
        sys.exit(1)


if __name__ == '__main__':
    main()
