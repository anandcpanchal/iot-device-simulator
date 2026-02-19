from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models import Device, DeviceParams
from app.database import get_db
from app.engine import engine
import aiosqlite
import uuid
import logging
from fastapi import UploadFile, File
import shutil
import os

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/devices", response_model=List[Device])
async def list_devices(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM devices")
    devices = []
    rows = await cursor.fetchall()
    for row in rows:
        device_data = dict(row)
        # Fetch params for each device
        params_cursor = await db.execute("SELECT * FROM device_params WHERE device_uuid = ?", (device_data['uuid'],))
        params_rows = await params_cursor.fetchall()
        device_data['params'] = [dict(p) for p in params_rows]
        # Fetch messages from engine
        device_data['messages'] = engine.received_messages.get(device_data['uuid'], [])
        devices.append(Device(**device_data))
    return devices

@router.post("/devices", response_model=Device)
async def create_device(device: Device, db: aiosqlite.Connection = Depends(get_db)):
    # Create or provided UUID
    if not device.uuid:
        device.uuid = str(uuid.uuid4())
    
    logger.info(f"Creating device: {device}")
    
    try:
        await db.execute("""
            INSERT INTO devices (uuid, name, status, mode, publish_topic, subscribe_topic, interval_ms, qos, retain, csv_file_path, csv_loop)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            device.uuid, device.name, device.status, device.mode,
            device.publish_topic, device.subscribe_topic, device.interval_ms,
            device.qos, int(device.retain), device.csv_file_path, int(device.csv_loop)
        ))
        
        for param in device.params:
            if not param.device_uuid:
                param.device_uuid = device.uuid
            await db.execute("""
                INSERT INTO device_params (device_uuid, param_name, type, min_val, max_val, precision, string_value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (device.uuid, param.param_name, param.type, param.min_val, param.max_val, param.precision, param.string_value))
        
        await db.commit()
    except aiosqlite.IntegrityError as e:
        logger.error(f"Integrity Error: {e}")
        raise HTTPException(status_code=400, detail="Device with this UUID already exists")
    except Exception as e:
        logger.error(f"Create Device Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return device

@router.get("/devices/{device_uuid}", response_model=Device)
async def get_device(device_uuid: str, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM devices WHERE uuid = ?", (device_uuid,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device_data = dict(row)
    params_cursor = await db.execute("SELECT * FROM device_params WHERE device_uuid = ?", (device_uuid,))
    params_rows = await params_cursor.fetchall()
    device_data['params'] = [dict(p) for p in params_rows]
    # Fetch messages from engine
    device_data['messages'] = engine.received_messages.get(device_uuid, [])
    
    return Device(**device_data)

@router.put("/devices/{device_uuid}", response_model=Device)
async def update_device(device_uuid: str, device: Device, db: aiosqlite.Connection = Depends(get_db)):
    # Verify device exists
    cursor = await db.execute("SELECT * FROM devices WHERE uuid = ?", (device_uuid,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Device not found")
    
    try:
        await db.execute("""
            UPDATE devices SET 
                name = ?, 
                mode = ?, 
                publish_topic = ?, 
                subscribe_topic = ?, 
                interval_ms = ?, 
                qos = ?, 
                retain = ?, 
                csv_file_path = ?, 
                csv_loop = ?
            WHERE uuid = ?
        """, (
            device.name, device.mode,
            device.publish_topic, device.subscribe_topic, device.interval_ms,
            device.qos, int(device.retain), device.csv_file_path, int(device.csv_loop),
            device_uuid
        ))
        
        # Update params: delete and re-insert
        await db.execute("DELETE FROM device_params WHERE device_uuid = ?", (device_uuid,))
        for param in device.params:
            if not param.device_uuid:
                param.device_uuid = device_uuid
            await db.execute("""
                INSERT INTO device_params (device_uuid, param_name, type, min_val, max_val, precision, string_value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (device_uuid, param.param_name, param.type, param.min_val, param.max_val, param.precision, param.string_value))
        
        await db.commit()
    except Exception as e:
        logger.error(f"Update Device Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    return device

@router.delete("/devices/{device_uuid}")
async def delete_device(device_uuid: str, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("DELETE FROM devices WHERE uuid = ?", (device_uuid,))
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"message": "Device deleted"}

@router.post("/devices/{device_uuid}/upload-csv")
async def upload_csv(device_uuid: str, file: UploadFile = File(...), db: aiosqlite.Connection = Depends(get_db)):
    # Verify device exists
    cursor = await db.execute("SELECT * FROM devices WHERE uuid = ?", (device_uuid,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Save file
    file_path = f"data/csv/{device_uuid}_{file.filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update device config
    await db.execute("UPDATE devices SET mode='CSV_PLAYBACK', csv_file_path=? WHERE uuid=?", (file_path, device_uuid))
    await db.commit()
    
    return {"message": "CSV uploaded and device updated", "file_path": file_path}

@router.post("/devices/{device_uuid}/start")
async def start_device(device_uuid: str, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("UPDATE devices SET status='RUNNING' WHERE uuid=?", (device_uuid,))
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"status": "RUNNING"}

@router.post("/devices/{device_uuid}/stop")
async def stop_device(device_uuid: str, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("UPDATE devices SET status='STOPPED' WHERE uuid=?", (device_uuid,))
    await db.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"status": "STOPPED"}

@router.post("/devices/start-all")
async def start_all_devices(db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("UPDATE devices SET status='RUNNING'")
    await db.commit()
    return {"message": "All devices started"}

@router.post("/devices/stop-all")
async def stop_all_devices(db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("UPDATE devices SET status='STOPPED'")
    await db.commit()
    return {"message": "All devices stopped"}

