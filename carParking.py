import cv2
import pickle
import cvzone
import numpy as np

try:
    with open('CarParkPos', 'rb') as f:
        poslist1 = pickle.load(f)
except Exception as e:
    print(f"Error loading CarParkPos: {e}")
    poslist1 = []

width, height = 107, 48

def checkParkingSpace(imgPro, img):
    spaceCounter = 0
    for pos in poslist1:
        x, y = pos
        imgCrop = imgPro[y:y + height, x:x + width]
        if imgCrop.size == 0:
            continue
        count = cv2.countNonZero(imgCrop)

        if count < 900:
            color = (0, 255, 0)
            thickness = 5
            spaceCounter += 1
        else:
            color = (0, 0, 255)
            thickness = 2
        cv2.rectangle(img, pos, (pos[0] + width, pos[1] + height), color, thickness)
    
    total_slots = len(poslist1) if len(poslist1) > 0 else 1
    cvzone.putTextRect(img, f'Available:{spaceCounter}/{total_slots}', (100, 50), scale=3, thickness=5, offset=10, colorR=(0, 200, 0))

cap = cv2.VideoCapture('carPark.mp4')

while True:
    if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    success, img = cap.read()
    if not success or img is None:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        success, img = cap.read()
        if not success or img is None:
            continue

    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(imgGray, (3, 3), 1)
    imgThreshold = cv2.adaptiveThreshold(imgBlur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)
    imgMedian = cv2.medianBlur(imgThreshold, 5)
    kernel = np.ones((3, 3), np.uint8)
    imgDilate = cv2.dilate(imgMedian, kernel, iterations=1)

    checkParkingSpace(imgDilate, img)

    cv2.imshow("image", img)
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()