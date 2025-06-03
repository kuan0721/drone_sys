// 速度指針 & 顯示
const speedValueEl = document.getElementById('percentage');
const currentSpeedEl = document.getElementById('current-speed');
const speedProgress = document.getElementById('speed-progress');
const speedNeedle = document.getElementById('speed-needle');

// 高度
const heightBar = document.getElementById('height-bar');
const heightValue = document.getElementById('height-value');

// 電池
const batteryProgressCircle = document.getElementById("battery-progress-circle");
const batteryPercentEl = document.getElementById("battery-percent");
const batteryVoltEl = document.getElementById("battery-volt");
const batteryCurrentEl = document.getElementById("battery-current");

// 飛行模式
const flightModeDisplay = document.getElementById('flight-mode');
// Arming 狀態
const armingStatusDisplay = document.getElementById("arming-status");
// RTK 狀態
const rtkStatusDisplay = document.getElementById("rtk-status");

// 姿態
const pitchAngleEl = document.getElementById('pitch-angle');
const yawAngleEl = document.getElementById('yaw-angle');
const rollAngleEl = document.getElementById('roll-angle');

// 地圖初始化
const map = L.map('map').setView([25.0330, 121.5654], 15);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

const droneIcon = L.icon({
    iconUrl: "/static/images/drone.png",
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});
let droneMarker = L.marker([25.0330, 121.5654], { icon: droneIcon }).addTo(map);

window.addEventListener("resize", function () {
    setTimeout(() => {
        map.invalidateSize();
    }, 500);
});

// 速度
async function fetchSpeed() {
    try {
        const response = await fetch('/get_speed');
        const data = await response.json();
        const speed = data.speed ?? 0;

        speedValueEl.textContent = speed;
        currentSpeedEl.textContent = `${speed} m/s`;

        // 圓弧進度條
        const totalLength = 160;
        const percent = Math.min(speed / 20 * 100, 100); // 假設最大20 m/s，超過顯示100%
        const progress = percent / 100 * totalLength;
        speedProgress.setAttribute("d", `M20 100 A80 80 0 0 1 ${20 + progress} 100`);
        speedProgress.style.strokeDasharray = totalLength;
        speedProgress.style.strokeDashoffset = totalLength - progress;

        // 指針
        const angle = percent * 1.8; // 0-180 deg
        speedNeedle.style.transform = `rotate(${angle}deg)`;
        speedNeedle.style.transformOrigin = 'bottom';
    } catch (error) {
        speedValueEl.textContent = '0';
        currentSpeedEl.textContent = '0 m/s';
    }
}

// 高度
async function fetchHeight() {
    try {
        const response = await fetch('/get_altitude');
        const data = await response.json();
        const height = data.altitude ?? 0;

        // 條狀比例（最大90m為例）
        const heightPercent = Math.min(height / 90 * 100, 100);
        heightBar.style.height = `${heightPercent}%`;

        // 顏色
        if (height <= 30) {
            heightBar.style.background = 'green';
        } else if (height <= 60) {
            heightBar.style.background = 'orange';
        } else {
            heightBar.style.background = 'red';
        }

        heightValue.textContent = `${height} 公尺`;
    } catch (error) {
        heightValue.textContent = `0 公尺`;
    }
}

// 電池
async function fetchBatteryData() {
    try {
        const response = await fetch("/get_battery");
        const data = await response.json();
        const volt = data.volt ?? 0;
        const current = data.current ?? 0;
        const percent = data.battery_percent ?? 0;

        // 圓環
        const radius = 45;
        const circumference = 2 * Math.PI * radius;
        const dashOffset = circumference * (1 - percent / 100);

        batteryProgressCircle.style.strokeDasharray = circumference;
        batteryProgressCircle.style.strokeDashoffset = dashOffset;

        batteryPercentEl.textContent = `${percent}%`;
        batteryVoltEl.textContent = `Volt: ${volt}V`;
        batteryCurrentEl.textContent = `Current: ${current}A`;

        if (percent > 60) {
            batteryProgressCircle.style.stroke = "green";
        } else if (percent > 30) {
            batteryProgressCircle.style.stroke = "orange";
        } else {
            batteryProgressCircle.style.stroke = "red";
        }
    } catch (error) {
        batteryPercentEl.textContent = `0%`;
        batteryVoltEl.textContent = `Volt: 0V`;
        batteryCurrentEl.textContent = `Current: 0A`;
    }
}

