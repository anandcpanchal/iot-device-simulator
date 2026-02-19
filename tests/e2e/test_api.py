import pytest
from fastapi import status

@pytest.mark.asyncio
async def test_create_and_get_device(client):
    device_data = {
        "uuid": "test-device-1",
        "name": "E2E Device",
        "publish_topic": "e2e/test",
        "interval_ms": 1000,
        "params": [
            {"param_name": "temp", "type": "float", "min_val": 20.0, "max_val": 30.0}
        ]
    }
    
    # Create
    response = client.post("/api/devices", json=device_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "E2E Device"
    assert len(data["params"]) == 1
    
    # Get
    response = client.get(f"/api/devices/{data['uuid']}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "E2E Device"

@pytest.mark.asyncio
async def test_list_devices(client):
    # Insert multiple
    client.post("/api/devices", json={"uuid": "d1", "name": "Dev1", "publish_topic": "t1"})
    client.post("/api/devices", json={"uuid": "d2", "name": "Dev2", "publish_topic": "t2"})
    
    response = client.get("/api/devices")
    assert response.status_code == status.HTTP_200_OK
    devices = response.json()
    assert len(devices) >= 2

@pytest.mark.asyncio
async def test_start_stop_device(client):
    # Setup
    client.post("/api/devices", json={"uuid": "d1", "name": "Dev1", "publish_topic": "t1"})
    
    # Start
    response = client.post("/api/devices/d1/start")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "RUNNING"
    
    # Verify status in DB via GET
    response = client.get("/api/devices/d1")
    assert response.json()["status"] == "RUNNING"
    
    # Stop
    response = client.post("/api/devices/d1/stop")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "STOPPED"

@pytest.mark.asyncio
async def test_delete_device(client):
    client.post("/api/devices", json={"uuid": "d1", "name": "Dev1", "publish_topic": "t1"})
    
    response = client.delete("/api/devices/d1")
    assert response.status_code == status.HTTP_200_OK
    
    # Verify 404
    response = client.get("/api/devices/d1")
    assert response.status_code == status.HTTP_404_NOT_FOUND
