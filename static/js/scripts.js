// 電池相關
// ==================== 全域變數 ====================
let droneMarker = null;
let map = null;
let chargingChart = null;
let chargingInterval = null;
let chargingStartTime = null;
let lastBatteryPercent = 0;

// DOM 元素
const elements = {
    // 速度相關
    speedValue: document.getElementById('speed-value'),
    currentSpeed: document.getElementById('current-speed'),
    speedProgress: document.getElementById('speed-progress'),
    speedNeedle: document.getElementById('speed-needle'),
    
    // 高度相關
    altitudeBar: document.getElementById('altitude-bar'),
    altitudeValue: document.getElementById('altitude-value'),
    altitudeIndicator: document.getElementById('altitude-indicator'),
    batteryCircle: document.getElementById('battery-circle'),
    batteryPercentage: document.getElementById('battery-percentage'),
    batteryVoltage: document.getElementById('battery-voltage'),
    batteryCurrent: document.getElementById('battery-current'),

    // 狀態相關
    flightMode: document.getElementById('flight-mode'),
    armingStatus: document.getElementById('arming-status'),
    rtkStatus: document.getElementById('rtk-status'),
    pitchAngle: document.getElementById('pitch-angle'),
    yawAngle: document.getElementById('yaw-angle'),
    rollAngle: document.getElementById('roll-angle'),

    // 充電相關
    startChargingBtn: document.getElementById('start-charging-btn'),
    stopChargingBtn: document.getElementById('stop-charging-btn'),
    chargingStatus: document.getElementById('charging-status'),
    chargingTime: document.getElementById('charging-time'),
    chargingRate: document.getElementById('charging-rate'),
    estimatedTime: document.getElementById('estimated-time'),

    // 其他
    currentTime: document.getElementById('current-time'),
    connectionStatus: document.getElementById('connection-status'),
    centerMapBtn: document.getElementById('center-map')
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
initializeMap();
initializeChart();
startDataUpdates();
setupEventListeners();
updateCurrentTime();

// 每秒更新時間
setInterval(updateCurrentTime, 1000);
});

// ==================== 時間更新 ====================
function updateCurrentTime() {
const now = new Date();
const timeString = now.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
});
if (elements.currentTime) {
    elements.currentTime.textContent = timeString;
}
}

// ==================== 地圖初始化 ====================
function initializeMap() {
try {
    map = L.map('map', {
        center: [25.0330, 121.5654],
        zoom: 15,
        zoomControl: true,
        attributionControl: false
    });

    // 添加地圖圖層
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // 創建無人機圖標
    const droneIcon = L.divIcon({
        className: 'drone-marker',
        html: '<i class="bi bi-geo-alt-fill text-primary fs-2"></i>',
        iconSize: [30, 30],
        iconAnchor: [15, 30]
    });

    // 添加無人機標記
    droneMarker = L.marker([25.0330, 121.5654], {
        icon: droneIcon,
        title: '無人機位置'
    }).addTo(map);

    // 添加點擊事件監聽
    map.on('click', function(e) {
        console.log('地圖點擊位置:', e.latlng);
    });

    // 調整地圖大小
    setTimeout(() => {
        map.invalidateSize();
    }, 250);

} catch (error) {
    console.error('地圖初始化失敗:', error);
    showNotification('地圖載入失敗', 'error');
}
}

// ==================== 圖表初始化 ====================
function initializeChart() {
const ctx = document.getElementById('charging-chart');
if (!ctx) return;

chargingChart = new Chart(ctx.getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: '電池電量 (%)',
            data: [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderWidth: 3,
            pointBackgroundColor: '#10b981',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 7,
            fill: true,
            tension: 0.4,
            cubicInterpolationMode: 'monotone'
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: {
                    color: '#374151',
                    font: { size: 14, weight: '500' },
                    usePointStyle: true,
                    padding: 20
                }
            },
            tooltip: {
                backgroundColor: 'rgba(31, 41, 55, 0.9)',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                borderColor: '#10b981',
                borderWidth: 1,
                cornerRadius: 8,
                displayColors: false,
                callbacks: {
                    title: function(context) {
                        return '時間: ' + context[0].label;
                    },
                    label: function(context) {
                        return '電量: ' + context.parsed.y + '%';
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    color: '#6b7280',
                    font: { size: 12 },
                    callback: function(value) {
                        return value + '%';
                    }
                },
                grid: {
                    color: 'rgba(107, 114, 128, 0.1)',
                    lineWidth: 1
                },
                title: {
                    display: true,
                    text: '電池電量 (%)',
                    color: '#374151',
                    font: { size: 14, weight: '500' }
                }
            },
            x: {
                ticks: {
                    color: '#6b7280',
                    font: { size: 12 },
                    maxTicksLimit: 10
                },
                grid: {
                    color: 'rgba(107, 114, 128, 0.1)',
                    lineWidth: 1
                },
                title: {
                    display: true,
                    text: '充電時間',
                    color: '#374151',
                    font: { size: 14, weight: '500' }
                }
            }
        },
        elements: {
            point: {
                hoverBorderWidth: 3
            },
            line: {
                borderJoinStyle: 'round'
            }
        }
    }
});
}

