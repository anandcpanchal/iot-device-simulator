import pytest
from app.models import Device, DeviceParams

def test_device_params_validation():
    # Valid params
    params = DeviceParams(
        param_name="temperature",
        type="float",
        min_val=20.0,
        max_val=30.0,
        precision=1
    )
    assert params.param_name == "temperature"
    assert params.type == "float"

    # Invalid type
    with pytest.raises(ValueError):
        DeviceParams(
            param_name="fail",
            type="invalid_type",
            min_val=0,
            max_val=1
        )

def test_device_validation():
    # Valid device
    device = Device(
        uuid="test-uuid",
        name="Test Device",
        publish_topic="test/topic",
        interval_ms=500,
        qos=1,
        params=[
            DeviceParams(param_name="p1", type="int", min_val=0, max_val=10)
        ]
    )
    assert device.uuid == "test-uuid"
    assert len(device.params) == 1
    assert device.status == "STOPPED" # Default

    # Invalid QOS
    with pytest.raises(ValueError):
        Device(
            uuid="test",
            name="test",
            publish_topic="t",
            qos=3
        )
