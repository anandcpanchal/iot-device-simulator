import asyncio
import time
from datetime import datetime, timezone
import json
import random
import logging
import csv
import os
import paho.mqtt.client as mqtt
from app.database import get_db, DB_PATH
import aiosqlite
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "backend_service")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "secure_password")

class CsvPlayer:
    def __init__(self, file_path, loop=True):
        self.file_path = file_path
        self.loop = loop
        self.file = open(file_path, 'r')
        self.reader = csv.DictReader(self.file)
        self.headers = self.reader.fieldnames
    
    def next_row(self):
        try:
            row = next(self.reader)
            return row
        except StopIteration:
            if self.loop:
                self.file.seek(0)
                # Skip header
                next(self.file) 
                # Re-create reader or just continue? CSV reader wrapper might need reset
                # Simplest: Close and reopen or seek 0 and consume header
                self.file.seek(0)
                self.reader = csv.DictReader(self.file)
                try:
                    return next(self.reader)
                except StopIteration:
                    return None # Empty file
            else:
                return None

    def close(self):
        if self.file:
            self.file.close()

class SimulationEngine:
    def __init__(self):
        self.running = False
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_message = self.on_message
        
        # Caches
        self.active_devices: Dict[str, Dict] = {} # UUID -> Device Dict
        self.device_params: Dict[str, List[Dict]] = {} # UUID -> List of Params
        self.csv_players: Dict[str, CsvPlayer] = {} # UUID -> CsvPlayer instance
        self.last_publish_times: Dict[str, float] = {} # UUID -> timestamp
        
        # Listening
        self.topic_map: Dict[str, List[str]] = {} # Topic -> List of UUIDs
        self.received_messages: Dict[str, List[Dict]] = {} # UUID -> List of messages

    def start_mqtt(self):
        try:
            if MQTT_USERNAME and MQTT_PASSWORD:
                self.mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT Broker at {MQTT_HOST}:{MQTT_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            timestamp = int(time.time())
            
            uuids = self.topic_map.get(topic, [])
            for uuid in uuids:
                if uuid not in self.received_messages:
                    self.received_messages[uuid] = []
                
                self.received_messages[uuid].append({
                    "timestamp": timestamp,
                    "topic": topic,
                    "payload": payload
                })
                
                # Keep last 5 messages
                if len(self.received_messages[uuid]) > 5:
                    self.received_messages[uuid].pop(0)
                    
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def start(self):
        self.running = True
        self.start_mqtt()
        asyncio.create_task(self._tick_loop())
        asyncio.create_task(self._sync_devices_loop())
        logger.info("Simulation Engine Started")

    async def stop(self):
        self.running = False
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        # Close all CSV handles
        for player in self.csv_players.values():
            player.close()
        logger.info("Simulation Engine Stopped")

    async def _sync_devices_loop(self):
        """Periodically sync active devices from DB to Memory"""
        while self.running:
            try:
                async with aiosqlite.connect(DB_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    cursor = await db.execute("SELECT * FROM devices WHERE status='RUNNING'")
                    rows = await cursor.fetchall()
                    
                    current_active_uuids = set()
                    new_topic_map = {}
                    
                    for row in rows:
                        device = dict(row)
                        uuid = device['uuid']
                        current_active_uuids.add(uuid)
                        
                        # Update cache if changed or new
                        self.active_devices[uuid] = device
                        
                        # Handle Subscriptions & Topic Map
                        sub_topic = device.get('subscribe_topic')
                        if sub_topic:
                            if sub_topic not in new_topic_map:
                                new_topic_map[sub_topic] = []
                            new_topic_map[sub_topic].append(uuid)
                            # Subscribe (idempotent in paho)
                            self.mqtt_client.subscribe(sub_topic)
                        
                        # Load Params if Random mode and not cached
                        if device['mode'] == 'RANDOM' and uuid not in self.device_params:
                            p_cursor = await db.execute("SELECT * FROM device_params WHERE device_uuid = ?", (uuid,))
                            p_rows = await p_cursor.fetchall()
                            self.device_params[uuid] = [dict(p) for p in p_rows]
                        
                        # Load CSV Player if CSV mode and not cached
                        if device['mode'] == 'CSV_PLAYBACK' and uuid not in self.csv_players:
                            if device['csv_file_path'] and os.path.exists(device['csv_file_path']):
                                self.csv_players[uuid] = CsvPlayer(device['csv_file_path'], loop=bool(device['csv_loop']))

                    # Replace topic map
                    self.topic_map = new_topic_map

                    # Cleanup stopped devices
                    cached_uuids = list(self.active_devices.keys())
                    for uuid in cached_uuids:
                        if uuid not in current_active_uuids:
                            del self.active_devices[uuid]
                            self.device_params.pop(uuid, None)
                            self.received_messages.pop(uuid, None) # Clear messages for stopped devices? Or keep? Let's clear for now to save memory
                            if uuid in self.csv_players:
                                self.csv_players[uuid].close()
                                del self.csv_players[uuid]

            except Exception as e:
                logger.error(f"Error syncing devices: {e}")
            
            await asyncio.sleep(5) # Sync every 5 seconds

    async def _tick_loop(self):
        """Main Simulation Loop"""
        while self.running:
            start_time = time.time()
            current_time_ms = int(start_time * 1000)
            
            # Iterate over a copy to allow modification during iteration if needed (though sync loop handles that)
            # Use list(self.active_devices.values()) is safer
            devices = list(self.active_devices.values())
            
            for device in devices:
                uuid = device['uuid']
                interval = device['interval_ms']
                last_pub = self.last_publish_times.get(uuid, 0)
                
                if current_time_ms - last_pub >= interval:
                    # Time to publish
                    await self.publish_device(device)
                    self.last_publish_times[uuid] = current_time_ms
            
            # Sleep mechanism to maintain loop but yield release
            elapsed = time.time() - start_time
            # Adaptive sleep: minimal 10ms, but try to hit 100ms cycle
            sleep_time = max(0.01, 0.1 - elapsed)
            await asyncio.sleep(sleep_time)

    async def publish_device(self, device):
        uuid = device['uuid']
        now = datetime.now(timezone.utc)
        iso_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        payload = {
            "uuid": uuid,
            "timestamp": iso_now,
            "data": {}
        }
        
        try:
            if device['mode'] == 'RANDOM':
                params = self.device_params.get(uuid, [])
                for p in params:
                    val = None
                    if p['type'] == 'int':
                        val = random.randint(int(p['min_val']), int(p['max_val']))
                    elif p['type'] == 'float':
                        val = round(random.uniform(p['min_val'], p['max_val']), p['precision'])
                    elif p['type'] == 'bool':
                        val = random.choice([True, False])
                    elif p['type'] == 'timestamp':
                        val = iso_now
                    elif p['type'] == 'string':
                        val = p.get('string_value', "")
                    
                    if val is not None:
                        payload['data'][p['param_name']] = val
                         
            elif device['mode'] == 'CSV_PLAYBACK':
                player = self.csv_players.get(uuid)
                if player:
                    row = player.next_row()
                    if row:
                        payload['data'] = row
                    else:
                        payload['data'] = {"status": "end_of_file"}
                else:
                    payload['data'] = {"error": "csv_reader_not_ready"}
                
            topic = device['publish_topic']
            # Blocking publish is okay here if fast, but paho loop_start handles it in background thread usually.
            # actually publish() is async-compatible in paho (queues it)
            self.mqtt_client.publish(topic, json.dumps(payload), qos=device['qos'], retain=bool(device['retain']))
        except Exception as e:
            logger.error(f"Error publishing for {uuid}: {e}")

engine = SimulationEngine()
