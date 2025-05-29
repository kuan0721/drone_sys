// 指針和速度數據
const needle = document.getElementById('needle');
const percentageDisplay = document.getElementById('percentage');

// 高度條和高度數據
const heightBar = document.getElementById('height-bar');
const heightValue = document.getElementById('height-value');


// 更新速度
async function fetchSpeed() {
    try {
        const response = await fetch('/get_speed');
        const data = await response.json();
        const speed = data.speed;

        // 更新速度值
        const speedValueEl = document.getElementById('percentage');
        const currentSpeedEl = document.getElementById('current-speed');
        speedValueEl.textContent = speed;
        currentSpeedEl.textContent = `${speed}%`;

        // 更新進度圖
        const speedProgress = document.getElementById('speed-progress');
        const totalLength = 502; // SVG圓弧的近似總長度
        const progress = (speed / 100) * totalLength;
        speedProgress.style.strokeDasharray = totalLength;
        speedProgress.style.strokeDashoffset = totalLength - progress;

        // 更新指針旋轉
        const needle = document.getElementById('speed-needle');
        const angle = (speed / 100) * 180;
        needle.style.transform = `rotate(${angle}deg)`;
        needle.style.transformOrigin = 'bottom';
    } catch (error) {
        console.error('Error fetching speed:', error);
    }
}

// 更新高度
async function fetchHeight() {
    try {
        const response = await fetch('/get_height');
        const data = await response.json();
        const height = data.height;

        // 計算高度條的高度百分比
        const heightPercent = (height / 90) * 100;
        heightBar.style.height = `${heightPercent}%`;

        // 設定高度條顏色
        if (height <= 30) {
            heightBar.style.background = 'green';
        } else if (height <= 60) {
            heightBar.style.background = 'orange';
        } else {
            heightBar.style.background = 'red';
        }

        // 更新高度值顯示
        heightValue.textContent = `${height}公尺`;
    } catch (error) {
        console.error('Error fetching height:', error);
    }
}



// 定期更新數據
setInterval(() => {
    fetchSpeed();
    fetchHeight();
}, 1);


// 定期取得並更新電池資訊
async function fetchBatteryData() {
    try {
      const response = await fetch("/get_battery");
      const data = await response.json();
      const volt = data.volt;
      const current = data.current;
      const percent = data.battery_percent;
  
      // 計算圓形周長 (半徑 r = 45)
      const radius = 45;
      const circumference = 2 * Math.PI * radius; // 約 282.74
      const dashOffset = circumference * (1 - percent / 100);
  
      // 更新 SVG 進度環
      const batteryProgressCircle = document.getElementById("battery-progress-circle");
      batteryProgressCircle.style.strokeDasharray = circumference;
      batteryProgressCircle.style.strokeDashoffset = dashOffset;
  
      // 更新電池數值顯示
      document.getElementById("battery-percent").textContent = `${percent}%`;
      document.getElementById("battery-volt").textContent = `Volt: ${volt}V`;
      document.getElementById("battery-current").textContent = `Current: ${current}A`;
  
      // 根據電池電量改變進度環顏色
      if (percent > 60) {
        batteryProgressCircle.style.stroke = "green";
      } else if (percent > 30) {
        batteryProgressCircle.style.stroke = "orange";
      } else {
        batteryProgressCircle.style.stroke = "red";
      }
    } catch (error) {
      console.error("Error fetching battery data:", error);
    }
  }
  
  // 每秒更新一次電池資料
  setInterval(fetchBatteryData, 1);
  


const flightModeDisplay = document.getElementById('flight-mode');

// 從 Flask 獲取飛行模式數據
async function fetchFlightMode() {
    try {
        const response = await fetch('/get_flight_mode');
        const data = await response.json();
        const mode = data.mode;

        // 更新飛行模式文字
        flightModeDisplay.textContent = mode;

        // 更新樣式對應顏色
        flightModeDisplay.className = 'flight-mode ' + mode.toLowerCase();
    } catch (error) {
        console.error('Error fetching flight mode:', error);
    }
}

