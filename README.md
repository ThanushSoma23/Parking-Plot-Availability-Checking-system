# 🅿️ ParkPulse AI — Parking Plot Availability Checking System

> An intelligent, computer vision-powered web application that monitors CCTV video feeds of parking lots in real-time, calculates slot availability, and displays live telemetry analytics on a dark glassmorphism dashboard.

---

## ✨ Features

- 🚘 **Real-Time Video Stream**: Live MJPEG computer vision video feed displaying bounded parking slots (Green = Available, Red = Occupied).
- 📊 **Telemetry Dashboard**: Live KPI cards showing Total Capacity (69), Available Slots, Occupied Slots, and Occupancy Rate (%).
- 🎛️ **Live Parameter Drawer**: Interactive sliders to adjust adaptive thresholding, Gaussian blur kernel size, block size, and noise offset in real-time.
- 🔲 **Slot Status Matrix**: Dynamic grid displaying individual status badges (P1 through P69) with status filtering (All / Available / Occupied).
- ☁️ **Cloud Deployable**: Ready for deployment on **Streamlit Cloud**, **Render**, **Docker**, **Railway**, or local deployment.

---

## 🚀 Quick Start (Local Execution)

### Option 1: Flask Web App (Recommended)
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the Flask Web Server
python server.py

# 3. Open browser at http://localhost:5000
```

### Option 2: Streamlit Dashboard
```bash
# Run Streamlit Application
streamlit run app.py

# Open browser at http://localhost:8501
```

---

## ☁️ Deployment Options

### 1. Streamlit Community Cloud (Free & 1-Click)
1. Push repository to GitHub.
2. Visit [share.streamlit.io](https://share.streamlit.io/).
3. Connect repository and select `app.py` as the entrypoint.

### 2. Render / Railway / Cloud Run
- Deploy using the included `Dockerfile` or `render.yaml`.
- Set start command to `python server.py`.

### 3. Docker Container
```bash
# Build image
docker build -t parkpulse-ai .

# Run container
docker run -p 5000:5000 parkpulse-ai
```

---

## 🛠️ Tech Stack

- **Computer Vision**: OpenCV (`cv2`), NumPy, CVZone
- **Backend**: Python 3.10+, Flask / Streamlit
- **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism), JavaScript (Fetch API), Google Fonts (Inter/Outfit), Lucide Icons