// ==================== 事件監聽器設置 ====================
function setupEventListeners() {
// 充電控制按鈕
if (elements.startChargingBtn) {
    elements.startChargingBtn.addEventListener('click', startChargingRecord);
}

if (elements.stopChargingBtn) {
    elements.stopChargingBtn.addEventListener('click', stopChargingRecord);
}

// 地圖居中按鈕
if (elements.centerMapBtn) {
    elements.centerMapBtn.addEventListener('click', centerMapOnDrone);
}

// 窗口大小調整
window.addEventListener('resize', debounce(function() {
    if (map) {
        setTimeout(() => map.invalidateSize(), 250);
    }
}, 250));
}

// ==================== 數據更新函數 ====================
async function fetchSpeed() {
try {
    const response = await fetch('/get_speed');
    const data = await response.json();
    const speed = Math.max(0, data.speed || 0);

    updateSpeedDisplay(speed);
    updateConnectionStatus(true);
} catch (error) {
    console.error('獲取速度數據失敗:', error);
    updateSpeedDisplay(0);
    updateConnectionStatus(false);
}
}

// ------------------------------------------------------
// 用於更新速度、進度半圓與指針位置的函式
// ------------------------------------------------------
async function fetchSpeed() {
    try {
        const response = await fetch('/get_speed');
        const data = await response.json();
        const speed = data.speed; // 假設 speed 的範圍是 0 ～ 100

        // 1. 更新顯示數值
        const speedValueEl = document.getElementById('percentage');
        const currentSpeedEl = document.getElementById('current-speed');
        const displayValue = Math.min(Math.max(speed, 0), 100).toFixed(0);
        if (speedValueEl) speedValueEl.textContent = displayValue;
        if (currentSpeedEl) currentSpeedEl.textContent = `${displayValue}%`;

        // 2. 更新半圓進度（綠色弧線）
        const speedProgress = document.getElementById('speed-progress');
        if (speedProgress) {
            // 半圓的近似長度 ≈ 502
            const totalLength = 502;
            const pct = Math.min(Math.max(speed / 100, 0), 1);
            const offset = totalLength - totalLength * pct;
            speedProgress.style.strokeDasharray = totalLength;
            speedProgress.style.strokeDashoffset = offset;
        }

        // 3. 更新指針旋轉：從右側(0°)→左側(180°)
        const needle = document.getElementById('speed-needle');
        if (needle) {
            const pct = Math.min(Math.max(speed / 100, 0), 1);
            const angle = 180 * pct; 
            // 0% → 0°（右側）；100% → 180°（左側）
            needle.style.transform = `rotate(${angle}deg)`;
        }

    } catch (error) {
        console.error('Error fetching speed:', error);
    }
}

// 如果您原本是 setInterval 呼叫 fetchSpeed，就保持不變，例如：
setInterval(fetchSpeed, 500);



// ------------------------------------------------------
// 範例：如果您原本有 setInterval 或 requestAnimationFrame 持續取速度，就把它改成呼叫這個 fetchSpeed()
// 例如：
setInterval(fetchSpeed, 500); // 每 0.5 秒更新一次


async function fetchAltitude() {
try {
    const response = await fetch('/get_altitude');
    const data = await response.json();
    const altitude = Math.max(0, data.altitude || 0);

    updateAltitudeDisplay(altitude);
} catch (error) {
    console.error('獲取高度數據失敗:', error);
    updateAltitudeDisplay(0);
}
}

function updateAltitudeDisplay(altitude) {
if (!elements.altitudeValue || !elements.altitudeBar) return;

elements.altitudeValue.textContent = altitude.toFixed(0);

// 更新高度條 (假設最大高度 90m)
const maxAltitude = 90;
const percentage = Math.min((altitude / maxAltitude) * 100, 100);

elements.altitudeBar.style.height = `${percentage}%`;

// 根據高度改變顏色
let color;
if (altitude <= 30) {
    color = '#10b981'; // 綠色
} else if (altitude <= 60) {
    color = '#f59e0b'; // 橙色
} else {
    color = '#ef4444'; // 紅色
}

elements.altitudeBar.style.background = `linear-gradient(to top, ${color}, ${color}bb)`;

// 更新指示器位置
if (elements.altitudeIndicator) {
    elements.altitudeIndicator.style.bottom = `${percentage}%`;
}
}