// 每2秒更新一次飛行模式
setInterval(fetchFlightMode, 10);

const armingStatusDisplay = document.getElementById("arming-status");

// 從 Flask 獲取 Arming 狀態
async function fetchArmingStatus() {
    try {
        const response = await fetch("/get_arming_status");
        const data = await response.json();
        const status = data.status;

        // 根據狀態更新文字和樣式
        armingStatusDisplay.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        armingStatusDisplay.className = "arming-status " + status.toLowerCase();
    } catch (error) {
        console.error("Error fetching arming status:", error);
    }
}

// 每秒更新一次狀態
setInterval(fetchArmingStatus, 10);

const rtkStatusDisplay = document.getElementById("rtk-status");

// 從 Flask 獲取 RTK 狀態
async function fetchRTKStatus() {
    try {
        const response = await fetch("/get_rtk_status");
        const data = await response.json();
        const status = data.status;

        // 根據狀態更新文字和樣式
        rtkStatusDisplay.textContent = `RTK: ${status.charAt(0).toUpperCase() + status.slice(1)}`;
        rtkStatusDisplay.className = "rtk-status " + status.toLowerCase();
    } catch (error) {
        console.error("Error fetching RTK status:", error);
    }
}

// 每秒更新一次狀態
setInterval(fetchRTKStatus, 10);

// 初始化地圖
const map = L.map('map').setView([25.0330, 121.5654], 15);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// 添加無人機標記
const droneIcon = L.icon({
    iconUrl: "/static/images/drone.png", // 直接使用絕對路徑
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});


let droneMarker = L.marker([25.0330, 121.5654], { icon: droneIcon }).addTo(map);

// 更新無人機位置
async function updateDronePosition() {
    try {
        const response = await fetch('/get_drone_position');
        const data = await response.json();
        const { lat, lon } = data;

        // 更新無人機標記位置
        droneMarker.setLatLng([lat, lon]);
        map.setView([lat, lon]); // 讓地圖跟隨無人機移動
    } catch (error) {
        console.error('Error fetching drone position:', error);
    }
}

// 監聽視窗大小變化，確保地圖適應畫面
window.addEventListener("resize", function () {
    setTimeout(() => {
        map.invalidateSize();
    }, 500);
});


// 每 1 秒更新一次無人機位置
setInterval(updateDronePosition, 10);


const ctx = document.getElementById('chargingChart').getContext('2d');

// 初始化折線圖
const chargingChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [], // 時間戳記
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
                    color: 'black' // 圖例文字顏色
                }
            }
        }
    }
});

// 獲取充電數據
async function fetchChargingData() {
    try {
        const response = await fetch('/get_charging_data');
        const data = await response.json();

        chargingChart.data.labels = data.timestamps;
        chargingChart.data.datasets[0].data = data.percentages;
        chargingChart.update();
    } catch (error) {
        console.error('Error fetching charging data:', error);
    }
}

// 每 5 秒更新一次數據
setInterval(fetchChargingData, 10);


// 從 Flask 獲取 Yaw、Pitch、Roll 數據
async function fetchDroneOrientation() {
    try {
        const response = await fetch('/get_drone_orientation');
        const data = await response.json();
        const { yaw, pitch, roll } = data;
        
        // 更新頁面上的角度顯示
        document.getElementById('pitch-angle').textContent = `${pitch.toFixed(1)}°`;
        document.getElementById('yaw-angle').textContent = `${yaw.toFixed(1)}°`;
        document.getElementById('roll-angle').textContent = `${roll.toFixed(1)}°`;

        // 原有的 3D 模型旋轉邏輯保持不變
        updateDroneRotation(yaw, pitch, roll);
    } catch (error) {
        console.error("Error fetching drone orientation:", error);
    }
}

// 確保定期調用該函數
setInterval(fetchDroneOrientation, 10);  // 每0.5秒更新一次