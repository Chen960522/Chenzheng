"""Property-based tests for Configuration Parser."""

import json
import yaml
import csv
import io
from hypothesis import given, strategies as st, settings
import pytest

from src.services.configuration_parser import (
    ConfigurationParser,
    ConfigurationParserError,
    InvalidFormatError,
    MissingFieldError
)
from src.models.service_config import ServiceConfig


# Strategies for generating test data
providers = st.sampled_from(ServiceConfig.SUPPORTED_PROVIDERS)
service_types = st.sampled_from(ServiceConfig.SUPPORTED_CATEGORIES)
service_names = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'),
    whitelist_characters='-_'
))
quantities = st.integers(min_value=1, max_value=100)
regions = st.one_of(
    st.none(),
    st.sampled_from(['us-east-1', 'cn-hangzhou', 'eu-west-1', 'ap-southeast-1'])
)

# Specification strategies
spec_keys = st.sampled_from(['cpu', 'vcpu', 'memory', 'ram', 'storage', 'disk', 
                             'bandwidth', 'network', 'capacity'])
spec_values = st.one_of(
    st.integers(min_value=1, max_value=1000),
    st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False),
    st.text(min_size=1, max_size=20)
)
specifications = st.dictionaries(
    keys=spec_keys,
    values=spec_values,
    min_size=1,
    max_size=10
)


def generate_service_dict(provider, service_type, service_name, specs, region, quantity):
    """Generate a service dictionary for testing."""
    service = {
        'provider': provider,
        'service_type': service_type,
        'service_name': service_name,
        'specifications': specs,
        'quantity': quantity
    }
    if region:
        service['region'] = region
    return service


