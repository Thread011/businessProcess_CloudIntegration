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
                h1 {
                    color: #333;
                    text-align: center;
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
                .variable-item {
                    margin: 5px 0;
                }
            </style>
            <script>
                // Get client ID from URL or generate one
                const urlParams = new URLSearchParams(window.location.search);
                const clientId = urlParams.get('clientId') || `CLIENT_${Date.now()}`;
                
                // WebSocket connection with retry
                function connectWebSocket() {
                    // Use the absolute WebSocket URL with the correct port
                    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${wsProtocol}//${window.location.hostname}:18014/ws/${clientId}`;
                    console.log('Connecting to WebSocket:', wsUrl);
                    
                    const ws = new WebSocket(wsUrl);
                    
                    ws.onopen = () => {
                        console.log('WebSocket connected');
                        addStatusMessage('Connected to notification service');
                    };
                    
                    ws.onclose = () => {
                        console.log('WebSocket disconnected. Retrying in 5s...');
                        addStatusMessage('Disconnected from notification service. Retrying...');
                        setTimeout(connectWebSocket, 5000);
                    };
                    
                    ws.onerror = (error) => {
                        console.error('WebSocket error:', error);
                        addStatusMessage('Error connecting to notification service');
                    };
                    
                    ws.onmessage = (event) => {
                        console.log('WebSocket message received:', event.data);
                        try {
                            const notification = JSON.parse(event.data);
                            updateDashboard(notification);
                        } catch (error) {
                            console.error('Error parsing WebSocket message:', error);
                            addStatusMessage('Error processing notification: ' + error.message);
                        }
                    };
                    
                    return ws;
                }

                function addStatusMessage(message) {
                    const statusDiv = document.getElementById('status-updates');
                    const noNotifications = document.getElementById('no-notifications');
                    if (noNotifications) {
                        noNotifications.style.display = 'none';
                    }
                    
                    const messageElement = document.createElement('div');
                    messageElement.className = 'status-update';
                    messageElement.innerHTML = `
                        <div class="timestamp">${new Date().toLocaleString()}</div>
                        <div class="content">${message}</div>
                    `;
                    statusDiv.insertBefore(messageElement, statusDiv.firstChild);
                }

                function updateDashboard(data) {
                    const statusDiv = document.getElementById('status-updates');
                    const noNotifications = document.getElementById('no-notifications');
                    if (noNotifications) {
                        noNotifications.style.display = 'none';
                    }
                    
                    console.log('Received data:', JSON.stringify(data));
                    
                    const updateElement = document.createElement('div');
                    updateElement.className = `status-update ${data.type === 'notification' ? 'notification' : ''} ${data.status ? data.status.toLowerCase() : 'pending'}`;
                    
                    let content = '';
                    
                    if (data.type === 'notification') {
                        // Format variables as a list if they exist
                        let variablesHtml = '';
                        if (data.content && data.content.variables) {
                            variablesHtml = `
                                <div class="variable-list">
                                    ${Object.entries(data.content.variables).map(([key, value]) => 
                                        `<div class="variable-item"><strong>${key}:</strong> ${value}</div>`
                                    ).join('')}
                                </div>
                            `;
                        }
                        
                        content = `
                            <div class="timestamp">${new Date(data.timestamp).toLocaleString()}</div>
                            <div class="content">
                                <h3>${data.content.subject || 'Notification'}</h3>
                                <p>${data.content.body || ''}</p>
                                ${variablesHtml}
                            </div>
                        `;
                    } else {
                        content = `
                            <div class="timestamp">${new Date(data.timestamp || Date.now()).toLocaleString()}</div>
                            <div class="content">
                                <p>${typeof data === 'object' ? JSON.stringify(data) : data}</p>
                            </div>
                        `;
                    }
                    
                    updateElement.innerHTML = content;
                    statusDiv.insertBefore(updateElement, statusDiv.firstChild);
                }

                // Initialize dashboard on page load
                document.addEventListener('DOMContentLoaded', function() {
                    // Update client ID display
                    document.getElementById('client-id-display').textContent = clientId;
                    
                    // Add initial message
                    addStatusMessage('Dashboard initialized for client: ' + clientId);
                    
                    // Connect WebSocket
                    const ws = connectWebSocket();
                    
                    // SSE connection
                    const sseUrl = `/sse/${clientId}`;
                    console.log('Connecting to SSE:', sseUrl);
                    const eventSource = new EventSource(sseUrl);
                    
                    eventSource.onmessage = function(event) {
                        console.log('SSE message received:', event.data);
                        try {
                            const update = JSON.parse(event.data);
                            updateDashboard(update);
                        } catch (error) {
                            console.error('Error parsing SSE message:', error);
                            addStatusMessage('Error processing SSE update: ' + error.message);
                        }
                    };
                    
                    eventSource.onerror = function(error) {
                        console.error('SSE error:', error);
                        addStatusMessage('Error with SSE connection');
                    };
                });
            </script>
        </head>
        <body>
            <h1>Loan Processing Dashboard</h1>
            <div class="client-id">Client ID: <span id="client-id-display"></span></div>
            <div id="status-updates">
                <div id="no-notifications" class="no-notifications">
                    No notifications yet. Waiting for updates...
                </div>
            </div>
        </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}