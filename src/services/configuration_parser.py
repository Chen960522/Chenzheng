"""Configuration Parser service for parsing cloud service configurations."""

import json
import csv
import yaml
import io
from typing import List, Dict, Any, Optional
from src.models.service_config import ServiceConfig


class ConfigurationParserError(Exception):
    """Base exception for configuration parsing errors."""
    pass


class InvalidFormatError(ConfigurationParserError):
    """Raised when the configuration format is invalid."""
    pass


class MissingFieldError(ConfigurationParserError):
    """Raised when required fields are missing."""
    pass


class ConfigurationParser:
    """
    Parser for cloud service configurations.
    
    Supports multiple input formats:
    - JSON: Structured JSON with service definitions
    - YAML: YAML format with service definitions
    - CSV: Tabular format with service specifications
    - Plain text: Unstructured text (requires LLM parsing)
    """
    
    def __init__(self, bedrock_client=None):
        """
        Initialize the configuration parser.
        
        Args:
            bedrock_client: Optional Bedrock client for LLM-based parsing
        """
        self.bedrock_client = bedrock_client
        self.required_fields = ['provider', 'service_type', 'service_name', 'specifications']
    
    def parse(self, input_text: str, format_hint: Optional[str] = None) -> List[ServiceConfig]:
        """
        Parse configuration from input text.
        
        Args:
            input_text: The configuration text to parse
            format_hint: Optional hint about the format ('json', 'yaml', 'csv', 'text')
        
        Returns:
            List of ServiceConfig objects
        
        Raises:
            ConfigurationParserError: If parsing fails
        """
        if not input_text or not input_text.strip():
            raise InvalidFormatError("Input text cannot be empty")
        
        # Try structured parsing first
        if format_hint in ['json', 'yaml', 'csv']:
            try:
                return self._parse_structured(input_text, format_hint)
            except Exception as e:
                # Logging removed to avoid circular import
                raise InvalidFormatError(f"Failed to parse as {format_hint}: {str(e)}")
        
        # Auto-detect format if no hint provided
        if format_hint is None:
            # Try JSON first
            try:
                return self._parse_json(input_text)
            except Exception:
                pass
            
            # Try YAML
            try:
                return self._parse_yaml(input_text)
            except Exception:
                pass
            
            # Try CSV
            try:
                return self._parse_csv(input_text)
            except Exception:
                pass
        
        # Fall back to LLM-based parsing for unstructured text
        if self.bedrock_client:
            return self._parse_with_llm(input_text)
        else:
            raise InvalidFormatError(
                "Unable to parse configuration. Please provide a valid JSON, YAML, or CSV format, "
                "or configure Bedrock client for unstructured text parsing."
            )
    
    def _parse_structured(self, text: str, format_type: str) -> List[ServiceConfig]:
        """Parse structured format (JSON, YAML, CSV)."""
        if format_type == 'json':
            return self._parse_json(text)
        elif format_type == 'yaml':
            return self._parse_yaml(text)
        elif format_type == 'csv':
            return self._parse_csv(text)
        else:
            raise InvalidFormatError(f"Unsupported format: {format_type}")
    
    def _parse_json(self, text: str) -> List[ServiceConfig]:
        """
        Parse JSON configuration.
        
        Expected format:
        {
            "services": [
                {
                    "provider": "alibaba",
                    "service_type": "compute",
                    "service_name": "ECS",
                    "specifications": {"cpu": 4, "memory": 8},
                    "region": "cn-hangzhou",
                    "quantity": 2
                }
            ]
        }
        
        Or a simple array:
        [
            {
                "provider": "alibaba",
                "service_type": "compute",
                ...
            }
        ]
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise InvalidFormatError(f"Invalid JSON format: {str(e)}")
        
        # Handle both {"services": [...]} and [...] formats
        if isinstance(data, dict) and 'services' in data:
            services_data = data['services']
        elif isinstance(data, list):
            services_data = data
        else:
            raise InvalidFormatError(
                "JSON must contain either a 'services' array or be an array of service objects"
            )
        
        return self._create_service_configs(services_data)
    
    def _parse_yaml(self, text: str) -> List[ServiceConfig]:
        """
        Parse YAML configuration.
        
        Expected format:
        services:
          - provider: alibaba
            service_type: compute
            service_name: ECS
            specifications:
              cpu: 4
              memory: 8
            region: cn-hangzhou
            quantity: 2
        """
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise InvalidFormatError(f"Invalid YAML format: {str(e)}")
        
        # Handle both {"services": [...]} and [...] formats
        if isinstance(data, dict) and 'services' in data:
            services_data = data['services']
        elif isinstance(data, list):
            services_data = data
        else:
            raise InvalidFormatError(
                "YAML must contain either a 'services' array or be an array of service objects"
            )
        
        return self._create_service_configs(services_data)
    
    def _parse_csv(self, text: str) -> List[ServiceConfig]:
        """
        Parse CSV configuration.
        
        Expected format:
        provider,service_type,service_name,cpu,memory,storage,bandwidth,region,quantity
        alibaba,compute,ECS,4,8,100,10,cn-hangzhou,2
        huawei,storage,OBS,,,1000,,cn-north-1,1
        
        Specifications are extracted from columns that are not standard fields.
        """
        try:
            # Use StringIO to treat string as file
            csv_file = io.StringIO(text)
            reader = csv.DictReader(csv_file)
            
            services_data = []
            for row in reader:
                # Extract standard fields
                service_dict = {
                    'provider': row.get('provider', '').strip(),
                    'service_type': row.get('service_type', '').strip(),
                    'service_name': row.get('service_name', '').strip(),
                    'region': row.get('region', '').strip() or None,
                    'quantity': int(row.get('quantity', 1))
                }
                
                # Extract specifications from remaining columns
                spec_columns = ['cpu', 'vcpu', 'memory', 'ram', 'storage', 'disk', 
                               'bandwidth', 'network', 'database_type', 'version', 'capacity']
                specifications = {}
                
                for col in spec_columns:
                    if col in row and row[col] and row[col].strip():
                        value = row[col].strip()
                        # Try to convert to number if possible
                        try:
                            specifications[col] = int(value)
                        except ValueError:
                            try:
                                specifications[col] = float(value)
                            except ValueError:
                                specifications[col] = value
                
                service_dict['specifications'] = specifications
                services_data.append(service_dict)
            
            if not services_data:
                raise InvalidFormatError("CSV file is empty or has no valid rows")
            
            return self._create_service_configs(services_data)
            
        except csv.Error as e:
            raise InvalidFormatError(f"Invalid CSV format: {str(e)}")
        except ValueError as e:
            raise InvalidFormatError(f"Invalid value in CSV: {str(e)}")
    
    def _create_service_configs(self, services_data: List[Dict[str, Any]]) -> List[ServiceConfig]:
        """
        Create ServiceConfig objects from parsed data.
        
        Args:
            services_data: List of dictionaries containing service data
        
        Returns:
            List of ServiceConfig objects
        
        Raises:
            MissingFieldError: If required fields are missing
        """
        configs = []
        
        for idx, service_data in enumerate(services_data):
            try:
                # Validate required fields
                missing_fields = []
                for field in self.required_fields:
                    if field not in service_data or not service_data[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    raise MissingFieldError(
                        f"Service at index {idx} is missing required fields: {', '.join(missing_fields)}"
                    )
                
                # Create ServiceConfig
                config = ServiceConfig(
                    provider=service_data['provider'],
                    service_type=service_data['service_type'],
                    service_name=service_data['service_name'],
                    specifications=service_data['specifications'],
                    region=service_data.get('region'),
                    quantity=service_data.get('quantity', 1)
                )
                
                configs.append(config)
                # Logging removed to avoid circular import
                
            except (ValueError, KeyError) as e:
                raise MissingFieldError(f"Error creating service config at index {idx}: {str(e)}")
        
        return configs
    
    def _parse_with_llm(self, text: str) -> List[ServiceConfig]:
        """
        Parse unstructured text using Bedrock LLM.
        
        Uses Claude to extract structured service information from plain text.
        Handles both Chinese and English service names and normalizes them.
        
        Args:
            text: Unstructured text containing service descriptions
        
        Returns:
            List of ServiceConfig objects
        
        Raises:
            ConfigurationParserError: If LLM parsing fails
        """
        if not self.bedrock_client:
            raise ConfigurationParserError(
                "Bedrock client is required for unstructured text parsing"
            )
        
        # Create prompt for Claude to extract structured data
        prompt = self._create_llm_prompt(text)
        
        try:
            # Call Bedrock Claude model
            response = self.bedrock_client.invoke_model(
                modelId='anthropic.claude-3-5-sonnet-20241022-v2:0',
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1  # Low temperature for more deterministic output
                })
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Extract JSON from response
            services_data = self._extract_json_from_llm_response(content)
            
            # Normalize service names (handle Chinese/English)
            services_data = self._normalize_service_names(services_data)
            
            # Create ServiceConfig objects
            return self._create_service_configs(services_data)
            
        except Exception as e:
            # Logging removed to avoid circular import
            raise ConfigurationParserError(f"Failed to parse text with LLM: {str(e)}")
    
    def _create_llm_prompt(self, text: str) -> str:
        """
        Create a prompt for the LLM to extract service configurations.
        
        Args:
            text: Input text to parse
        
        Returns:
            Formatted prompt string
        """
        return f"""Extract cloud service configurations from the following text and return them as a JSON array.

