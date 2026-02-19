const API_URL = '/api';

// State
let devices = [];
let paramsList = []; // Temporary params for new device
let isEditing = false;
let editUuid = null;

// DOM Elements
const deviceGrid = document.getElementById('deviceGrid');
const statsTotal = document.getElementById('statsTotal');
const statsRunning = document.getElementById('statsRunning');
const addDeviceModal = document.getElementById('addDeviceModal');
const deviceForm = document.getElementById('deviceForm');
const paramsContainer = document.getElementById('paramsContainer');
const modalTitle = document.getElementById('modalTitle');
const submitBtn = document.getElementById('submitBtn');

// Init
document.addEventListener('DOMContentLoaded', () => {
    fetchDevices();
    setInterval(fetchDevices, 2000); // Poll for status updates
});

async function fetchDevices() {
    try {
        const res = await fetch(`${API_URL}/devices`);
        devices = await res.json();
        renderDevices();
        updateStats();
    } catch (e) {
        console.error("Failed to fetch devices", e);
    }
}

function updateStats() {
    statsTotal.textContent = devices.length;
    statsRunning.textContent = devices.filter(d => d.status === 'RUNNING').length;
}

function renderDevices() {
    deviceGrid.innerHTML = devices.map(device => `
        <div class="device-card">
            <div class="device-header">
                <div>
                    <div class="device-name">${device.name}</div>
                    <div class="device-uuid">${device.uuid}</div>
                </div>
                <span class="status-badge ${device.status === 'RUNNING' ? 'status-running' : 'status-stopped'}">
                    ${device.status}
                </span>
            </div>
            <div class="device-details">
                <div>Topic: ${device.publish_topic}</div>
                <div>Interval: ${device.interval_ms}ms</div>
                <div>Mode: ${device.mode}</div>
            </div>
            <div class="device-actions">
                ${device.status === 'STOPPED'
            ? `<button class="primary" onclick="controlDevice('${device.uuid}', 'start')">Start</button>`
            : `<button onclick="controlDevice('${device.uuid}', 'stop')">Stop</button>`
        }
                <button onclick="openEditModal('${device.uuid}')">Edit</button>
                <button onclick="deleteDevice('${device.uuid}')" class="danger">Delete</button>
                <button onclick="uploadCsvPrompt('${device.uuid}')">CSV</button>
            </div>
            ${device.messages && device.messages.length > 0 ? `
            <div class="device-messages">
                <div class="messages-label">Received Messages:</div>
                ${device.messages.map(m => `
                    <div class="message-item">
                        <span class="message-time">${new Date(m.timestamp * 1000).toLocaleTimeString()}</span>
                        <span class="message-payload">${m.payload}</span>
                    </div>
                `).join('')}
            </div>
            ` : ''}
        </div>
    `).join('');
}

async function controlDevice(uuid, action) {
    await fetch(`${API_URL}/devices/${uuid}/${action}`, { method: 'POST' });
    fetchDevices();
}

async function deleteDevice(uuid) {
    if (!confirm('Are you sure?')) return;
    await fetch(`${API_URL}/devices/${uuid}`, { method: 'DELETE' });
    fetchDevices();
}

async function uploadCsvPrompt(uuid) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        await fetch(`${API_URL}/devices/${uuid}/upload-csv`, {
            method: 'POST',
            body: formData
        });
        alert('CSV Uploaded');
        fetchDevices();
    };
    input.click();
}

// Modal Logic
function openAddModal() {
    isEditing = false;
    editUuid = null;
    modalTitle.textContent = "Add New Device";
    submitBtn.textContent = "Create Device";

    addDeviceModal.classList.add('active');
    document.getElementById('deviceUuidInput').value = crypto.randomUUID();
    paramsList = [];
    renderParams();
}

