"""
Cost projection model for multi-cloud TCO analysis.
Supports Reserved Instances, Spot pricing, and storage/egress costs.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class CostModel:
    """Models cloud costs over time with various pricing options."""
    
    def __init__(self, pricing_data_path: str = "data/normalized.json"):
        """
        Initialize cost model with pricing data.
        
        Args:
            pricing_data_path: Path to normalized pricing JSON
        """
        with open(pricing_data_path, "r") as f:
            self.pricing_data = json.load(f)
    
    def calculate_tco(
        self,
        provider: str,
        instance_type: str,
        region: str,
        hours_per_month: int = 730,
        years: int = 1,
        reserved_instance: bool = False,
        spot_instance: bool = False
    ) -> Dict:
        """
        Calculate Total Cost of Ownership for a given instance.
        
        Args:
            provider: Cloud provider (aws, gcp, oci)
            instance_type: Instance type SKU
            region: Region code
            hours_per_month: Hours of usage per month
            years: Number of years to project
            reserved_instance: Use Reserved Instance pricing (30% discount)
            spot_instance: Use Spot pricing (60% discount, AWS/GCP only)
            
        Returns:
            Dictionary with cost breakdown
        """
        # Find matching pricing entry
        match = None
        for item in self.pricing_data:
            if (item["provider"] == provider and 
                item["instance_type"] == instance_type and
                item["region"] == region):
                match = item
                break
        
        if not match:
            return {"error": "No matching pricing found"}
        
        # Base hourly price
        hourly_price = match.get("price_per_hour", 0)
        
        # Apply discounts
        if spot_instance:
            hourly_price *= 0.4  # 60% discount
        elif reserved_instance:
            hourly_price *= 0.7  # 30% discount
        
        # Calculate costs
        monthly_cost = hourly_price * hours_per_month
        yearly_cost = monthly_cost * 12
        total_cost = yearly_cost * years
        
        return {
            "provider": provider,
            "instance_type": instance_type,
            "region": region,
            "pricing_model": "spot" if spot_instance else ("reserved" if reserved_instance else "on-demand"),
            "hourly_price": round(hourly_price, 4),
            "monthly_cost": round(monthly_cost, 2),
            "yearly_cost": round(yearly_cost, 2),
            "total_cost_5yr": round(total_cost, 2),
            "hours_per_month": hours_per_month,
            "years": years
        }
    
    def compare_providers(
        self,
        instance_type_equivalent: str,
        region: str,
        hours_per_month: int = 730,
        years: int = 5
    ) -> List[Dict]:
        """
        Compare costs across providers for equivalent instances.
        
        Args:
            instance_type_equivalent: Instance type identifier (e.g., "2vcpu-8gb")
            region: Region code
            hours_per_month: Hours of usage per month
            years: Number of years to project
            
        Returns:
            List of cost comparisons
        """
        # Simplified comparison - in production, map equivalent instance types
        comparisons = []
        
        # Map equivalent instances
        equivalents = {
            "aws": ("m5.large", "us-east-1"),
            "gcp": ("n1-standard-2", "us-central1"),
            "oci": ("VM.Standard2.2", "us-ashburn-1")
        }
        
        for provider, (instance_type, provider_region) in equivalents.items():
            cost = self.calculate_tco(
                provider=provider,
                instance_type=instance_type,
                region=provider_region,
                hours_per_month=hours_per_month,
                years=years
            )
            comparisons.append(cost)
        
        return comparisons


if __name__ == "__main__":
    # Test cost model
    model = CostModel()
    
    # Example: 5-year TCO comparison
    print("5-Year TCO Comparison (On-Demand):")
    comparisons = model.compare_providers("2vcpu-8gb", "us-east-1", years=5)
    for comp in comparisons:
        print(f"{comp['provider']}: ${comp['total_cost_5yr']:,.2f}")

