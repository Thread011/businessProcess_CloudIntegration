import requests
import time

SERVICES = {
    "Loan Request": "http://localhost:8000/health",
    "Credit Check": "http://localhost:8001/health",
    "Property Evaluation": "http://localhost:8002/health"
}

def check_services_health():
    print("\n=== Checking Services Health ===\n")
    all_healthy = True
    
    for service_name, url in SERVICES.items():
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"✅ {service_name}: Healthy")
            else:
                print(f"❌ {service_name}: Unhealthy (Status: {response.status_code})")
                all_healthy = False
        except requests.RequestException as e:
            print(f"❌ {service_name}: Not responding ({str(e)})")
            all_healthy = False
    
    return all_healthy

if __name__ == "__main__":
    check_services_health()