@given(
    provider=providers,
    service_type=service_types,
    service_name=service_names,
    specs=specifications,
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_1_json_parsing(provider, service_type, service_name, specs, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 1: Multi-format configuration parsing
    
    For any valid configuration input in JSON format, the Configuration Parser 
    should successfully extract service types and specifications.
    
    Validates: Requirements 1.1, 1.3
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = generate_service_dict(provider, service_type, service_name, specs, region, quantity)
    json_text = json.dumps({'services': [service_dict]})
    
    # Act
    result = parser.parse(json_text, format_hint='json')
    
    # Assert
    assert len(result) == 1
    config = result[0]
    assert isinstance(config, ServiceConfig)
    assert config.provider == provider
    assert config.service_type == service_type
    assert config.service_name == service_name
    assert config.quantity == quantity
    assert config.region == region
    
    # Verify all specifications are extracted
    for key, value in specs.items():
        assert key in config.specifications
        # Handle float comparison with tolerance
        if isinstance(value, float):
            assert abs(config.specifications[key] - value) < 0.001
        else:
            assert config.specifications[key] == value


@given(
    provider=providers,
    service_type=service_types,
    service_name=service_names,
    specs=specifications,
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_1_yaml_parsing(provider, service_type, service_name, specs, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 1: Multi-format configuration parsing
    
    For any valid configuration input in YAML format, the Configuration Parser 
    should successfully extract service types and specifications.
    
    Validates: Requirements 1.1, 1.3
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = generate_service_dict(provider, service_type, service_name, specs, region, quantity)
    yaml_text = yaml.dump({'services': [service_dict]})
    
    # Act
    result = parser.parse(yaml_text, format_hint='yaml')
    
    # Assert
    assert len(result) == 1
    config = result[0]
    assert isinstance(config, ServiceConfig)
    assert config.provider == provider
    assert config.service_type == service_type
    assert config.service_name == service_name
    assert config.quantity == quantity
    assert config.region == region
    
    # Verify all specifications are extracted
    for key, value in specs.items():
        assert key in config.specifications
        # Handle float comparison with tolerance
        if isinstance(value, float):
            assert abs(config.specifications[key] - value) < 0.001
        else:
            assert config.specifications[key] == value


@given(
    provider=providers,
    service_type=service_types,
    service_name=service_names,
    cpu=st.integers(min_value=1, max_value=128),
    memory=st.integers(min_value=1, max_value=1024),
    storage=st.integers(min_value=1, max_value=10000),
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_1_csv_parsing(provider, service_type, service_name, cpu, memory, storage, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 1: Multi-format configuration parsing
    
    For any valid configuration input in CSV format, the Configuration Parser 
    should successfully extract service types and specifications.
    
    Validates: Requirements 1.1, 1.3
    """
    # Arrange
    parser = ConfigurationParser()
    
    # Create CSV text
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=['provider', 'service_type', 'service_name', 'cpu', 'memory', 'storage', 'region', 'quantity']
    )
    writer.writeheader()
    writer.writerow({
        'provider': provider,
        'service_type': service_type,
        'service_name': service_name,
        'cpu': cpu,
        'memory': memory,
        'storage': storage,
        'region': region or '',
        'quantity': quantity
    })
    csv_text = csv_buffer.getvalue()
    
    # Act
    result = parser.parse(csv_text, format_hint='csv')
    
    # Assert
    assert len(result) == 1
    config = result[0]
    assert isinstance(config, ServiceConfig)
    assert config.provider == provider
    assert config.service_type == service_type
    assert config.service_name == service_name
    assert config.quantity == quantity
    assert config.region == region
    
    # Verify specifications are extracted
    assert 'cpu' in config.specifications
    assert config.specifications['cpu'] == cpu
    assert 'memory' in config.specifications
    assert config.specifications['memory'] == memory
    assert 'storage' in config.specifications
    assert config.specifications['storage'] == storage


@given(
    provider=providers,
    service_type=service_types,
    service_name=service_names,
    specs=specifications,
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_1_auto_detect_json(provider, service_type, service_name, specs, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 1: Multi-format configuration parsing
    
    For any valid JSON configuration without format hint, the Configuration Parser 
    should auto-detect and successfully parse it.
    
    Validates: Requirements 1.1, 1.3
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = generate_service_dict(provider, service_type, service_name, specs, region, quantity)
    json_text = json.dumps({'services': [service_dict]})
    
    # Act - no format hint provided
    result = parser.parse(json_text)
    
    # Assert
    assert len(result) == 1
    config = result[0]
    assert isinstance(config, ServiceConfig)
    assert config.provider == provider
    assert config.service_type == service_type
    assert config.service_name == service_name


@given(
    provider=providers,
    service_type=service_types,
    service_name=service_names,
    specs=specifications,
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_1_auto_detect_yaml(provider, service_type, service_name, specs, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 1: Multi-format configuration parsing
    
    For any valid YAML configuration without format hint, the Configuration Parser 
    should auto-detect and successfully parse it.
    
    Validates: Requirements 1.1, 1.3
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = generate_service_dict(provider, service_type, service_name, specs, region, quantity)
    yaml_text = yaml.dump({'services': [service_dict]})
    
    # Act - no format hint provided
    result = parser.parse(yaml_text)
    
    # Assert
    assert len(result) == 1
    config = result[0]
    assert isinstance(config, ServiceConfig)
    assert config.provider == provider
    assert config.service_type == service_type
    assert config.service_name == service_name



# Property 2: Multi-language service recognition tests

@given(
    provider=st.sampled_from(['alibaba', 'huawei', 'tencent']),
    service_name_pair=st.sampled_from([
        ('阿里云ECS', 'ECS'),
        ('阿里云OSS', 'OSS'),
        ('阿里云RDS', 'RDS'),
        ('Alibaba Cloud ECS', 'ECS'),
        ('华为云ECS', 'ECS'),
        ('华为云OBS', 'OBS'),
        ('Huawei Cloud OBS', 'OBS'),
        ('腾讯云CVM', 'CVM'),
        ('腾讯云COS', 'COS'),
        ('Tencent Cloud CVM', 'CVM'),
    ]),
    specs=specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_2_chinese_service_name_normalization(provider, service_name_pair, specs):
    """
    Feature: aws-pricing-assistant, Property 2: Multi-language service recognition
    
    For any service name in Chinese or English, the Configuration Parser 
    should recognize and normalize it to a standard format.
    
    Validates: Requirements 1.2
    """
    # Arrange
    parser = ConfigurationParser()
    input_name, expected_normalized = service_name_pair
    
    # Create a service dict with the input name
    service_dict = {
        'provider': provider,
        'service_type': 'compute',
        'service_name': input_name,
        'specifications': specs,
        'quantity': 1
    }
    
    # Manually normalize (simulating what _normalize_service_names does)
    normalized_data = parser._normalize_service_names([service_dict])
    
    # Assert
    assert len(normalized_data) == 1
    assert normalized_data[0]['service_name'] == expected_normalized


@given(
    provider=st.sampled_from(['gcp', 'azure']),
    service_name_pair=st.sampled_from([
        ('Google Compute Engine', 'Compute Engine'),
        ('Google Cloud Storage', 'Cloud Storage'),
        ('Google Cloud SQL', 'Cloud SQL'),
        ('Azure Virtual Machines', 'Virtual Machines'),
        ('Azure Blob Storage', 'Blob Storage'),
        ('Azure SQL Database', 'SQL Database'),
    ]),
    specs=specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_2_english_service_name_normalization(provider, service_name_pair, specs):
    """
    Feature: aws-pricing-assistant, Property 2: Multi-language service recognition
    
    For any service name in English with provider prefix, the Configuration Parser 
    should recognize and normalize it to a standard format.
    
    Validates: Requirements 1.2
    """
    # Arrange
    parser = ConfigurationParser()
    input_name, expected_normalized = service_name_pair
    
    # Create a service dict with the input name
    service_dict = {
        'provider': provider,
        'service_type': 'compute',
        'service_name': input_name,
        'specifications': specs,
        'quantity': 1
    }
    
    # Manually normalize
    normalized_data = parser._normalize_service_names([service_dict])
    
    # Assert
    assert len(normalized_data) == 1
    assert normalized_data[0]['service_name'] == expected_normalized


@given(
    provider=providers,
    service_type=service_types,
    service_name=service_names,
    specs=specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_2_already_normalized_names_unchanged(provider, service_type, service_name, specs):
    """
    Feature: aws-pricing-assistant, Property 2: Multi-language service recognition
    
    For any service name that doesn't need normalization, the Configuration Parser 
    should leave it unchanged.
    
    Validates: Requirements 1.2
    """
    # Arrange
    parser = ConfigurationParser()
    
    # Create a service dict with a name that doesn't need normalization
    service_dict = {
        'provider': provider,
        'service_type': service_type,
        'service_name': service_name,
        'specifications': specs,
        'quantity': 1
    }
    
    # Manually normalize
    normalized_data = parser._normalize_service_names([service_dict])
    
    # Assert - name should be unchanged if not in normalization map
    assert len(normalized_data) == 1
    # If the name was in the normalization map, it would be changed
    # Otherwise it should remain the same
    assert normalized_data[0]['service_name'] in [service_name, 'ECS', 'OSS', 'RDS', 'OBS', 'CVM', 'COS', 'TencentDB', 'Compute Engine', 'Cloud Storage', 'Cloud SQL', 'Virtual Machines', 'Blob Storage', 'SQL Database']



# Property 3: Complete specification extraction tests

@given(
    provider=providers,
    service_name=service_names,
    cpu=st.integers(min_value=1, max_value=128),
    memory=st.integers(min_value=1, max_value=1024),
    storage=st.integers(min_value=1, max_value=10000),
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_3_compute_resource_extraction(provider, service_name, cpu, memory, storage, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 3: Complete specification extraction
    
    For any configuration containing compute resources (CPU, memory, storage),
    the Configuration Parser should extract all specification details.
    
    Validates: Requirements 1.4, 1.5, 1.6
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': provider,
        'service_type': 'compute',
        'service_name': service_name,
        'specifications': {
            'cpu': cpu,
            'memory': memory,
            'storage': storage
        },
        'region': region,
        'quantity': quantity
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act
    result = parser.parse(json_text, format_hint='json')
    
    # Assert
    assert len(result) == 1
    config = result[0]
    
    # Verify all compute specifications are extracted
    assert 'cpu' in config.specifications
    assert config.specifications['cpu'] == cpu
    assert 'memory' in config.specifications
    assert config.specifications['memory'] == memory
    assert 'storage' in config.specifications
    assert config.specifications['storage'] == storage
    
    # Verify helper methods work
    compute_specs = config.get_compute_specs()
    assert 'cpu' in compute_specs
    assert 'memory' in compute_specs
    
    storage_specs = config.get_storage_specs()
    assert 'storage' in storage_specs


@given(
    provider=providers,
    service_name=service_names,
    bandwidth=st.integers(min_value=1, max_value=10000),
    throughput=st.integers(min_value=1, max_value=100000),
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_3_network_resource_extraction(provider, service_name, bandwidth, throughput, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 3: Complete specification extraction
    
    For any configuration containing network resources (bandwidth, throughput),
    the Configuration Parser should extract all specification details.
    
    Validates: Requirements 1.4, 1.5, 1.6
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': provider,
        'service_type': 'network',
        'service_name': service_name,
        'specifications': {
            'bandwidth': bandwidth,
            'throughput': throughput
        },
        'region': region,
        'quantity': quantity
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act
    result = parser.parse(json_text, format_hint='json')
    
    # Assert
    assert len(result) == 1
    config = result[0]
    
    # Verify all network specifications are extracted
    assert 'bandwidth' in config.specifications
    assert config.specifications['bandwidth'] == bandwidth
    assert 'throughput' in config.specifications
    assert config.specifications['throughput'] == throughput
    
    # Verify helper method works
    network_specs = config.get_network_specs()
    assert 'bandwidth' in network_specs
    assert 'throughput' in network_specs


@given(
    provider=providers,
    service_name=service_names,
    database_type=st.sampled_from(['mysql', 'postgresql', 'mongodb', 'redis']),
    version=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Nd',), whitelist_characters='.')),
    capacity=st.integers(min_value=1, max_value=10000),
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_3_database_resource_extraction(provider, service_name, database_type, version, capacity, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 3: Complete specification extraction
    
    For any configuration containing database resources (type, version, capacity),
    the Configuration Parser should extract all specification details.
    
    Validates: Requirements 1.4, 1.5, 1.6
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': provider,
        'service_type': 'database',
        'service_name': service_name,
        'specifications': {
            'database_type': database_type,
            'version': version,
            'capacity': capacity
        },
        'region': region,
        'quantity': quantity
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act
    result = parser.parse(json_text, format_hint='json')
    
    # Assert
    assert len(result) == 1
    config = result[0]
    
    # Verify all database specifications are extracted
    assert 'database_type' in config.specifications
    assert config.specifications['database_type'] == database_type
    assert 'version' in config.specifications
    assert config.specifications['version'] == version
    assert 'capacity' in config.specifications
    assert config.specifications['capacity'] == capacity


@given(
    provider=providers,
    service_name=service_names,
    specs=st.dictionaries(
        keys=st.sampled_from(['cpu', 'memory', 'storage', 'bandwidth', 'database_type', 'version', 'capacity']),
        values=st.one_of(
            st.integers(min_value=1, max_value=1000),
            st.text(min_size=1, max_size=20)
        ),
        min_size=3,
        max_size=7
    ),
    region=regions,
    quantity=quantities
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_3_mixed_specifications_extraction(provider, service_name, specs, region, quantity):
    """
    Feature: aws-pricing-assistant, Property 3: Complete specification extraction
    
    For any configuration containing mixed resource specifications,
    the Configuration Parser should extract all specification details.
    
    Validates: Requirements 1.4, 1.5, 1.6
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': provider,
        'service_type': 'compute',
        'service_name': service_name,
        'specifications': specs,
        'region': region,
        'quantity': quantity
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act
    result = parser.parse(json_text, format_hint='json')
    
    # Assert
    assert len(result) == 1
    config = result[0]
    
    # Verify all specifications are extracted
    for key, value in specs.items():
        assert key in config.specifications
        assert config.specifications[key] == value
    
    # Verify has_specification method works
    for key in specs.keys():
        assert config.has_specification(key)
    
    # Verify get_specification method works
    for key, value in specs.items():
        assert config.get_specification(key) == value



# Property 4: Ambiguous input handling tests

@given(
    text=st.one_of(
        st.just(''),  # Empty string
        st.just('   '),  # Whitespace only
        st.just('\n\n\n'),  # Newlines only
    )
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_4_empty_input_rejection(text):
    """
    Feature: aws-pricing-assistant, Property 4: Ambiguous input handling
    
    For any empty or whitespace-only input, the Configuration Parser 
    should reject it with a clear error message.
    
    Validates: Requirements 1.7
    """
    # Arrange
    parser = ConfigurationParser()
    
    # Act & Assert
    with pytest.raises(InvalidFormatError) as exc_info:
        parser.parse(text)
    
    assert "empty" in str(exc_info.value).lower()


@given(
    provider=providers,
    service_type=service_types,
    # Missing service_name
    specs=specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_4_missing_required_field_service_name(provider, service_type, specs):
    """
    Feature: aws-pricing-assistant, Property 4: Ambiguous input handling
    
    For any configuration missing the required service_name field,
    the Configuration Parser should reject it with a clear error message.
    
    Validates: Requirements 1.7
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': provider,
        'service_type': service_type,
        # 'service_name' is missing
        'specifications': specs
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act & Assert
    with pytest.raises((MissingFieldError, InvalidFormatError)) as exc_info:
        parser.parse(json_text, format_hint='json')
    
    assert "service_name" in str(exc_info.value).lower()


@given(
    provider=providers,
    service_name=service_names,
    # Missing service_type
    specs=specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_4_missing_required_field_service_type(provider, service_name, specs):
    """
    Feature: aws-pricing-assistant, Property 4: Ambiguous input handling
    
    For any configuration missing the required service_type field,
    the Configuration Parser should reject it with a clear error message.
    
    Validates: Requirements 1.7
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': provider,
        # 'service_type' is missing
        'service_name': service_name,
        'specifications': specs
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act & Assert
    with pytest.raises((MissingFieldError, InvalidFormatError)) as exc_info:
        parser.parse(json_text, format_hint='json')
    
    assert "service_type" in str(exc_info.value).lower()


@given(
    service_type=service_types,
    service_name=service_names,
    # Missing provider
    specs=specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_4_missing_required_field_provider(service_type, service_name, specs):
    """
    Feature: aws-pricing-assistant, Property 4: Ambiguous input handling
    
    For any configuration missing the required provider field,
    the Configuration Parser should reject it with a clear error message.
    
    Validates: Requirements 1.7
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        # 'provider' is missing
        'service_type': service_type,
        'service_name': service_name,
        'specifications': specs
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act & Assert
    with pytest.raises((MissingFieldError, InvalidFormatError)) as exc_info:
        parser.parse(json_text, format_hint='json')
    
    assert "provider" in str(exc_info.value).lower()


@given(
    provider=providers,
    service_type=service_types,
    service_name=service_names
    # Missing specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_4_missing_required_field_specifications(provider, service_type, service_name):
    """
    Feature: aws-pricing-assistant, Property 4: Ambiguous input handling
    
    For any configuration missing the required specifications field,
    the Configuration Parser should reject it with a clear error message.
    
    Validates: Requirements 1.7
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': provider,
        'service_type': service_type,
        'service_name': service_name
        # 'specifications' is missing
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act & Assert
    with pytest.raises((MissingFieldError, InvalidFormatError)) as exc_info:
        parser.parse(json_text, format_hint='json')
    
    assert "specifications" in str(exc_info.value).lower()


@given(
    text=st.text(min_size=10, max_size=100, alphabet=st.characters(
        blacklist_categories=('Cc', 'Cs'),  # Exclude control characters
        blacklist_characters='{}[]":'  # Exclude JSON special characters
    ))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_4_invalid_json_format(text):
    """
    Feature: aws-pricing-assistant, Property 4: Ambiguous input handling
    
    For any invalid JSON input, the Configuration Parser should reject it 
    with a clear error message indicating the JSON is malformed.
    
    Validates: Requirements 1.7
    """
    # Arrange
    parser = ConfigurationParser()
    
    # Act & Assert
    with pytest.raises(InvalidFormatError) as exc_info:
        parser.parse(text, format_hint='json')
    
    # Should mention JSON or format in error
    error_msg = str(exc_info.value).lower()
    assert 'json' in error_msg or 'format' in error_msg or 'invalid' in error_msg


@given(
    unsupported_provider=st.text(min_size=1, max_size=20).filter(
        lambda x: x not in ServiceConfig.SUPPORTED_PROVIDERS
    ),
    service_type=service_types,
    service_name=service_names,
    specs=specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_4_unsupported_provider(unsupported_provider, service_type, service_name, specs):
    """
    Feature: aws-pricing-assistant, Property 4: Ambiguous input handling
    
    For any configuration with an unsupported cloud provider,
    the Configuration Parser should reject it with a clear error message.
    
    Validates: Requirements 1.7
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': unsupported_provider,
        'service_type': service_type,
        'service_name': service_name,
        'specifications': specs
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act & Assert
    with pytest.raises((ValueError, ConfigurationParserError, MissingFieldError)) as exc_info:
        parser.parse(json_text, format_hint='json')
    
    # Should mention provider or unsupported
    error_msg = str(exc_info.value).lower()
    assert 'provider' in error_msg or 'unsupported' in error_msg


@given(
    provider=providers,
    unsupported_service_type=st.text(min_size=1, max_size=20).filter(
        lambda x: x not in ServiceConfig.SUPPORTED_CATEGORIES
    ),
    service_name=service_names,
    specs=specifications
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_4_unsupported_service_type(provider, unsupported_service_type, service_name, specs):
    """
    Feature: aws-pricing-assistant, Property 4: Ambiguous input handling
    
    For any configuration with an unsupported service type,
    the Configuration Parser should reject it with a clear error message.
    
    Validates: Requirements 1.7
    """
    # Arrange
    parser = ConfigurationParser()
    service_dict = {
        'provider': provider,
        'service_type': unsupported_service_type,
        'service_name': service_name,
        'specifications': specs
    }
    json_text = json.dumps({'services': [service_dict]})
    
    # Act & Assert
    with pytest.raises((ValueError, ConfigurationParserError, MissingFieldError)) as exc_info:
        parser.parse(json_text, format_hint='json')
    
    # Should mention service type or unsupported
    error_msg = str(exc_info.value).lower()
    assert 'service' in error_msg or 'type' in error_msg or 'unsupported' in error_msg
