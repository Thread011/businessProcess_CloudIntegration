#!/bin/bash

# Function to handle errors
handle_error() {
    local response=$1
    local step=$2
    if echo "$response" | grep -q "error\|Error\|ERROR"; then
        echo "Warning in $step:"
        echo "$response"
        # Don't exit immediately, continue with the process
    fi
}

# Function to wait for service health
wait_for_service() {
    local service_url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    echo "Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$service_url/health" | grep -q "healthy"; then
            echo "$service_name is ready"
            return 0
        fi
        echo "Attempt $attempt: $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "$service_name failed to become ready"
    return 1
}

# Wait for all services to be ready
wait_for_service "http://localhost:8000" "Loan Request Service"
wait_for_service "http://localhost:8001" "Credit Check Service"
wait_for_service "http://localhost:8002" "Property Evaluation Service"
wait_for_service "http://localhost:8003" "Decision Service"
wait_for_service "http://localhost:8004" "Notification Service"

# Generate a unique request ID
REQUEST_ID="LOAN_$(date +%Y%m%d_%H%M%S)"

echo "1. Creating loan request..."
RESPONSE=$(curl -s -X POST http://localhost:8000/loan-requests/ \
-H "Content-Type: application/json" \
-d '{
    "client_name": "Jean Dupont",
    "address": "123 Rue de Paris, 75001 Paris",
    "email": "jean.dupont@email.com",
    "phone": "+33612345678",
    "loan_amount": 250000.00,
    "loan_duration_years": 20,
    "property_description": "3-bedroom apartment in Paris",
    "monthly_income": 5000.00,
    "monthly_expenses": 1500.00
}')

echo "Response: $RESPONSE"
handle_error "$RESPONSE" "loan request creation"

echo -e "\n2. Initiating credit check..."
RESPONSE=$(curl -s -X POST http://localhost:8001/credit-check/ \
-H "Content-Type: application/json" \
-d '{
    "request_id": "'$REQUEST_ID'",
    "client_name": "Jean Dupont",
    "monthly_income": 5000.00,
    "monthly_expenses": 1500.00,
    "existing_loans": 0,
    "employment_years": 5
}')
echo "Credit check response: $RESPONSE"
handle_error "$RESPONSE" "credit check"

echo -e "\n3. Requesting property evaluation..."
RESPONSE=$(curl -s -X POST http://localhost:8002/evaluations/ \
-H "Content-Type: application/json" \
-d '{
    "request_id": "'$REQUEST_ID'",
    "address": {
        "street": "123 Rue de Paris",
        "city": "Paris",
        "postal_code": "75001",
        "country": "France"
    },
    "property_details": {
        "property_type": "APARTMENT",
        "surface_area": 85.5,
        "rooms": 3,
        "construction_year": 1995,
        "condition": "GOOD"
    },
    "loan_amount": 250000.00,
    "additional_info": {
        "current_usage": "RESIDENTIAL",
        "renovation_needed": false
    }
}')
echo "Property evaluation response: $RESPONSE"
handle_error "$RESPONSE" "property evaluation"

# Add delay to allow for async processing
echo "Waiting for property evaluation to complete..."
sleep 15

echo -e "\n4. Waiting for decision..."
sleep 10  # Wait for processing
RESPONSE=$(curl -s -X GET "http://localhost:8003/decisions/$REQUEST_ID")
echo "Decision response: $RESPONSE"
handle_error "$RESPONSE" "decision"

echo -e "\n5. Opening dashboard to view notifications..."
echo "Please open http://localhost:8004/dashboard in your browser"
echo "You should see real-time updates for request ID: $REQUEST_ID"

# Optional: Wait for user to view dashboard
read -p "Press Enter to exit..." 