// 飛行模式
async function fetchFlightMode() {
    try {
        const response = await fetch('/get_flight_mode');
        const data = await response.json();
        const mode = data.flight_mode ?? '未知';

        flightModeDisplay.textContent = mode;
        flightModeDisplay.className = 'flight-mode ' + mode.toLowerCase();
    } catch (error) {
        flightModeDisplay.textContent = '未知';
    }
}

// 解鎖狀態
async function fetchArmingStatus() {
    try {
        const response = await fetch("/get_arming_status");
        const data = await response.json();
        const status = data.arm_status ?? 'unknown';

        armingStatusDisplay.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        armingStatusDisplay.className = "arming-status " + status.toLowerCase();
    } catch (error) {
        armingStatusDisplay.textContent = '未知';
    }
}

// RTK 狀態
async function fetchRTKStatus() {
    try {
        const response = await fetch("/get_rtk_status");
        const data = await response.json();
        const status = data.rtk_status ?? 'unknown';

        rtkStatusDisplay.textContent = `${status}`;
        rtkStatusDisplay.className = "rtk-status " + status.toLowerCase();
    } catch (error) {
        rtkStatusDisplay.textContent = '未知';
    }
}

// 姿態角度
async function fetchDroneOrientation() {
    try {
        const response = await fetch('/get_drone_orientation');
        const data = await response.json();
        const pitch = data.pitch ?? 0;
        const yaw = data.yaw ?? 0;
        const roll = data.roll ?? 0;

        pitchAngleEl.textContent = `${pitch.toFixed(1)}°`;
        yawAngleEl.textContent = `${yaw.toFixed(1)}°`;
        rollAngleEl.textContent = `${roll.toFixed(1)}°`;

        // 若有3D模型旋轉，可加這裡
        // updateDroneRotation(yaw, pitch, roll);
    } catch (error) {
        pitchAngleEl.textContent = `0°`;
        yawAngleEl.textContent = `0°`;
        rollAngleEl.textContent = `0°`;
    }
}

// 地圖位置
async function updateDronePosition() {
    try {
        const response = await fetch('/get_drone_position');
        const data = await response.json();
        const lat = data.lat ?? 25.0330;
        const lon = data.lon ?? 121.5654;

        droneMarker.setLatLng([lat, lon]);
        map.setView([lat, lon]);
    } catch (error) {
        // 忽略不變
    }
}

// 充電歷程 Chart.js
const ctx = document.getElementById('chargingChart').getContext('2d');
const chargingChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: '電磁充電效率',
            data: [],
            borderColor: 'cyan',
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointBackgroundColor: 'black',
            pointRadius: 5
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                title: {
                    display: true,
                    text: '充電百分比 (%)'
                }
            },
            x: {
                title: {
                    display: true,
                    text: '時間 (分:秒)'
                }
            }
        },
        plugins: {
            legend: {
                labels: {
                    color: 'black'
                }
            }
        }
    }
});

// 充電資料
async function fetchChargingData() {
    try {
        const response = await fetch('/get_charge_data');
        const data = await response.json();
        // 若有時間戳與百分比資料再填充，否則略過
        // chargingChart.data.labels = data.timestamps ?? [];
        // chargingChart.data.datasets[0].data = data.percentages ?? [];
        // chargingChart.update();
    } catch (error) {
        // do nothing
    }
}

// 排程，每1秒定期刷新主要資料
setInterval(fetchSpeed, 10);
setInterval(fetchHeight, 10);
setInterval(fetchBatteryData, 10);
setInterval(fetchFlightMode, 10);
setInterval(fetchArmingStatus, 10);
setInterval(fetchRTKStatus, 1);
setInterval(fetchDroneOrientation, 10);
setInterval(updateDronePosition, 10);
// 充電歷程每5秒
setInterval(fetchChargingData, 5000);
