# Bedrock Knowledge Base Content

This directory contains the data that will be uploaded to S3 and used as the data source for Amazon Bedrock Knowledge Base.

## Directory Structure

```
knowledge_base/
├── README.md                           # This file
├── service_mappings/                   # Service mapping rules
│   ├── alibaba_mappings.json
│   ├── huawei_mappings.json
│   ├── tencent_mappings.json
│   ├── gcp_mappings.json
│   └── azure_mappings.json
├── aws_services/                       # AWS service descriptions
│   ├── compute_services.json
│   ├── storage_services.json
│   ├── database_services.json
│   ├── network_services.json
│   ├── analytics_services.json
│   ├── ml_services.json
│   └── other_services.json
└── pricing_data/                       # AWS pricing information
    ├── compute_pricing.json
    ├── storage_pricing.json
    ├── database_pricing.json
    └── data_transfer_pricing.json
```

## Data Formats

### Service Mapping Format

Service mappings define how to map services from other cloud providers to AWS services.

**File**: `service_mappings/{provider}_mappings.json`

**Schema**:
```json
{
  "provider": "string",
  "last_updated": "ISO 8601 datetime",
  "mappings": [
    {
      "source_service": "string",
      "source_service_zh": "string (optional)",
      "service_category": "string",
      "aws_service": "string",
      "aws_service_type": "string (optional)",
      "confidence": "float (0.0-1.0)",
      "mapping_rules": {
        "instance_type_mappings": {},
        "storage_class_mappings": {},
        "other_mappings": {}
      },
      "notes": "string",
      "alternatives": ["string"]
    }
  ]
}
```

### AWS Service Description Format

AWS service descriptions provide detailed information about AWS services.

**File**: `aws_services/{category}_services.json`

**Schema**:
```json
{
  "category": "string",
  "last_updated": "ISO 8601 datetime",
  "services": [
    {
      "service_name": "string",
      "service_name_zh": "string",
      "description": "string",
      "description_zh": "string",
      "use_cases": ["string"],
      "key_features": ["string"],
      "pricing_model": ["on-demand", "reserved", "savings-plan"],
      "available_regions": ["string"],
      "related_services": ["string"]
    }
  ]
}
```

### Pricing Data Format

Pricing data contains AWS service pricing information.

**File**: `pricing_data/{category}_pricing.json`

**Schema**:
```json
{
  "category": "string",
  "last_updated": "ISO 8601 datetime",
  "pricing": [
    {
      "service": "string",
      "service_type": "string",
      "region": "string",
      "pricing_models": {
        "on_demand": {
          "unit": "string",
          "price": "float",
          "currency": "USD"
        },
        "reserved_1yr": {
          "upfront": "float",
          "unit": "string",
          "price": "float",
          "currency": "USD"
        },
        "reserved_3yr": {
          "upfront": "float",
          "unit": "string",
          "price": "float",
          "currency": "USD"
        }
      },
      "data_transfer": {
        "ingress": "float",
        "egress": "float",
        "unit": "GB"
      }
    }
  ]
}
```

## Usage

1. **Prepare Content**: Create JSON files following the schemas above
2. **Upload to S3**: Use AWS CLI or SDK to upload to S3 bucket
3. **Configure Knowledge Base**: Point Bedrock Knowledge Base to S3 bucket
4. **Sync**: Knowledge Base will automatically index the content

## Maintenance

- Update pricing data monthly or when AWS announces price changes
- Update service mappings when new services are launched
- Update service descriptions when features change
- Keep `last_updated` timestamps current

## Notes

- All pricing is in USD
- Regions follow AWS region naming convention (e.g., us-east-1)
- Service categories: compute, storage, database, network, analytics, ml, container, serverless, messaging, monitoring, security, cdn, iot, blockchain
- Confidence scores: 1.0 = exact match, 0.8-0.9 = close match, 0.6-0.7 = approximate match