async function openEditModal(uuid) {
    isEditing = true;
    editUuid = uuid;
    modalTitle.textContent = "Edit Device";
    submitBtn.textContent = "Update Device";

    const res = await fetch(`${API_URL}/devices/${uuid}`);
    const device = await res.json();

    document.getElementById('deviceUuidInput').value = device.uuid;
    deviceForm.name.value = device.name;
    deviceForm.publish_topic.value = device.publish_topic;
    deviceForm.subscribe_topic.value = device.subscribe_topic || '';
    deviceForm.interval_ms.value = device.interval_ms;

    paramsList = device.params || [];
    renderParams();
    addDeviceModal.classList.add('active');
}

function closeAddModal() {
    addDeviceModal.classList.remove('active');
    deviceForm.reset();
}

function addParam() {
    const name = prompt("Parameter Name (e.g. temperature)");
    if (!name) return;
    const type = prompt("Type (int, float, bool, timestamp, string)", "float");
    const min = parseFloat(prompt("Min Value (ignored for string/timestamp)", "0"));
    const max = parseFloat(prompt("Max Value (ignored for string/timestamp)", "100"));
    const strVal = type === 'string' ? prompt("String Value", "") : null;

    paramsList.push({
        param_name: name,
        type: type,
        min_val: min,
        max_val: max,
        precision: 2,
        string_value: strVal
    });
    renderParams();
}

function removeParam(index) {
    paramsList.splice(index, 1);
    renderParams();
}

function editParam(index) {
    const p = paramsList[index];
    const name = prompt("Parameter Name", p.param_name);
    if (!name) return;
    const type = prompt("Type (int, float, bool, timestamp, string)", p.type);
    const min = parseFloat(prompt("Min Value", p.min_val));
    const max = parseFloat(prompt("Max Value", p.max_val));
    const strVal = type === 'string' ? prompt("String Value", p.string_value || "") : null;

    paramsList[index] = {
        ...p,
        param_name: name,
        type: type,
        min_val: min,
        max_val: max,
        string_value: strVal
    };
    renderParams();
}

function renderParams() {
    paramsContainer.innerHTML = paramsList.map((p, index) => {
        let rangeText = "";
        if (p.type === 'string') rangeText = `Value: "${p.string_value}"`;
        else if (p.type === 'timestamp') rangeText = "Auto-populated timestamp";
        else rangeText = `Range: ${p.min_val} - ${p.max_val}`;

        return `
        <div style="font-size: 0.8rem; background: #f1f5f9; padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>${p.param_name}</strong> (${p.type})<br>
                <span style="color: #64748b; font-size: 0.75rem;">${rangeText}</span>
            </div>
            <div style="display: flex; gap: 0.25rem;">
                <button type="button" class="small-btn" onclick="editParam(${index})" style="padding: 2px 6px; font-size: 0.7rem;">Edit</button>
                <button type="button" class="small-btn danger" onclick="removeParam(${index})" style="padding: 2px 6px; font-size: 0.7rem;">Del</button>
            </div>
        </div>
        `;
    }).join('');
}

deviceForm.onsubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(deviceForm);

    const deviceUuid = formData.get('uuid');

    const device = {
        uuid: deviceUuid,
        name: formData.get('name'),
        publish_topic: formData.get('publish_topic'),
        subscribe_topic: formData.get('subscribe_topic'),
        interval_ms: parseInt(formData.get('interval_ms')),
        params: paramsList.map(p => ({ ...p, device_uuid: deviceUuid })),
        mode: 'RANDOM',
        status: isEditing ? (devices.find(d => d.uuid === deviceUuid)?.status || 'STOPPED') : 'STOPPED',
        qos: 0,
        retain: false,
        csv_loop: true
    };

    try {
        const url = isEditing ? `${API_URL}/devices/${deviceUuid}` : `${API_URL}/devices`;
        const method = isEditing ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(device)
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to process device');
        }

        closeAddModal();
        fetchDevices();
    } catch (err) {
        console.error(err);
        alert(`Error: ${err.message}`);
    }
};

async function startAll() {
    await fetch(`${API_URL}/devices/start-all`, { method: 'POST' });
    fetchDevices();
}

async function stopAll() {
    await fetch(`${API_URL}/devices/stop-all`, { method: 'POST' });
    fetchDevices();
}
