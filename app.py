import streamlit as st
import cv2
import time
import os
from parking_detector import ParkingDetector

def run_streamlit():
    # Page configuration
    st.set_page_config(
        page_title="ParkPulse AI — Live Parking Availability",
        page_icon="🅿️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom Glassmorphism & Dark Mode Styling
    st.markdown("""
    <style>
        .main {
            background-color: #0b0f19;
            color: #f8fafc;
        }
        .stApp {
            background: linear-gradient(180deg, #0b0f19 0%, #111827 100%);
        }
        .metric-card {
            background: rgba(17, 24, 39, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1.25rem;
            backdrop-filter: blur(12px);
            text-align: center;
        }
        .metric-title {
            font-size: 0.85rem;
            color: #94a3b8;
            font-weight: 500;
        }
        .metric-value-green {
            font-size: 2rem;
            font-weight: 700;
            color: #00e676;
        }
        .metric-value-red {
            font-size: 2rem;
            font-weight: 700;
            color: #ff3d00;
        }
        .metric-value-blue {
            font-size: 2rem;
            font-weight: 700;
            color: #38bdf8;
        }
        .metric-value-purple {
            font-size: 2rem;
            font-weight: 700;
            color: #c084fc;
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize Detector instance
    detector = ParkingDetector(pos_file='CarParkPos', video_source='carPark.mp4')

    # Sidebar Parameters
    st.sidebar.title("⚙️ Detection Controls")
    st.sidebar.markdown("Tune computer vision parameters in real-time.")

    detector.pixel_threshold = st.sidebar.slider(
        "Pixel Occupancy Threshold",
        min_value=200, max_value=2500, value=900, step=25,
        help="Pixel count above which slot is marked Occupied"
    )

    detector.blur_kernel = st.sidebar.slider(
        "Gaussian Blur Kernel",
        min_value=1, max_value=15, value=3, step=2
    )

    detector.block_size = st.sidebar.slider(
        "Adaptive Threshold Block Size",
        min_value=5, max_value=51, value=25, step=2
    )

    detector.c_val = st.sidebar.slider(
        "Threshold C Offset",
        min_value=1, max_value=40, value=16, step=1
    )

    # Header Title
    st.title("🅿️ ParkPulse AI — Live Telemetry Dashboard")
    st.caption("CCTV Automated Parking Availability Detection & Slot Management System")

    # Top KPI Metric Columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        kpi_available = st.empty()

    with col2:
        kpi_occupied = st.empty()

    with col3:
        kpi_total = st.empty()

    with col4:
        kpi_rate = st.empty()

    # Main Display: Video Frame Stream + Slot Grid
    video_placeholder = st.empty()

    # Run Video Loop
    cap = cv2.VideoCapture('carPark.mp4')

    if not cap.isOpened():
        st.error("Error loading video file: carPark.mp4")
    else:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        delay = 1.0 / fps

        while True:
            if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            annotated_frame, stats = detector.process_frame(frame)
            rgb_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

            # Update metrics
            kpi_available.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Available Slots</div>
                <div class="metric-value-green">{stats['available_slots']}</div>
            </div>
            """, unsafe_allow_html=True)

            kpi_occupied.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Occupied Slots</div>
                <div class="metric-value-red">{stats['occupied_slots']}</div>
            </div>
            """, unsafe_allow_html=True)

            kpi_total.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Capacity</div>
                <div class="metric-value-blue">{stats['total_slots']}</div>
            </div>
            """, unsafe_allow_html=True)

            kpi_rate.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Occupancy Rate</div>
                <div class="metric-value-purple">{stats['occupancy_rate']}%</div>
            </div>
            """, unsafe_allow_html=True)

            # Display Frame
            video_placeholder.image(rgb_frame, channels="RGB", use_column_width=True)

            time.sleep(0.03)

if __name__ == '__main__' or 'STREAMLIT_RUN' in os.environ:
    run_streamlit()
