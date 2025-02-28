import requests
import json
from datetime import datetime, timedelta
import time
import websocket
import threading

# Base URLs
LOAN_SERVICE_URL = "http://localhost:18010"
CREDIT_CHECK_URL = "http://localhost:18011"
PROPERTY_EVAL_URL = "http://localhost:18012"
DECISION_SERVICE_URL = "http://localhost:18013"
NOTIFICATION_SERVICE_URL = "http://localhost:18014"

# Function to handle WebSocket notifications
def on_message(ws, message):
    data = json.loads(message)
    if data.get("type") == "notification":
        content = data["content"]
        print(f"\n[!] New Notification:")
        print(f"  > Subject: {content['subject']}")
        print(f"  > Message: {content['body']}")
        if content.get('variables'):
            print("  > Details:")
            for key, value in content['variables'].items():
                print(f"    - {key}: {value}")
        print(f"  > Time: {datetime.fromisoformat(data['timestamp']).strftime('%H:%M:%S')}\n")

def on_error(ws, error):
    print(f"\n[X] Connection Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("\n[-] Connection closed")

def on_open(ws):
    print("\n[+] Connected to notification service")

def start_websocket(client_id):
    ws_url = f"ws://localhost:18014/ws/{client_id}"
    ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    return ws

# Function to create loan request data with different financial profiles
def create_loan_request(profile_type="medium"):
    """
    Create a loan request with different financial profiles:
    - poor: Low credit score, high DTI ratio
    - medium: Average credit score, moderate DTI ratio
    - rich: High credit score, low DTI ratio
    """
    # Base loan request data
    request_data = {
        "client_name": f"John Doe ({profile_type.capitalize()})",
        "email": f"john.doe.{profile_type}@example.com",
        "phone": "+33123456789",
        "birth_date": (datetime.now() - timedelta(days=30*365)).isoformat(),  # 30 years old
        "nationality": "French",
        "current_address": {
            "street": "123 Rue de Paris",
            "city": "Paris",
            "postal_code": "75001",
            "country": "France"
        },
        "loan_purpose": "PURCHASE",
        "loan_duration_years": 20,
        "employment_info": {
            "employer_name": "Tech Corp",
            "position": "Engineer",
            "contract_type": "CDI",
        },
        "property_info": {
            "type": "APARTMENT",
            "address": {
                "street": "456 Avenue des Champs-Élysées",
                "city": "Paris",
                "postal_code": "75008",
                "country": "France"
            },
            "surface_area": 85,
            "rooms": 3,
            "construction_year": 2010,
            "description": "Modern apartment in prime location",
            "condition": "EXCELLENT"
        }
    }
    
    # Adjust values based on profile type
    if profile_type == "poor":
        # Low income, high expenses, lower property value, higher loan amount
        request_data["monthly_income"] = "3500"
        request_data["monthly_expenses"] = "2000"
        request_data["loan_amount"] = "300000"
        request_data["employment_info"]["years_employed"] = 2
        request_data["employment_info"]["annual_income"] = "42000"
        request_data["property_info"]["estimated_value"] = "320000"
    
    elif profile_type == "medium":
        # Medium income, moderate expenses, balanced property value and loan
        request_data["monthly_income"] = "6250"
        request_data["monthly_expenses"] = "2000"
        request_data["loan_amount"] = "250000"
        request_data["employment_info"]["years_employed"] = 5
        request_data["employment_info"]["annual_income"] = "75000"
        request_data["property_info"]["estimated_value"] = "450000"
    
    elif profile_type == "rich":
        # High income, low expenses relative to income, lower loan to value ratio
        request_data["monthly_income"] = "12000"
        request_data["monthly_expenses"] = "3000"
        request_data["loan_amount"] = "400000"
        request_data["employment_info"]["years_employed"] = 10
        request_data["employment_info"]["annual_income"] = "144000"
        request_data["property_info"]["estimated_value"] = "850000"
    
    return request_data

# Function to process a loan request and display results
def process_loan_request(profile_type="medium"):
    print("\n" + "="*80)
    print(f" Loan Processing for {profile_type.upper()} Profile ".center(80, "="))
    print("="*80 + "\n")
    
    # Get loan request data for the specified profile
    loan_request_data = create_loan_request(profile_type)
    
    # 1. Submit loan request
    print("[1] Submitting Loan Request")
    print("-"*60)
    response = requests.post(
        f"{LOAN_SERVICE_URL}/loan-requests/",
        json=loan_request_data
    )
    
    if response.status_code != 200:
        print(f"[X] Error: {response.text}")
        return
    
    request_id = response.json()["request_id"]
    print(f"[+] Request submitted successfully")
    print(f"[>] Request ID: {request_id}\n")
    
    # Start WebSocket connection for notifications
    ws = start_websocket(request_id)
    print("[*] Processing request (5 seconds)...")
    time.sleep(5)
    
    # 2. Check credit evaluation
    print("\n[2] Credit Evaluation")
    print("-"*60)
    response = requests.get(f"{CREDIT_CHECK_URL}/credit-check/{request_id}")
    if response.status_code == 200:
        credit_check = response.json()
        print(f"[>] Credit Score: {credit_check['credit_score']}")
        print(f"[>] DTI Ratio: {credit_check['dti_ratio']:.2f}")
        print(f"[>] Eligibility: {'Approved' if credit_check['is_eligible'] else 'Rejected'}\n")
    else:
        print(f"[X] Credit check failed: {response.text}\n")
    
    # 3. Check property evaluation
    print("[3] Property Evaluation")
    print("-"*60)
    response = requests.get(f"{PROPERTY_EVAL_URL}/evaluations/{request_id}")
    if response.status_code == 200:
        property_evaluation = response.json()
        print(f"[>] Estimated Value: €{property_evaluation['estimated_value']:,.2f}")
        print(f"[>] Risk Level: {property_evaluation['risk_assessment']}")
        print(f"[>] LTV Ratio: {property_evaluation['ltv_ratio']:.2%}\n")
    else:
        print(f"[X] Property evaluation failed: {response.text}\n")
    
    # 4. Check decision result
    print("[4] Loan Decision")
    print("-"*60)
    
    # First, create a decision request
    decision_request = {
        "request_id": request_id,
        "application_summary": {
            "request_id": request_id,
            "client_name": loan_request_data["client_name"],
            "loan_amount": loan_request_data["loan_amount"],
            "loan_duration_years": loan_request_data["loan_duration_years"],
            "property_value": property_evaluation["estimated_value"],
            "monthly_income": loan_request_data["monthly_income"],
            "monthly_expenses": loan_request_data["monthly_expenses"],
            "credit_score": credit_check["credit_score"],
            "dti_ratio": credit_check["dti_ratio"],
            "property_assessment_result": property_evaluation["risk_assessment"]
        },
        "criteria": {
            "min_credit_score": 650,
            "max_dti_ratio": 0.43,
            "min_property_value_ratio": 1.2,
            "max_loan_to_income_ratio": 4.0
        }
    }
    
    # Submit the decision request
    response = requests.post(
        f"{DECISION_SERVICE_URL}/decisions/",
        json=decision_request
    )
    
    if response.status_code == 200:
        print("[+] Decision request submitted successfully")
        decision_response = response.json()
        print(f"[>] Initial Status: {decision_response['status']}")
        
        # Wait a moment for the decision to be processed
        print("[*] Waiting for decision processing (5 seconds)...")
        time.sleep(5)
    else:
        print(f"[X] Failed to create decision: {response.text}")
    
    # Now check the decision result
    response = requests.get(f"{DECISION_SERVICE_URL}/decisions/{request_id}")
    if response.status_code == 200:
        decision = response.json()
        print(f"[>] Decision: {decision['status'].upper()}")
        print(f"[>] Interest Rate: {decision.get('proposed_rate', 'N/A')}%")
        if decision.get('requirements'):
            print("[>] Requirements:")
            for req in decision['requirements']:
                print(f"    - {req}")
        if decision.get('notes'):
            print("[>] Notes:")
            for note in decision['notes']:
                print(f"    - {note}")
        print()
    else:
        print(f"[X] Decision service failed: {response.text}\n")
    
    # 5. Test notification service
    print("[5] Notification System")
    print("-"*60)
    notification_request = {
        "request_id": request_id,
        "notification_type": "INTERNAL",
        "priority": "MEDIUM",
        "recipient": {
            "client_id": request_id,
            "name": loan_request_data["client_name"],
            "language": "fr"
        },
        "content": {
            "subject": "Loan Application Update",
            "body": "Your loan application is being processed",
            "template_id": "APPLICATION_APPROVED",
            "variables": {
                "client_name": loan_request_data["client_name"],
                "loan_amount": loan_request_data["loan_amount"]
            },
            "status": "PENDING"
        }
    }
    
    response = requests.post(
        f"{NOTIFICATION_SERVICE_URL}/notifications/",
        json=notification_request
    )
    
    if response.status_code == 200:
        print("[+] Notification sent successfully\n")
    else:
        print(f"[X] Notification failed: {response.text}\n")
    
    # 6. Show dashboard URL
    print("[6] Dashboard Access")
    print("-"*60)
    dashboard_url = f"{NOTIFICATION_SERVICE_URL}/dashboard?clientId={request_id}"
    print(f"[>] View your application status:")
    print(f"    {dashboard_url}\n")
    
    # Wait for notifications
    print("[*] Waiting for notifications...")
    time.sleep(5)
    
    # Cleanup
    ws.close()
    print("\n" + "="*60)
    print(f" Process Complete for {profile_type.upper()} Profile ".center(60, "="))
    print("="*60 + "\n")
    return request_id

if __name__ == "__main__":
    # Process loan requests for different financial profiles
    print("\n" + "="*80)
    print(" Loan Processing System - Testing All Financial Profiles ".center(80, "="))
    print("="*80 + "\n")
    
    # Process a poor financial profile
    poor_request_id = process_loan_request("poor")
    
    # Process a medium financial profile
    medium_request_id = process_loan_request("medium")
    
    # Process a rich financial profile
    rich_request_id = process_loan_request("rich")
    
    print("\n" + "="*80)
    print(" All Financial Profiles Tested ".center(80, "="))
    print("="*80 + "\n")