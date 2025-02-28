from common.celery_app import celery_app, TASK_LATENCY, TASK_FAILURE_COUNTER
from celery.utils.log import get_task_logger
from .models import (
    EvaluationRequest, PropertyEvaluation, EvaluationError,
    PropertyCondition, RiskLevel, LocationQuality
)
from decimal import Decimal
import json
from datetime import datetime
import numpy as np
from typing import Dict, List
import os
from functools import wraps
import time
from .market_data import (
    generate_comparable_properties,
    calculate_price_trend,
    assess_location_quality
)

logger = get_task_logger(__name__)

def monitor_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        task_name = func.__name__
        try:
            result = func(*args, **kwargs)
            TASK_LATENCY.labels(task_name=task_name).observe(
                time.time() - start_time
            )
            return result
        except Exception as e:
            TASK_FAILURE_COUNTER.labels(task_name=task_name).inc()
            logger.error(f"Task {task_name} failed: {str(e)}")
            raise
    return wrapper

@celery_app.task(name='property_evaluation.evaluate_property')
def evaluate_property(self, evaluation_request: Dict) -> Dict:
    try:
        request = EvaluationRequest(**evaluation_request)
        
        # Get market data locally instead of from external API
        market_data = analyze_market_data(
            request.address.dict(),
            request.property_details.dict()
        )
        
        # Calculate estimated value
        estimated_value = calculate_base_value(
            request.property_details.dict(),
            market_data
        )
        
        # Assess risk and loan viability
        risk_assessment = assess_risk(
            estimated_value=estimated_value,
            loan_amount=request.loan_amount,
            market_data=market_data,
            property_details=request.property_details.dict()
        )
        
        evaluation = PropertyEvaluation(
            request_id=request.request_id,
            address=request.address,
            property_details=request.property_details,
            market_analysis=market_data,
            estimated_value=estimated_value,
            confidence_score=calculate_confidence_score(
                market_data['comparable_properties'],
                risk_assessment['condition'],
                request.property_details.dict()
            ),
            condition_assessment=risk_assessment['condition'],
            risk_assessment=risk_assessment['risk_level'],
            loan_to_value_ratio=float(request.loan_amount / estimated_value),
            evaluator="AUTOMATED_SYSTEM"
        )
        
        return evaluation.dict()
        
    except Exception as exc:
        logger.error(f"Property evaluation failed: {str(exc)}")
        if self is not None:
            self.retry(exc=exc)
        else:
            raise exc

def assess_risk(
    estimated_value: Decimal,
    loan_amount: Decimal,
    market_data: Dict,
    property_details: Dict
) -> Dict:
    """Enhanced risk assessment"""
    ltv_ratio = loan_amount / estimated_value
    market_trend = market_data['price_trend_1y']
    property_age = datetime.now().year - property_details.get('construction_year', datetime.now().year)
    
    risk_factors = {
        'ltv_ratio': ltv_ratio,
        'market_trend': market_trend,
        'property_age': property_age,
        'location_quality': market_data.get('location_rating')
    }
    
    # Determine risk level based on multiple factors
    if ltv_ratio > Decimal('0.9') or market_trend < -5:
        risk_level = RiskLevel.VERY_HIGH
    elif ltv_ratio > Decimal('0.8') or market_trend < -2:
        risk_level = RiskLevel.HIGH
    elif ltv_ratio > Decimal('0.7') or market_trend < 0:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW
        
    return {
        'risk_level': risk_level,
        'risk_factors': risk_factors,
        'condition': assess_property_condition(property_details)
    }

def analyze_market_data(address: Dict, property_details: Dict) -> Dict:
    """
    Analyzes market data for the property location using local simulation
    instead of external API calls
    """
    try:
        # Generate comparable properties locally
        comparable_properties = generate_comparable_properties(
            address,
            property_details
        )
        
        # Calculate average price per m2
        prices_per_m2 = [
            float(prop['price_per_m2'])
            for prop in comparable_properties
        ]
        avg_price_per_m2 = Decimal(str(np.mean(prices_per_m2)))
        
        # Calculate price trends locally
        price_trend_6m = calculate_price_trend(comparable_properties, months=6)
        price_trend_1y = calculate_price_trend(comparable_properties, months=12)
        
        # Assess location quality locally
        location_rating = assess_location_quality(address)
        
        # Calculate average time on market
        avg_time_on_market = int(np.mean([
            prop['days_on_market'] for prop in comparable_properties
        ]))
        
        return {
            'average_price_per_m2': avg_price_per_m2,
            'price_trend_6m': price_trend_6m,
            'price_trend_1y': price_trend_1y,
            'average_time_on_market': avg_time_on_market,
            'comparable_properties': comparable_properties,
            'location_rating': location_rating
        }
        
    except Exception as e:
        logger.error(f"Market analysis failed: {str(e)}")
        raise

def calculate_base_value(property_details: Dict, market_data: Dict) -> Decimal:
    """
    Calculates base property value using market data
    """
    base_price_per_m2 = market_data['average_price_per_m2']
    surface_area = Decimal(str(property_details['surface_area']))
    
    return base_price_per_m2 * surface_area

def assess_property_condition(property_details: Dict) -> PropertyCondition:
    """
    Assesses property condition based on available information
    """
    if not property_details.get('construction_year'):
        return PropertyCondition.FAIR
        
    age = datetime.now().year - property_details['construction_year']
    
    if age < 5:
        return PropertyCondition.EXCELLENT
    elif age < 15:
        return PropertyCondition.GOOD
    elif age < 30:
        return PropertyCondition.FAIR
    else:
        return PropertyCondition.RENOVATION_NEEDED

def calculate_confidence_score(
    comparable_properties: List[Dict],
    condition: PropertyCondition,
    property_details: Dict
) -> float:
    """
    Calculates confidence score for the evaluation
    """
    base_score = 0.7  # Base confidence score
    
    # Adjust based on number of comparables
    num_comparables = len(comparable_properties)
    if num_comparables >= 10:
        base_score += 0.2
    elif num_comparables >= 5:
        base_score += 0.1
    
    # Adjust based on property condition
    if condition in [PropertyCondition.EXCELLENT, PropertyCondition.GOOD]:
        base_score += 0.1
    
    return min(1.0, base_score)