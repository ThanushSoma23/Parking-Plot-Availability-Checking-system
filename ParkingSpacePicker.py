import cv2
import pickle
import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Interactive Parking Space Coordinate Picker Tool")
    parser.add_argument("--video", type=str, default=None, help="Path to input video file")
    parser.add_argument("--image", type=str, default=None, help="Path to input image file")
    parser.add_argument("--output", type=str, default="CarParkPos", help="Path to output pickle position file")
    parser.add_argument("--width", type=int, default=107, help="Parking slot box width in pixels")
    parser.add_argument("--height", type=int, default=48, help="Parking slot box height in pixels")

    args = parser.parse_args()

    width = args.width
    height = args.height
    pos_file = args.output

    # Load initial positions if file exists
    pos_list = []
    if os.path.exists(pos_file):
        try:
            with open(pos_file, 'rb') as f:
                pos_list = pickle.load(f)
            print(f"Loaded {len(pos_list)} slot positions from '{pos_file}'.")
        except Exception as e:
            print(f"Warning: Failed to load '{pos_file}': {e}")
            pos_list = []

    def save_positions():
        try:
            with open(pos_file, 'wb') as f:
                pickle.dump(pos_list, f)
            print(f"Saved {len(pos_list)} positions to '{pos_file}'.")
        except Exception as e:
            print(f"Error saving to '{pos_file}': {e}")

    # Determine frame source
    frame = None
    if args.video:
        if not os.path.exists(args.video):
            print(f"Error: Video file '{args.video}' not found.")
            sys.exit(1)
        cap = cv2.VideoCapture(args.video)
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            print(f"Error: Could not read first frame from video '{args.video}'.")
            sys.exit(1)
    elif args.image:
        if not os.path.exists(args.image):
            print(f"Error: Image file '{args.image}' not found.")
            sys.exit(1)
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"Error: Could not read image '{args.image}'.")
            sys.exit(1)
    else:
        # Fallback default source check
        if os.path.exists("carParkImg.png"):
            frame = cv2.imread("carParkImg.png")
        elif os.path.exists("carPark.mp4"):
            cap = cv2.VideoCapture("carPark.mp4")
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                frame = None

    if frame is None:
        print("Error: No valid video or image input available.")
        sys.exit(1)

    def mouse_click(event, x, y, flags, param):
        nonlocal pos_list
        if event == cv2.EVENT_LBUTTONDOWN:
            pos_list.append((x, y))
            save_positions()
        elif event == cv2.EVENT_RBUTTONDOWN:
            for idx, pos in enumerate(pos_list):
                x1, y1 = pos
                if x1 <= x <= x1 + width and y1 <= y <= y1 + height:
                    pos_list.pop(idx)
                    save_positions()
                    break

    window_name = f"Parking Slot Picker - {pos_file}"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_click)

    print("\n--- Parking Space Picker Tool ---")
    print("  Left-click:  Add a parking space box")
    print("  Right-click: Delete bounding box under cursor")
    print("  Press 'q' or ESC: Save and exit")
    print(f"  Target File: {pos_file}")
    print("---------------------------------\n")

    while True:
        img_copy = frame.copy()
        for idx, pos in enumerate(pos_list):
            x1, y1 = pos
            cv2.rectangle(img_copy, (x1, y1), (x1 + width, y1 + height), (255, 0, 255), 2)
            cv2.putText(img_copy, f"{idx+1}", (x1 + 4, y1 + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

        # Draw slot count overlay
        cv2.putText(img_copy, f"Total Slots Marked: {len(pos_list)}", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow(window_name, img_copy)
        key = cv2.waitKey(20) & 0xFF
        if key == ord('q') or key == 27:
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
