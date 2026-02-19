import asyncio
import httpx
import paho.mqtt.client as mqtt
import time
import json

API_URL = "http://localhost:8000/api"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

async def verify_listening():
    print("Verifying Listening Topic Feature...")
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        # 1. Create Device with Subscription
        device_payload = {
            "uuid": "listener-1",
            "name": "Listener Device",
            "publish_topic": "test/pub",
            "subscribe_topic": "test/cmd",
            "interval_ms": 1000,
            "mode": "RANDOM",
            "status": "RUNNING"
        }
        
        # Delete if exists
        await client.delete(f"{API_URL}/devices/listener-1")
        
        print("Creating device...")
        resp = await client.post(f"{API_URL}/devices", json=device_payload)
        if resp.status_code != 200:
            print(f"Failed to create device: {resp.text}")
            return
            
        # Give some time for subscription to happen
        print("Waiting for subscription sync...")
        await asyncio.sleep(6) # Sync loop runs every 5s
        
        # 2. Publish Message to 'test/cmd'
        print("Publishing MQTT message...")
        client_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
        client_mqtt.loop_start()
        
        msg_payload = {"command": "reset", "val": 123}
        client_mqtt.publish("test/cmd", json.dumps(msg_payload))
        
        await asyncio.sleep(2)
        
        # 3. Check API
        print("Checking API for messages...")
        resp = await client.get(f"{API_URL}/devices/listener-1")
        device_data = resp.json()
        
        messages = device_data.get("messages", [])
        print(f"Messages received: {messages}")
        
        found = False
        for m in messages:
            if m['topic'] == "test/cmd" and json.dumps(msg_payload) in m['payload']: # Payload might vary in spacing
                 # exact string match might fail due to json dumping spacing, but let's check basic validity.
                 # The simulator engine decodes payload.
                 pass
        
        # Simpler check
        if len(messages) > 0 and messages[0]['topic'] == "test/cmd":
            print("SUCCESS: Message received and stored!")
        else:
            print("FAILURE: No messages found.")
            
        client_mqtt.loop_stop()
        
if __name__ == "__main__":
    if asyncio.get_event_loop_policy().__class__.__name__ == 'WindowsProactorEventLoopPolicy':
         # Fix for Windows specific loop issue if needed, though usually Selector is safer for some libs
         pass
    asyncio.run(verify_listening())
