from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from .models import (
    NotificationRequest, NotificationResult, NotificationError,
    NotificationType
)
from .tasks import send_notification
from .websocket import NotificationManager
import json
import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, List, Any
import os
import redis
import requests

# Try to import sse_starlette, but provide a fallback if it's not available
try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:
    # Define a simple fallback for EventSourceResponse that works with FastAPI
    class EventSourceResponse(StreamingResponse):
        def __init__(self, content: AsyncGenerator[str, None], *args, **kwargs):
            async def event_generator():
                async for data in content:
                    if isinstance(data, dict):
                        data = json.dumps(data)
                    yield f"data: {data}\n\n"
            super().__init__(
                event_generator(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                *args,
                **kwargs
            )

# Try to import MessageBroker, but provide a fallback if it's not available
try:
    from common.messaging import MessageBroker
    message_broker = MessageBroker()
except ImportError:
    # Define a simple fallback for MessageBroker
    class MessageBroker:
        async def publish(self, *args, **kwargs):
            pass
    message_broker = MessageBroker()

app = FastAPI(title="Notification Service")
notification_manager = NotificationManager()

# In-memory store for client updates
client_updates = {}

def add_client_update(client_id: str, update: Dict[str, Any]):
    """Add an update for a client to be sent via SSE or WebSocket"""
    if client_id not in client_updates:
        client_updates[client_id] = []
    client_updates[client_id].append(update)

async def get_client_updates(client_id: str) -> list:
    """Get and clear updates for a client"""
    updates = client_updates.get(client_id, [])
    client_updates[client_id] = []
    return updates

@app.post("/notifications/")
async def create_notification(request: NotificationRequest):
    """Create and send a notification"""
    try:
        # Send notification via Celery task
        notification_data = request.dict()
        result = send_notification.delay(notification_data)
        
        # Prepare notification for client
        notification = {
            "type": "notification",
            "status": "sent",
            "content": request.content.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to client updates for SSE/WebSocket
        add_client_update(request.recipient.client_id, notification)
        
        # Send directly via WebSocket for immediate delivery
        await notification_manager.send_notification(request.recipient.client_id, notification)
        
        return {"status": "notification queued", "task_id": result.id}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send notification: {str(e)}"
        )

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time notifications"""
    await notification_manager.connect(client_id, websocket)
    try:
        # Send a test notification to confirm connection
        test_notification = {
            "type": "notification",
            "status": "sent",
            "content": {
                "subject": "Connection Established",
                "body": f"Successfully connected to notification service for client {client_id}",
                "variables": {
                    "connection_time": datetime.now().isoformat(),
                    "client_id": client_id
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_json(test_notification)
        
        # Send any existing notifications for this client
        updates = await get_client_updates(client_id)
        for update in updates:
            await websocket.send_json(update)
            
        # Keep the connection alive
        while True:
            data = await websocket.receive_text()
            # Echo back any received messages
            await websocket.send_json({"type": "echo", "data": data, "timestamp": datetime.now().isoformat()})
    except WebSocketDisconnect:
        await notification_manager.disconnect(client_id, websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
        await notification_manager.disconnect(client_id, websocket)

@app.get("/sse/{client_id}")
async def sse_endpoint(request: Request, client_id: str):
    """Server-Sent Events endpoint for real-time notifications"""
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
                
            # Check for new updates
            updates = await get_client_updates(client_id)
            if updates:
                for update in updates:
                    yield json.dumps(update)
            
            await asyncio.sleep(1)  # Poll every second
    
    return EventSourceResponse(event_generator())

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Loan Processing Dashboard</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                h1, h2 {
                    color: #333;
                    text-align: center;
                }
                .tabs {
                    display: flex;
                    justify-content: center;
                    margin: 20px 0;
                    padding: 10px;
                    background-color: #fff;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .tab {
                    padding: 12px 24px;
                    margin: 0 10px;
                    background-color: #eee;
                    border-radius: 5px;
                    cursor: pointer;
                    font-weight: bold;
                    font-size: 16px;
                    transition: all 0.3s ease;
                }
                .tab:hover {
                    background-color: #ddd;
                }
                .tab.active {
                    background-color: #007bff;
                    color: white;
                }
                .tab-content {
                    display: none;
                    padding: 20px;
                    background-color: #fff;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-top: 20px;
                }
                .tab-content.active {
                    display: block;
                }
                .status-update {
                    margin: 10px;
                    padding: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    background-color: white;
                }
                .sent { background-color: #dff0d8; }
                .failed { background-color: #f2dede; }
                .pending { background-color: #fcf8e3; }
                .notification { background-color: #d9edf7; }
                .timestamp {
                    color: #666;
                    font-size: 0.9em;
                }
                .content {
                    margin-top: 10px;
                }
                .no-notifications {
                    text-align: center;
                    color: #666;
                    margin-top: 30px;
                }
                .client-id {
                    text-align: center;
                    font-weight: bold;
                    margin-bottom: 20px;
                    padding: 10px;
                    background-color: #eee;
                    border-radius: 5px;
                }
                .variable-list {
                    margin-top: 10px;
                    padding: 10px;
                    background-color: #f9f9f9;
                    border-radius: 5px;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }
                th, td {
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: left;
                }
                th {
                    background-color: #f2f2f2;
                }
                tr:nth-child(even) {
                    background-color: #f9f9f9;
                }
                .application-details {
                    margin-top: 20px;
                    padding: 15px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    background-color: white;
                    display: none;
                }
                .btn {
                    padding: 5px 10px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    cursor: pointer;
                }
                .btn:hover {
                    background-color: #0056b3;
                }
                .approved { color: green; font-weight: bold; }
                .rejected { color: red; font-weight: bold; }
                .pending { color: orange; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>Loan Processing Dashboard</h1>
            
            <div class="tabs">
                <div class="tab active" onclick="showTab('notifications')">Notifications</div>
                <div class="tab" onclick="showTab('applications')">All Applications</div>
            </div>
            
            <div id="instructions" style="text-align: center; margin: 10px 0; padding: 10px; background-color: #ffffd0; border-radius: 5px;">
                <p><strong>Click on the "All Applications" tab above to view all loan applications in a table.</strong></p>
            </div>
            
            <div id="notifications" class="tab-content active">
                <div class="client-id">
                    Client ID: <span id="client-id">Loading...</span>
                </div>
                
                <div style="text-align: center; margin: 15px 0;">
                    <button class="btn" style="padding: 10px 20px; font-size: 16px;" onclick="showTab('applications')">
                        View All Loan Applications →
                    </button>
                </div>
                
                <div id="notifications-container">
                    <div class="no-notifications">
                        Waiting for notifications...
                    </div>
                </div>
            </div>
            
            <div id="applications" class="tab-content">
                <h2>All Loan Applications</h2>
                <table id="applications-table">
                    <thead>
                        <tr>
                            <th>Request ID</th>
                            <th>Client Name</th>
                            <th>Loan Amount</th>
                            <th>Credit Score</th>
                            <th>Property Value</th>
                            <th>Decision</th>
                            <th>Interest Rate</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="applications-body">
                        <tr>
                            <td colspan="8" style="text-align: center;">Loading applications...</td>
                        </tr>
                    </tbody>
                </table>
                
                <div id="application-details" class="application-details">
                    <h3>Application Details</h3>
                    <pre id="application-json"></pre>
                </div>
            </div>
            
            <script>
                // Get client ID from URL parameter
                const urlParams = new URLSearchParams(window.location.search);
                const clientId = urlParams.get('clientId');
                
                if (clientId) {
                    document.getElementById('client-id').textContent = clientId;
                    
                    // Connect to WebSocket for real-time notifications
                    const ws = new WebSocket(`ws://${window.location.host}/ws/${clientId}`);
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        if (data.type === 'notification') {
                            // Clear "no notifications" message if present
                            const noNotifications = document.querySelector('.no-notifications');
                            if (noNotifications) {
                                noNotifications.remove();
                            }
                            
                            // Create notification element
                            const notificationDiv = document.createElement('div');
                            notificationDiv.className = `status-update notification`;
                            
                            const content = data.content;
                            let notificationHtml = `
                                <div class="subject">${content.subject}</div>
                                <div class="message">${content.body}</div>
                                <div class="timestamp">Time: ${new Date(data.timestamp).toLocaleTimeString()}</div>
                            `;
                            
                            if (content.variables) {
                                notificationHtml += `<div class="variable-list">`;
                                for (const [key, value] of Object.entries(content.variables)) {
                                    notificationHtml += `<div>${key}: ${value}</div>`;
                                }
                                notificationHtml += `</div>`;
                            }
                            
                            notificationDiv.innerHTML = notificationHtml;
                            
                            // Add to notifications container
                            document.getElementById('notifications-container').prepend(notificationDiv);
                        }
                    };
                    
                    ws.onclose = function(event) {
                        console.log('Connection closed');
                    };
                    
                    ws.onerror = function(error) {
                        console.error('WebSocket error:', error);
                    };
                } else {
                    document.getElementById('client-id').textContent = 'No client ID provided';
                }
                
                // Function to show tab content
                function showTab(tabId) {
                    // Hide all tab contents
                    const tabContents = document.querySelectorAll('.tab-content');
                    tabContents.forEach(content => {
                        content.classList.remove('active');
                    });
                    
                    // Deactivate all tabs
                    const tabs = document.querySelectorAll('.tab');
                    tabs.forEach(tab => {
                        tab.classList.remove('active');
                    });
                    
                    // Show selected tab content
                    document.getElementById(tabId).classList.add('active');
                    
                    // Activate selected tab
                    document.querySelector(`.tab[onclick="showTab('${tabId}')"]`).classList.add('active');
                    
                    // Load applications data if applications tab is selected
                    if (tabId === 'applications') {
                        loadApplications();
                    }
                }
                
                // Function to load all applications
                function loadApplications() {
                    fetch('/api/loan-applications')
                        .then(response => response.json())
                        .then(applications => {
                            const tableBody = document.getElementById('applications-body');
                            tableBody.innerHTML = '';
                            
                            if (applications.length === 0) {
                                tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No applications found</td></tr>';
                                return;
                            }
                            
                            applications.forEach(app => {
                                const row = document.createElement('tr');
                                
                                // Get the loan request data
                                const loanRequest = app.loan_request || {};
                                const creditCheck = app.credit_check || {};
                                const propertyEval = app.property_evaluation || {};
                                const decision = app.decision || {};
                                
                                // Create decision status class
                                let statusClass = 'pending';
                                if (decision.status === 'APPROVED') {
                                    statusClass = 'approved';
                                } else if (decision.status === 'REJECTED') {
                                    statusClass = 'rejected';
                                }
                                
                                row.innerHTML = `
                                    <td>${app.request_id}</td>
                                    <td>${loanRequest.client_name || 'N/A'}</td>
                                    <td>${loanRequest.loan_amount || 'N/A'}</td>
                                    <td>${creditCheck.credit_score || 'N/A'}</td>
                                    <td>${propertyEval.estimated_value || 'N/A'}</td>
                                    <td class="${statusClass}">${decision.status || 'PENDING'}</td>
                                    <td>${decision.proposed_rate || 'N/A'}</td>
                                    <td><button class="btn" onclick="viewApplicationDetails('${app.request_id}')">View Details</button></td>
                                `;
                                
                                tableBody.appendChild(row);
                            });
                        })
                        .catch(error => {
                            console.error('Error loading applications:', error);
                            document.getElementById('applications-body').innerHTML = 
                                '<tr><td colspan="8" style="text-align: center;">Error loading applications</td></tr>';
                        });
                }
                
                // Function to view application details
                function viewApplicationDetails(requestId) {
                    fetch(`/api/loan-application/${requestId}`)
                        .then(response => response.json())
                        .then(application => {
                            const detailsDiv = document.getElementById('application-details');
                            const jsonPre = document.getElementById('application-json');
                            
                            jsonPre.textContent = JSON.stringify(application, null, 2);
                            detailsDiv.style.display = 'block';
                            
                            // Scroll to details
                            detailsDiv.scrollIntoView({ behavior: 'smooth' });
                        })
                        .catch(error => {
                            console.error('Error loading application details:', error);
                            alert('Error loading application details');
                        });
                }
                
                // Initial load of applications if applications tab is active
                if (document.getElementById('applications').classList.contains('active')) {
                    loadApplications();
                }
            </script>
        </body>
    </html>
    """

@app.get("/api/loan-applications")
async def get_all_loan_applications():
    """Get all loan applications with their complete data"""
    try:
        # Get all client IDs from Redis (using pattern matching)
        redis_client = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', 6379)),
            db=0
        )
        
        # Get all keys that match the pattern 'decision:*'
        decision_keys = redis_client.keys('decision:*')
        request_ids = [key.decode('utf-8').split(':')[1] for key in decision_keys]
        
        # Fetch data for each loan application
        loan_applications = []
        
        for request_id in request_ids:
            application_data = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Get loan request data
            try:
                loan_service_url = os.environ.get('LOAN_SERVICE_URL', 'http://loan-request-service:8000')
                response = requests.get(f"{loan_service_url}/loan-requests/{request_id}")
                if response.status_code == 200:
                    application_data["loan_request"] = response.json()
            except Exception as e:
                application_data["loan_request_error"] = str(e)
            
            # Get credit check data
            try:
                credit_service_url = os.environ.get('CREDIT_SERVICE_URL', 'http://credit-check-service:8001')
                response = requests.get(f"{credit_service_url}/credit-check/{request_id}")
                if response.status_code == 200:
                    application_data["credit_check"] = response.json()
            except Exception as e:
                application_data["credit_check_error"] = str(e)
            
            # Get property evaluation data
            try:
                property_service_url = os.environ.get('PROPERTY_SERVICE_URL', 'http://property-evaluation-service:8002')
                response = requests.get(f"{property_service_url}/evaluations/{request_id}")
                if response.status_code == 200:
                    application_data["property_evaluation"] = response.json()
            except Exception as e:
                application_data["property_evaluation_error"] = str(e)
            
            # Get decision data
            try:
                decision_service_url = os.environ.get('DECISION_SERVICE_URL', 'http://decision-service:8003')
                response = requests.get(f"{decision_service_url}/decisions/{request_id}")
                if response.status_code == 200:
                    application_data["decision"] = response.json()
            except Exception as e:
                application_data["decision_error"] = str(e)
            
            loan_applications.append(application_data)
        
        return loan_applications
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve loan applications: {str(e)}"
        )

