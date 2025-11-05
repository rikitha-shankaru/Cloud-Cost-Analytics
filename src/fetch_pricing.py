"""
Unified pricing fetcher for AWS, GCP, and OCI.
Supports live API integration (currently uses mock data for demo).
"""

import json
from typing import Dict, List, Optional
from enum import Enum


class Provider(str, Enum):
    """Supported cloud providers."""
    AWS = "aws"
    GCP = "gcp"
    OCI = "oci"


def fetch_aws_pricing(region: str = "us-east-1") -> List[Dict]:
    """
    Fetch AWS pricing data for a given region.
    
    TODO: Replace with real AWS Pricing API integration:
    - Use boto3: pricing_client = boto3.client('pricing', region_name='us-east-1')
    - Query GetProducts API for EC2 and S3 pricing
    
    Args:
        region: AWS region code
        
    Returns:
        List of pricing SKU dictionaries
    """
    # Mock data - replace with AWS Pricing API calls
    mock_data = [
        {
            "provider": "aws",
            "region": region,
            "sku": f"aws-ec2-m5-large-{region}",
            "service": "EC2",
            "instance_type": "m5.large",
            "on_demand_price": 0.096,
            "currency": "USD",
            "unit": "per-hour",
            "attributes": {
                "vcpu": 2,
                "memory_gb": 8,
                "storage_gb": "ebs-only"
            }
        },
        {
            "provider": "aws",
            "region": region,
            "sku": f"aws-ec2-m5-xlarge-{region}",
            "service": "EC2",
            "instance_type": "m5.xlarge",
            "on_demand_price": 0.192,
            "currency": "USD",
            "unit": "per-hour",
            "attributes": {
                "vcpu": 4,
                "memory_gb": 16,
                "storage_gb": "ebs-only"
            }
        },
        {
            "provider": "aws",
            "region": region,
            "sku": f"aws-s3-standard-{region}",
            "service": "S3",
            "instance_type": "standard",
            "on_demand_price": 0.023,
            "currency": "USD",
            "unit": "per-gb-month",
            "attributes": {}
        }
    ]
    
    return mock_data


def fetch_gcp_pricing(region: str = "us-central1") -> List[Dict]:
    """
    Fetch GCP pricing data for a given region.
    
    TODO: Replace with real GCP Pricing API integration:
    - Use google-cloud-billing API
    - Query Cloud Billing Catalog API for Compute Engine and Storage pricing
    
    Args:
        region: GCP region code
        
    Returns:
        List of pricing SKU dictionaries
    """
    # Mock data - replace with GCP Pricing API calls
    mock_data = [
        {
            "provider": "gcp",
            "region": region,
            "sku": f"gcp-compute-n1-standard-2-{region}",
            "service": "Compute Engine",
            "instance_type": "n1-standard-2",
            "on_demand_price": 0.094,
            "currency": "USD",
            "unit": "per-hour",
            "attributes": {
                "vcpu": 2,
                "memory_gb": 7.5,
                "storage_gb": "persistent-disk"
            }
        },
        {
            "provider": "gcp",
            "region": region,
            "sku": f"gcp-compute-n1-standard-4-{region}",
            "service": "Compute Engine",
            "instance_type": "n1-standard-4",
            "on_demand_price": 0.188,
            "currency": "USD",
            "unit": "per-hour",
            "attributes": {
                "vcpu": 4,
                "memory_gb": 15,
                "storage_gb": "persistent-disk"
            }
        },
        {
            "provider": "gcp",
            "region": region,
            "sku": f"gcp-storage-standard-{region}",
            "service": "Cloud Storage",
            "instance_type": "standard",
            "on_demand_price": 0.020,
            "currency": "USD",
            "unit": "per-gb-month",
            "attributes": {}
        }
    ]
    
    return mock_data


