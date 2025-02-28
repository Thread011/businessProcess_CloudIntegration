import random
from decimal import Decimal
from typing import Dict, List
from datetime import datetime, timedelta
from .models import LocationQuality

def generate_comparable_properties(address: Dict, property_details: Dict, num_properties: int = 8) -> List[Dict]:
    """
    Generate a list of comparable properties based on the given property details
    """
    comparable_properties = []
    base_price_per_m2 = get_base_price_for_location(address)
    property_type = property_details.get('property_type')
    surface_area = property_details.get('surface_area')
    
    for i in range(num_properties):
        # Vary surface area slightly
        comp_surface_area = max(10, surface_area * random.uniform(0.8, 1.2))
        
        # Vary price per m2 based on random factors
        price_variation = random.uniform(0.85, 1.15)
        price_per_m2 = base_price_per_m2 * price_variation
        
        # Calculate total price
        total_price = Decimal(str(price_per_m2 * comp_surface_area))
        
        # Generate random sale date within the last 12 months
        days_ago = random.randint(1, 365)
        sale_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        comparable_properties.append({
            'id': f"COMP_{i+1}",
            'property_type': property_type,
            'surface_area': comp_surface_area,
            'price': total_price,
            'price_per_m2': Decimal(str(price_per_m2)),
            'rooms': max(1, property_details.get('rooms', 2) + random.randint(-1, 1)),
            'sale_date': sale_date,
            'days_on_market': random.randint(15, 90)
        })
    
    return comparable_properties

def get_base_price_for_location(address: Dict) -> Decimal:
    """
    Determine a base price per square meter based on the location
    """
    # Map of postal code prefixes to base prices
    postal_code = address.get('postal_code', '75000')
    
    # Paris (75) and surrounding areas have higher prices
    if postal_code.startswith('75'):
        return Decimal(str(random.uniform(9000, 12000)))
    elif postal_code.startswith(('92', '93', '94')):
        return Decimal(str(random.uniform(6000, 9000)))
    elif postal_code.startswith(('77', '78', '91', '95')):
        return Decimal(str(random.uniform(4000, 6000)))
    # Other major cities
    elif postal_code.startswith(('69', '33', '59', '31', '06')):
        return Decimal(str(random.uniform(3500, 5500)))
    # Rest of France
    else:
        return Decimal(str(random.uniform(2000, 3500)))

def calculate_price_trend(comparable_properties: List[Dict], months: int = 6) -> float:
    """
    Calculate price trend over the specified number of months
    """
    # Simulate a price trend based on the location and current market conditions
    # In a real system, this would analyze the actual sales data
    return random.uniform(-3.0, 5.0)

def assess_location_quality(address: Dict) -> LocationQuality:
    """
    Assess the quality of the location based on the address
    """
    postal_code = address.get('postal_code', '75000')
    
    # Premium locations in Paris and French Riviera
    if postal_code.startswith(('75', '06', '92')):
        return random.choice([LocationQuality.PREMIUM, LocationQuality.GOOD])
    # Good locations in major cities
    elif postal_code.startswith(('69', '33', '59', '31', '13')):
        return random.choice([LocationQuality.GOOD, LocationQuality.AVERAGE])
    # Average locations in suburbs and medium cities
    elif postal_code.startswith(('77', '78', '91', '94', '95')):
        return random.choice([LocationQuality.AVERAGE, LocationQuality.BELOW_AVERAGE])
    # Other locations
    else:
        return random.choice([LocationQuality.AVERAGE, LocationQuality.BELOW_AVERAGE])