@app.get("/api/loan-application/{request_id}")
async def get_loan_application(request_id: str):
    """Get a specific loan application with complete data"""
    try:
        application_data = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get loan request data
        try:
            loan_service_url = os.environ.get('LOAN_SERVICE_URL', 'http://loan-request-service:8000')
            response = requests.get(f"{loan_service_url}/loan-requests/{request_id}")
            if response.status_code == 200:
                application_data["loan_request"] = response.json()
        except Exception as e:
            application_data["loan_request_error"] = str(e)
        
        # Get credit check data
        try:
            credit_service_url = os.environ.get('CREDIT_SERVICE_URL', 'http://credit-check-service:8001')
            response = requests.get(f"{credit_service_url}/credit-check/{request_id}")
            if response.status_code == 200:
                application_data["credit_check"] = response.json()
        except Exception as e:
            application_data["credit_check_error"] = str(e)
        
        # Get property evaluation data
        try:
            property_service_url = os.environ.get('PROPERTY_SERVICE_URL', 'http://property-evaluation-service:8002')
            response = requests.get(f"{property_service_url}/evaluations/{request_id}")
            if response.status_code == 200:
                application_data["property_evaluation"] = response.json()
        except Exception as e:
            application_data["property_evaluation_error"] = str(e)
        
        # Get decision data
        try:
            decision_service_url = os.environ.get('DECISION_SERVICE_URL', 'http://decision-service:8003')
            response = requests.get(f"{decision_service_url}/decisions/{request_id}")
            if response.status_code == 200:
                application_data["decision"] = response.json()
        except Exception as e:
            application_data["decision_error"] = str(e)
        
        return application_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve loan application: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}