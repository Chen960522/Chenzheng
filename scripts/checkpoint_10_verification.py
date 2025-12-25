#!/usr/bin/env python3
"""
Checkpoint 10: 验证核心组件
测试 Configuration Parser, Service Mapper, Price Calculator, Quote Generator
"""

import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# 设置 UTF-8 编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.service_config import ServiceConfig
from src.models.cloud_service import AWSServiceMapping
from src.models.pricing_result import PricingResult
from src.models.quote import Quote
from src.services.configuration_parser import ConfigurationParser
from src.services.service_mapper import ServiceMapper
from src.services.price_calculator import PriceCalculator
from src.services.quote_generator import QuoteGenerator


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")


def print_success(text: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")


def print_error(text: str):
    """打印错误消息"""
    print(f"{Colors.RED}[FAIL] {text}{Colors.RESET}")


def print_warning(text: str):
    """打印警告消息"""
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")


def test_configuration_parser():
    """测试配置解析器"""
    print_header("测试 1: Configuration Parser")
    
    parser = ConfigurationParser(bedrock_client=None)
    results = []
    
    # 测试 1.1: JSON 格式解析
    print_info("测试 1.1: JSON 格式解析")
    json_input = '''
    {
        "services": [
            {
                "provider": "alibaba",
                "service_type": "compute",
                "service_name": "ECS",
                "specifications": {
                    "instance_type": "ecs.c6.large",
                    "cpu": 2,
                    "memory": 4,
                    "storage": 100
                }
            }
        ]
    }
    '''
    try:
        configs = parser.parse(json_input, format_hint='json')
        if configs and len(configs) > 0:
            print_success(f"JSON 解析成功: 解析出 {len(configs)} 个服务")
            print(f"  - 服务: {configs[0].service_name}")
            print(f"  - 提供商: {configs[0].provider}")
            print(f"  - 规格: {configs[0].specifications}")
            results.append(True)
        else:
            print_error("JSON 解析失败: 未解析出服务")
            results.append(False)
    except Exception as e:
        print_error(f"JSON 解析异常: {e}")
        results.append(False)
    
    # 测试 1.2: YAML 格式解析
    print_info("\n测试 1.2: YAML 格式解析")
    yaml_input = '''
services:
  - provider: huawei
    service_type: storage
    service_name: OBS
    specifications:
      storage_class: standard
      capacity: 1000
    '''
    try:
        configs = parser.parse(yaml_input, format_hint='yaml')
        if configs and len(configs) > 0:
            print_success(f"YAML 解析成功: 解析出 {len(configs)} 个服务")
            print(f"  - 服务: {configs[0].service_name}")
            print(f"  - 提供商: {configs[0].provider}")
            results.append(True)
        else:
            print_error("YAML 解析失败: 未解析出服务")
            results.append(False)
    except Exception as e:
        print_error(f"YAML 解析异常: {e}")
        results.append(False)
    
    # 测试 1.3: CSV 格式解析
    print_info("\n测试 1.3: CSV 格式解析")
    csv_input = '''provider,service_type,service_name,cpu,memory,storage
tencent,compute,CVM,4,8,200'''
    try:
        configs = parser.parse(csv_input, format_hint='csv')
        if configs and len(configs) > 0:
            print_success(f"CSV 解析成功: 解析出 {len(configs)} 个服务")
            print(f"  - 服务: {configs[0].service_name}")
            print(f"  - 提供商: {configs[0].provider}")
            results.append(True)
        else:
            print_error("CSV 解析失败: 未解析出服务")
            results.append(False)
    except Exception as e:
        print_error(f"CSV 解析异常: {e}")
        results.append(False)
    
    # 测试 1.4: 多语言识别
    print_info("\n测试 1.4: 多语言服务名称识别")
    chinese_input = '''
    {
        "services": [
            {
                "provider": "alibaba",
                "service_type": "compute",
                "service_name": "云服务器ECS",
                "specifications": {"cpu": 2, "memory": 4}
            }
        ]
    }
    '''
    try:
        configs = parser.parse(chinese_input, format_hint='json')
        if configs and len(configs) > 0:
            print_success(f"中文服务名识别成功: {configs[0].service_name}")
            results.append(True)
        else:
            print_error("中文服务名识别失败")
            results.append(False)
    except Exception as e:
        print_error(f"中文服务名识别异常: {e}")
        results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n{Colors.BOLD}Configuration Parser 测试结果: {sum(results)}/{len(results)} 通过 ({success_rate:.1f}%){Colors.RESET}")
    return all(results)


def test_service_mapper():
    """测试服务映射器"""
    print_header("测试 2: Service Mapper")
    
    mapper = ServiceMapper(knowledge_base_service=None, cloud_service_service=None)
    results = []
    
    # 测试 2.1: 计算服务映射
    print_info("测试 2.1: 阿里云 ECS 映射到 AWS EC2")
    config = ServiceConfig(
        provider="alibaba",
        service_type="compute",
        service_name="ECS",
        specifications={"instance_type": "ecs.c6.large", "cpu": 2, "memory": 4}
    )
    try:
        mappings = mapper.map_service(config)
        if mappings and len(mappings) > 0:
            print_success(f"服务映射成功: {config.service_name} → {mappings[0].aws_service}")
            print(f"  - AWS 服务: {mappings[0].aws_service}")
            print(f"  - 实例类型: {mappings[0].aws_service_type}")
            print(f"  - 置信度: {mappings[0].confidence_score:.2f}")
            results.append(True)
        else:
            print_error("服务映射失败: 未找到映射")
            results.append(False)
    except Exception as e:
        print_error(f"服务映射异常: {e}")
        results.append(False)
    
    # 测试 2.2: 存储服务映射
    print_info("\n测试 2.2: 华为云 OBS 映射到 AWS S3")
    config = ServiceConfig(
        provider="huawei",
        service_type="storage",
        service_name="OBS",
        specifications={"storage_class": "standard", "capacity": 1000}
    )
    try:
        mappings = mapper.map_service(config)
        if mappings and len(mappings) > 0:
            print_success(f"存储映射成功: {config.service_name} → {mappings[0].aws_service}")
            print(f"  - AWS 服务: {mappings[0].aws_service}")
            print(f"  - 存储类: {mappings[0].aws_service_type}")
            results.append(True)
        else:
            print_error("存储映射失败: 未找到映射")
            results.append(False)
    except Exception as e:
        print_error(f"存储映射异常: {e}")
        results.append(False)
    
    # 测试 2.3: 数据库服务映射
    print_info("\n测试 2.3: 腾讯云 CDB 映射到 AWS RDS")
    config = ServiceConfig(
        provider="tencent",
        service_type="database",
        service_name="CDB",
        specifications={"engine": "mysql", "version": "8.0", "cpu": 2, "memory": 8}
    )
    try:
        mappings = mapper.map_service(config)
        if mappings and len(mappings) > 0:
            print_success(f"数据库映射成功: {config.service_name} → {mappings[0].aws_service}")
            print(f"  - AWS 服务: {mappings[0].aws_service}")
            results.append(True)
        else:
            print_error("数据库映射失败: 未找到映射")
            results.append(False)
    except Exception as e:
        print_error(f"数据库映射异常: {e}")
        results.append(False)
    
    # 测试 2.4: 多个选项处理
    print_info("\n测试 2.4: 测试多个 AWS 服务选项")
    config = ServiceConfig(
        provider="gcp",
        service_type="compute",
        service_name="Compute Engine",
        specifications={"cpu": 4, "memory": 16}
    )
    try:
        mappings = mapper.map_service(config)
        if mappings and len(mappings) > 0:
            print_success(f"找到 {len(mappings)} 个映射选项")
            for i, mapping in enumerate(mappings[:3], 1):
                print(f"  选项 {i}: {mapping.aws_service} ({mapping.aws_service_type})")
            results.append(True)
        else:
            print_error("未找到映射选项")
            results.append(False)
    except Exception as e:
        print_error(f"多选项测试异常: {e}")
        results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n{Colors.BOLD}Service Mapper 测试结果: {sum(results)}/{len(results)} 通过 ({success_rate:.1f}%){Colors.RESET}")
    return all(results)


def test_price_calculator():
    """测试价格计算器"""
    print_header("测试 3: Price Calculator")
    
    calculator = PriceCalculator(pricing_service=None, knowledge_base_service=None)
    results = []
    
    # 测试 3.1: EC2 定价计算
    print_info("测试 3.1: EC2 实例定价计算")
    mapping = AWSServiceMapping(
        aws_service="EC2",
        aws_service_category="compute",
        aws_service_type="t3.micro",
        specifications={"cpu": 2, "memory": 1},
        confidence_score=0.95,
        explanation="T3 micro instance",
        alternatives=[]
    )
    try:
        pricing = calculator.calculate_price(mapping, region='us-east-1')
        if pricing and pricing.monthly_cost > 0:
            print_success(f"EC2 定价计算成功")
            print(f"  - 月费用: ${pricing.monthly_cost:.2f}")
            print(f"  - 年费用: ${pricing.annual_cost:.2f}")
            print(f"  - 区域: {pricing.region}")
            print(f"  - 定价模式: {pricing.pricing_model}")
            results.append(True)
        else:
            print_error("EC2 定价计算失败: 费用为 0")
            results.append(False)
    except Exception as e:
        print_error(f"EC2 定价计算异常: {e}")
        results.append(False)
    
    # 测试 3.2: S3 定价计算
    print_info("\n测试 3.2: S3 存储定价计算")
    mapping = AWSServiceMapping(
        aws_service="S3",
        aws_service_category="storage",
        aws_service_type="Standard",
        specifications={"capacity": 1000},
        confidence_score=0.98,
        explanation="S3 Standard storage",
        alternatives=[]
    )
    try:
        pricing = calculator.calculate_price(mapping, region='us-east-1')
        if pricing and pricing.monthly_cost >= 0:
            print_success(f"S3 定价计算成功")
            print(f"  - 月费用: ${pricing.monthly_cost:.2f}")
            print(f"  - 年费用: ${pricing.annual_cost:.2f}")
            results.append(True)
        else:
            print_error("S3 定价计算失败")
            results.append(False)
    except Exception as e:
        print_error(f"S3 定价计算异常: {e}")
        results.append(False)
    
    # 测试 3.3: 多区域定价
    print_info("\n测试 3.3: 多区域定价比较")
    mapping = AWSServiceMapping(
        aws_service="EC2",
        aws_service_category="compute",
        aws_service_type="t3.small",
        specifications={"cpu": 2, "memory": 2},
        confidence_score=0.95,
        explanation="T3 small instance",
        alternatives=[]
    )
    try:
        regions = ['us-east-1', 'us-west-2', 'ap-northeast-1']
        all_prices = calculator.get_all_region_prices(mapping)
        
        available_prices = {r: p for r, p in all_prices.items() if p is not None and r in regions}
        
        if len(available_prices) > 0:
            print_success(f"多区域定价成功: 获取了 {len(available_prices)} 个区域的定价")
            for region, pricing in list(available_prices.items())[:3]:
                print(f"  - {region}: ${pricing.monthly_cost:.2f}/月")
            results.append(True)
        else:
            print_error("多区域定价失败: 未获取到任何区域定价")
            results.append(False)
    except Exception as e:
        print_error(f"多区域定价异常: {e}")
        results.append(False)
    
    # 测试 3.4: 多种定价模式
    print_info("\n测试 3.4: 多种定价模式 (On-Demand, Reserved)")
    mapping = AWSServiceMapping(
        aws_service="EC2",
        aws_service_category="compute",
        aws_service_type="t3.medium",
        specifications={"cpu": 2, "memory": 4},
        confidence_score=0.95,
        explanation="T3 medium instance",
        alternatives=[]
    )
    try:
        on_demand = calculator.calculate_price(mapping, pricing_model='on-demand')
        reserved = calculator.calculate_price(mapping, pricing_model='reserved')
        
        if on_demand and reserved:
            print_success(f"多定价模式计算成功")
            print(f"  - On-Demand: ${on_demand.monthly_cost:.2f}/月")
            print(f"  - Reserved (1年): ${reserved.monthly_cost:.2f}/月")
            savings = (on_demand.monthly_cost - reserved.monthly_cost) / on_demand.monthly_cost * 100
            print(f"  - 节省: {savings:.1f}%")
            results.append(True)
        else:
            print_error("多定价模式计算失败")
            results.append(False)
    except Exception as e:
        print_error(f"多定价模式计算异常: {e}")
        results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n{Colors.BOLD}Price Calculator 测试结果: {sum(results)}/{len(results)} 通过 ({success_rate:.1f}%){Colors.RESET}")
    return all(results)


def test_quote_generator():
    """测试报价生成器"""
    print_header("测试 4: Quote Generator")
    
    generator = QuoteGenerator()
    results = []
    
    # 准备测试数据
    original_configs = [
        ServiceConfig(
            provider="alibaba",
            service_type="compute",
            service_name="ECS",
            specifications={"instance_type": "ecs.c6.large", "cpu": 2, "memory": 4}
        ),
        ServiceConfig(
            provider="alibaba",
            service_type="storage",
            service_name="OSS",
            specifications={"storage_class": "standard", "capacity": 1000}
        )
    ]
    
    mappings = [
        AWSServiceMapping(
            aws_service="EC2",
            aws_service_category="compute",
            aws_service_type="c6i.large",
            specifications={"cpu": 2, "memory": 4},
            confidence_score=0.95,
            explanation="C6i large instance matches ECS c6.large",
            alternatives=["c5.large", "c5a.large"]
        ),
        AWSServiceMapping(
            aws_service="S3",
            aws_service_category="storage",
            aws_service_type="Standard",
            specifications={"capacity": 1000},
            confidence_score=0.98,
            explanation="S3 Standard storage matches OSS standard",
            alternatives=["S3 Intelligent-Tiering"]
        )
    ]
    
    pricing_results = [
        PricingResult(
            monthly_cost=Decimal("68.00"),
            annual_cost=Decimal("816.00"),
            pricing_model="on-demand",
            region="us-east-1",
            breakdown={"compute": Decimal("68.00")},
            currency="USD",
            last_updated=datetime.now()
        ),
        PricingResult(
            monthly_cost=Decimal("23.00"),
            annual_cost=Decimal("276.00"),
            pricing_model="on-demand",
            region="us-east-1",
            breakdown={"storage": Decimal("23.00")},
            currency="USD",
            last_updated=datetime.now()
        )
    ]
    
    user_info = {
        "user_id": "test-user-123",
        "username": "test_user",
        "email": "test@example.com"
    }
    
    # 测试 4.1: 报价生成
    print_info("测试 4.1: 生成完整报价")
    try:
        quote = generator.generate_quote(
            user_id=user_info['user_id'],
            original_input="Test configuration",
            parsed_services=original_configs,
            aws_mappings=mappings,
            pricing_results=pricing_results,
            region='us-east-1',
            language='en'
        )
        
        if quote and quote.quote_id:
            print_success(f"报价生成成功")
            print(f"  - 报价 ID: {quote.quote_id}")
            print(f"  - 服务数量: {len(quote.original_services)}")
            print(f"  - 月总费用: ${quote.total_monthly_cost:.2f}")
            print(f"  - 年总费用: ${quote.total_annual_cost:.2f}")
            print(f"  - 用户: {quote.user_id}")
            results.append(True)
        else:
            print_error("报价生成失败: 未生成报价")
            results.append(False)
    except Exception as e:
        print_error(f"报价生成异常: {e}")
        results.append(False)
    
    # 测试 4.2: JSON 导出
    print_info("\n测试 4.2: JSON 格式导出")
    try:
        if quote:
            json_url = generator.export_quote(quote, format='json')
            if json_url:
                print_success(f"JSON 导出成功")
                print(f"  - 导出路径: {json_url}")
                results.append(True)
            else:
                print_error("JSON 导出失败")
                results.append(False)
        else:
            print_warning("跳过 JSON 导出测试 (报价未生成)")
            results.append(False)
    except Exception as e:
        print_error(f"JSON 导出异常: {e}")
        results.append(False)
    
    # 测试 4.3: Excel 导出
    print_info("\n测试 4.3: Excel 格式导出")
    try:
        if quote:
            excel_url = generator.export_quote(quote, format='excel')
            if excel_url:
                print_success(f"Excel 导出成功")
                print(f"  - 导出路径: {excel_url}")
                results.append(True)
            else:
                print_error("Excel 导出失败")
                results.append(False)
        else:
            print_warning("跳过 Excel 导出测试 (报价未生成)")
            results.append(False)
    except Exception as e:
        print_error(f"Excel 导出异常: {e}")
        results.append(False)
    
    # 测试 4.4: PDF 导出
    print_info("\n测试 4.4: PDF 格式导出")
    try:
        if quote:
            pdf_url = generator.export_quote(quote, format='pdf')
            if pdf_url:
                print_success(f"PDF 导出成功")
                print(f"  - 导出路径: {pdf_url}")
                results.append(True)
            else:
                print_error("PDF 导出失败")
                results.append(False)
        else:
            print_warning("跳过 PDF 导出测试 (报价未生成)")
            results.append(False)
    except Exception as e:
        print_error(f"PDF 导出异常: {e}")
        results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n{Colors.BOLD}Quote Generator 测试结果: {sum(results)}/{len(results)} 通过 ({success_rate:.1f}%){Colors.RESET}")
    return all(results)


def main():
    """主函数"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                    Checkpoint 10: 核心组件验证                              ║")
    print("║                                                                            ║")
    print("║  测试范围:                                                                  ║")
    print("║  1. Configuration Parser - 配置解析器                                       ║")
    print("║  2. Service Mapper - 服务映射器                                            ║")
    print("║  3. Price Calculator - 价格计算器                                          ║")
    print("║  4. Quote Generator - 报价生成器                                           ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    results = {}
    
    # 运行所有测试
    try:
        results['parser'] = test_configuration_parser()
    except Exception as e:
        print_error(f"Configuration Parser 测试失败: {e}")
        results['parser'] = False
    
    try:
        results['mapper'] = test_service_mapper()
    except Exception as e:
        print_error(f"Service Mapper 测试失败: {e}")
        results['mapper'] = False
    
    try:
        results['calculator'] = test_price_calculator()
    except Exception as e:
        print_error(f"Price Calculator 测试失败: {e}")
        results['calculator'] = False
    
    try:
        results['generator'] = test_quote_generator()
    except Exception as e:
        print_error(f"Quote Generator 测试失败: {e}")
        results['generator'] = False
    
    # 打印总结
    print_header("测试总结")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    success_rate = passed_tests / total_tests * 100
    
    print(f"{Colors.BOLD}组件测试结果:{Colors.RESET}")
    for component, passed in results.items():
        status = f"{Colors.GREEN}[OK] 通过{Colors.RESET}" if passed else f"{Colors.RED}[FAIL] 失败{Colors.RESET}"
        print(f"  - {component.title()}: {status}")
    
    print(f"\n{Colors.BOLD}总体结果: {passed_tests}/{total_tests} 组件通过 ({success_rate:.1f}%){Colors.RESET}")
    
    if all(results.values()):
        print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] 所有核心组件验证通过！{Colors.RESET}")
        print(f"{Colors.GREEN}系统已准备好进行下一阶段开发。{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}[WARNING] 部分组件验证失败{Colors.RESET}")
        print(f"{Colors.YELLOW}请检查失败的组件并解决问题。{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