async function fetchBatteryData() {
try {
    const response = await fetch('/get_battery');
    const data = await response.json();
    const voltage = data.volt || 0;
    const current = data.current || 0;
    const percentage = data.battery_percent || 0;

    updateBatteryDisplay(voltage, current, percentage);
} catch (error) {
    console.error('獲取電池數據失敗:', error);
    updateBatteryDisplay(0, 0, 0);
}
}

function updateBatteryDisplay(voltage, current, percentage) {
if (!elements.batteryPercentage) return;

elements.batteryPercentage.textContent = `${percentage.toFixed(0)}%`;

if (elements.batteryVoltage) {
    elements.batteryVoltage.textContent = `${voltage.toFixed(1)}V`;
}

if (elements.batteryCurrent) {
    elements.batteryCurrent.textContent = `${current.toFixed(1)}A`;
}

// 更新圓環進度
if (elements.batteryCircle) {
    const circumference = 2 * Math.PI * 45;
    const offset = circumference - (percentage / 100) * circumference;
    elements.batteryCircle.style.strokeDashoffset = offset;

    // 根據電量改變顏色
    let color;
    if (percentage > 60) {
        color = '#10b981'; // 綠色
    } else if (percentage > 30) {
        color = '#f59e0b'; // 橙色
    } else {
        color = '#ef4444'; // 紅色
    }
    elements.batteryCircle.style.stroke = color;
}

// 記錄最後的電池百分比用於充電計算
lastBatteryPercent = percentage;
}

async function fetchFlightStatus() {
try {
    const [modeResponse, armingResponse, rtkResponse] = await Promise.all([
        fetch('/get_flight_mode'),
        fetch('/get_arming_status'),
        fetch('/get_rtk_status')
    ]);

    const modeData = await modeResponse.json();
    const armingData = await armingResponse.json();
    const rtkData = await rtkResponse.json();

    updateFlightStatus(
        modeData.flight_mode || '未知',
        armingData.arm_status || '未知',
        rtkData.rtk_status || '未知'
    );
} catch (error) {
    console.error('獲取飛行狀態失敗:', error);
    updateFlightStatus('未知', '未知', '未知');
}
}

function updateFlightStatus(flightMode, armingStatus, rtkStatus) {
if (elements.flightMode) {
    elements.flightMode.textContent = flightMode;
    elements.flightMode.className = `badge status-badge ${flightMode.toLowerCase()}`;
}

if (elements.armingStatus) {
    elements.armingStatus.textContent = armingStatus;
    elements.armingStatus.className = `badge status-badge ${armingStatus.toLowerCase()}`;
}

if (elements.rtkStatus) {
    elements.rtkStatus.textContent = rtkStatus;
    elements.rtkStatus.className = `badge status-badge ${rtkStatus.toLowerCase()}`;
}
}

async function fetchDroneOrientation() {
try {
    const response = await fetch('/get_drone_orientation');
    const data = await response.json();
    
    updateOrientationDisplay(
        data.pitch || 0,
        data.yaw || 0,
        data.roll || 0
    );
} catch (error) {
    console.error('獲取姿態數據失敗:', error);
    updateOrientationDisplay(0, 0, 0);
}
}

function updateOrientationDisplay(pitch, yaw, roll) {
if (elements.pitchAngle) {
    elements.pitchAngle.textContent = `${pitch.toFixed(1)}°`;
}
if (elements.yawAngle) {
    elements.yawAngle.textContent = `${yaw.toFixed(1)}°`;
}
if (elements.rollAngle) {
    elements.rollAngle.textContent = `${roll.toFixed(1)}°`;
}
}

async function fetchDronePosition() {
try {
    const response = await fetch('/get_drone_position');
    const data = await response.json();
    
    updateDronePosition(data.lat || 25.0330, data.lon || 121.5654);
} catch (error) {
    console.error('獲取位置數據失敗:', error);
}
}

function updateDronePosition(lat, lon) {
if (droneMarker && map) {
    droneMarker.setLatLng([lat, lon]);
}
}

// ==================== 充電記錄功能 ====================
function startChargingRecord() {
if (chargingInterval) return;

chargingStartTime = new Date();
elements.startChargingBtn.disabled = true;
elements.stopChargingBtn.disabled = false;
elements.chargingStatus.textContent = '充電中';
elements.chargingStatus.className = 'fw-bold text-success';

// 清空圖表數據
chargingChart.data.labels = [];
chargingChart.data.datasets[0].data = [];
chargingChart.update();

chargingInterval = setInterval(updateChargingData, 2000);
showNotification('開始記錄充電數據', 'success');
}