The text may contain service descriptions in Chinese or English. Please extract:
- provider: The cloud provider (alibaba, huawei, tencent, gcp, azure)
- service_type: The service category (compute, storage, database, network, analytics, ml, container, serverless, messaging, monitoring, security, cdn, iot, blockchain, developer_tools, management, application_integration, business_applications, end_user_computing, media_services, game_development)
- service_name: The original service name from the provider
- specifications: A dictionary of technical specifications (cpu, memory, storage, bandwidth, etc.)
- region: The provider's region (if mentioned)
- quantity: Number of instances (default to 1 if not specified)

Normalize service names:
- Alibaba Cloud ECS / 阿里云ECS → ECS
- Huawei Cloud OBS / 华为云OBS → OBS
- Tencent Cloud CVM / 腾讯云CVM → CVM
- Google Compute Engine → Compute Engine
- Azure Virtual Machines → Virtual Machines

Return ONLY a valid JSON array in this format:
[
  {{
    "provider": "alibaba",
    "service_type": "compute",
    "service_name": "ECS",
    "specifications": {{
      "cpu": 4,
      "memory": 8,
      "storage": 100
    }},
    "region": "cn-hangzhou",
    "quantity": 2
  }}
]

Text to parse:
{text}

Return only the JSON array, no additional text or explanation."""
    
    def _extract_json_from_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Extract JSON array from LLM response.
        
        The LLM might return JSON wrapped in markdown code blocks or with extra text.
        
        Args:
            response_text: Raw response from LLM
        
        Returns:
            Parsed JSON data
        
        Raises:
            InvalidFormatError: If JSON cannot be extracted
        """
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith('```json'):
            text = text[7:]  # Remove ```json
        elif text.startswith('```'):
            text = text[3:]  # Remove ```
        
        if text.endswith('```'):
            text = text[:-3]  # Remove trailing ```
        
        text = text.strip()
        
        # Try to find JSON array in the text
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        
        if start_idx == -1 or end_idx == -1:
            raise InvalidFormatError("No JSON array found in LLM response")
        
        json_text = text[start_idx:end_idx + 1]
        
        try:
            data = json.loads(json_text)
            if not isinstance(data, list):
                raise InvalidFormatError("LLM response is not a JSON array")
            return data
        except json.JSONDecodeError as e:
            raise InvalidFormatError(f"Invalid JSON in LLM response: {str(e)}")
    
    def _normalize_service_names(self, services_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize service names to handle Chinese and English variations.
        
        Args:
            services_data: List of service dictionaries
        
        Returns:
            List with normalized service names
        """
        # Service name normalization mappings
        normalization_map = {
            # Alibaba Cloud
            '阿里云ECS': 'ECS',
            '阿里云OSS': 'OSS',
            '阿里云RDS': 'RDS',
            'Alibaba Cloud ECS': 'ECS',
            'Alibaba Cloud OSS': 'OSS',
            'Alibaba Cloud RDS': 'RDS',
            
            # Huawei Cloud
            '华为云ECS': 'ECS',
            '华为云OBS': 'OBS',
            '华为云RDS': 'RDS',
            'Huawei Cloud ECS': 'ECS',
            'Huawei Cloud OBS': 'OBS',
            'Huawei Cloud RDS': 'RDS',
            
            # Tencent Cloud
            '腾讯云CVM': 'CVM',
            '腾讯云COS': 'COS',
            '腾讯云TencentDB': 'TencentDB',
            'Tencent Cloud CVM': 'CVM',
            'Tencent Cloud COS': 'COS',
            'Tencent Cloud TencentDB': 'TencentDB',
            
            # GCP
            'Google Compute Engine': 'Compute Engine',
            'Google Cloud Storage': 'Cloud Storage',
            'Google Cloud SQL': 'Cloud SQL',
            
            # Azure
            'Azure Virtual Machines': 'Virtual Machines',
            'Azure Blob Storage': 'Blob Storage',
            'Azure SQL Database': 'SQL Database'
        }
        
        for service in services_data:
            service_name = service.get('service_name', '')
            
            # Check if normalization is needed
            if service_name in normalization_map:
                service['service_name'] = normalization_map[service_name]
                # Logging removed to avoid circular import
        
        return services_data
    
    def validate_configuration(self, config: ServiceConfig) -> bool:
        """
        Validate a service configuration.
        
        Args:
            config: ServiceConfig to validate
        
        Returns:
            True if valid
        
        Raises:
            ConfigurationParserError: If validation fails
        """
        # Basic validation is done in ServiceConfig.__post_init__
        # Additional validation can be added here
        
        if not config.specifications:
            raise ConfigurationParserError(
                f"Service {config.service_name} has no specifications"
            )
        
        return True
