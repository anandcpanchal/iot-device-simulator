from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal

class DeviceParams(BaseModel):
    id: Optional[int] = None
    device_uuid: Optional[str] = None
    param_name: str
    type: Literal['int', 'float', 'bool', 'timestamp', 'string']
    min_val: float
    max_val: float
    precision: Optional[int] = 2
    string_value: Optional[str] = None

class Device(BaseModel):
    uuid: str
    name: str
    status: Literal['RUNNING', 'STOPPED'] = 'STOPPED'
    mode: Literal['RANDOM', 'CSV_PLAYBACK'] = 'RANDOM'
    publish_topic: str
    subscribe_topic: Optional[str] = None
    interval_ms: int = 1000
    qos: Literal[0, 1, 2] = 0
    retain: bool = False
    csv_file_path: Optional[str] = None
    csv_loop: bool = True
    params: List[DeviceParams] = []
    messages: List[dict] = [] # Received MQTT messages