function stopChargingRecord() {
if (!chargingInterval) return;

clearInterval(chargingInterval);
chargingInterval = null;

elements.startChargingBtn.disabled = false;
elements.stopChargingBtn.disabled = true;
elements.chargingStatus.textContent = '已停止';
elements.chargingStatus.className = 'fw-bold text-secondary';

if (elements.chargingTime) {
    elements.chargingTime.textContent = '00:00';
}
if (elements.chargingRate) {
    elements.chargingRate.textContent = '0%/min';
}
if (elements.estimatedTime) {
    elements.estimatedTime.textContent = '--:--';
}

showNotification('充電記錄已停止', 'info');
}

function updateChargingData() {
if (!chargingStartTime) return;

const now = new Date();
const elapsedMinutes = (now - chargingStartTime) / (1000 * 60);
const timeString = formatTime(Math.floor(elapsedMinutes));

// 添加數據點到圖表
chargingChart.data.labels.push(timeString);
chargingChart.data.datasets[0].data.push(lastBatteryPercent);

// 限制數據點數量
if (chargingChart.data.labels.length > 50) {
    chargingChart.data.labels.shift();
    chargingChart.data.datasets[0].data.shift();
}

chargingChart.update('none');

// 更新充電統計
if (elements.chargingTime) {
    elements.chargingTime.textContent = timeString;
}

// 計算充電速率
const dataPoints = chargingChart.data.datasets[0].data;
if (dataPoints.length >= 2) {
    const rate = (dataPoints[dataPoints.length - 1] - dataPoints[0]) / elapsedMinutes;
    if (elements.chargingRate) {
        elements.chargingRate.textContent = `${rate.toFixed(1)}%/min`;
    }

    // 估算完成時間
    if (rate > 0 && lastBatteryPercent < 100) {
        const remainingPercent = 100 - lastBatteryPercent;
        const estimatedMinutes = remainingPercent / rate;
        if (elements.estimatedTime) {
            elements.estimatedTime.textContent = formatTime(Math.ceil(estimatedMinutes));
        }
    }
}
}

// ==================== 輔助函數 ====================
function formatTime(minutes) {
const hrs = Math.floor(minutes / 60);
const mins = minutes % 60;
return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}

function centerMapOnDrone() {
if (droneMarker && map) {
    const position = droneMarker.getLatLng();
    map.setView(position, 15, { animate: true });
    showNotification('地圖已居中到無人機位置', 'info');
}
}

function updateConnectionStatus(connected) {
if (!elements.connectionStatus) return;

if (connected) {
    elements.connectionStatus.innerHTML = '<i class="bi bi-wifi me-1"></i>已連線';
    elements.connectionStatus.className = 'badge bg-success pulse';
} else {
    elements.connectionStatus.innerHTML = '<i class="bi bi-wifi-off me-1"></i>連線中斷';
    elements.connectionStatus.className = 'badge bg-danger';
}
}

function showNotification(message, type = 'info') {
// 創建通知元素
const notification = document.createElement('div');
notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
notification.style.cssText = 'top: 100px; right: 20px; z-index: 9999; min-width: 300px;';
notification.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
`;

document.body.appendChild(notification);

// 3秒後自動移除
setTimeout(() => {
    if (notification.parentNode) {
        notification.remove();
    }
}, 3000);
}

function debounce(func, wait) {
let timeout;
return function executedFunction(...args) {
    const later = () => {
        clearTimeout(timeout);
        func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
};
}

// ==================== 數據更新排程 ====================
function startDataUpdates() {
// 立即執行一次
fetchSpeed();
fetchAltitude();
fetchBatteryData();
fetchFlightStatus();
fetchDroneOrientation();
fetchDronePosition();

// 設置定期更新
setInterval(fetchSpeed, 500);           // 速度更新頻率較高
setInterval(fetchAltitude, 100);       // 高度每秒更新
setInterval(fetchBatteryData, 200);    // 電池每2秒更新
setInterval(fetchFlightStatus, 300);   // 狀態每3秒更新
setInterval(fetchDroneOrientation, 100); // 姿態每秒更新
setInterval(fetchDronePosition, 200);  // 位置每2秒更新
}

// ==================== 錯誤處理 ====================
window.onerror = function(msg, url, line, col, error) {
console.error('全域錯誤:', {
    message: msg,
    source: url,
    line: line,
    column: col,
    error: error
});
showNotification('系統發生錯誤，請重新整理頁面', 'error');
};

// ==================== 頁面卸載清理 ====================
window.addEventListener('beforeunload', function() {
if (chargingInterval) {
    clearInterval(chargingInterval);
}
});