def fetch_oci_pricing(region: str = "us-ashburn-1") -> List[Dict]:
    """
    Fetch OCI pricing data for a given region.
    
    TODO: Replace with real OCI Pricing API integration:
    - Use oci SDK: oci.pricing.PricingClient
    - Query pricing catalog API
    
    Args:
        region: OCI region code
        
    Returns:
        List of pricing SKU dictionaries
    """
    # Mock data - replace with OCI Pricing API calls
    mock_data = [
        {
            "provider": "oci",
            "region": region,
            "sku": f"oci-compute-vm-standard2-2-{region}",
            "service": "Compute",
            "instance_type": "VM.Standard2.2",
            "on_demand_price": 0.088,
            "currency": "USD",
            "unit": "per-hour",
            "attributes": {
                "vcpu": 2,
                "memory_gb": 32,
                "storage_gb": "block-volume"
            }
        },
        {
            "provider": "oci",
            "region": region,
            "sku": f"oci-compute-vm-standard2-4-{region}",
            "service": "Compute",
            "instance_type": "VM.Standard2.4",
            "on_demand_price": 0.176,
            "currency": "USD",
            "unit": "per-hour",
            "attributes": {
                "vcpu": 4,
                "memory_gb": 64,
                "storage_gb": "block-volume"
            }
        },
        {
            "provider": "oci",
            "region": region,
            "sku": f"oci-object-storage-standard-{region}",
            "service": "Object Storage",
            "instance_type": "standard",
            "on_demand_price": 0.025,
            "currency": "USD",
            "unit": "per-gb-month",
            "attributes": {}
        }
    ]
    
    return mock_data


def fetch_all_pricing(providers: Optional[List[str]] = None, regions: Optional[List[str]] = None) -> List[Dict]:
    """
    Fetch pricing data from all providers and regions.
    
    Args:
        providers: List of providers to fetch (default: all)
        regions: List of regions to fetch (default: all)
        
    Returns:
        Combined list of pricing SKUs from all providers
    """
    if providers is None:
        providers = ["aws", "gcp", "oci"]
    
    if regions is None:
        regions = {
            "aws": ["us-east-1"],
            "gcp": ["us-central1"],
            "oci": ["us-ashburn-1"]
        }
    
    all_data = []
    
    for provider in providers:
        if provider == "aws":
            for region in regions.get("aws", ["us-east-1"]):
                all_data.extend(fetch_aws_pricing(region))
        elif provider == "gcp":
            for region in regions.get("gcp", ["us-central1"]):
                all_data.extend(fetch_gcp_pricing(region))
        elif provider == "oci":
            for region in regions.get("oci", ["us-ashburn-1"]):
                all_data.extend(fetch_oci_pricing(region))
    
    return all_data


def normalize_pricing_data(pricing_data: List[Dict]) -> List[Dict]:
    """
    Normalize pricing data from multiple providers into unified format.
    
    Args:
        pricing_data: Raw pricing data from providers
        
    Returns:
        Normalized pricing data
    """
    normalized = []
    
    for item in pricing_data:
        normalized_item = {
            "provider": item["provider"],
            "region": item["region"],
            "sku": item["sku"],
            "service": item["service"],
            "instance_type": item["instance_type"],
            "price_per_hour": item["on_demand_price"] if item["unit"] == "per-hour" else None,
            "price_per_gb_month": item["on_demand_price"] if item["unit"] == "per-gb-month" else None,
            "currency": item["currency"],
            "vcpu": item.get("attributes", {}).get("vcpu"),
            "memory_gb": item.get("attributes", {}).get("memory_gb"),
            "storage_type": item.get("attributes", {}).get("storage_gb", "unknown")
        }
        normalized.append(normalized_item)
    
    return normalized


if __name__ == "__main__":
    # Test fetching and normalization
    print("Fetching pricing data from all providers...")
    raw_data = fetch_all_pricing()
    normalized = normalize_pricing_data(raw_data)
    
    print(f"\nFetched {len(raw_data)} SKUs")
    print(f"Normalized to {len(normalized)} entries")
    print("\nSample normalized data:")
    print(json.dumps(normalized[:2], indent=2))

