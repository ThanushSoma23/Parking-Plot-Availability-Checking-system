import cv2
import pickle


width,height=107,48
try:
    with open('CarParkPos', 'rb') as f:
        poslist1=pickle.load(f)
except:
    poslist1=[]

def mouseClick(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        poslist1.append((x,y))
    if event==cv2.EVENT_RBUTTONDOWN:
        for i,pos in enumerate(poslist1):
            x1,y1=pos
            if x1<x<x1+width and y1<y<y1+height:
                poslist1.pop(i)

    with open('CarParkPos','wb') as f:
        pickle.dump(poslist1,f)


while True:
    img = cv2.imread('carParkImg.png')
    for pos in poslist1:
        cv2.rectangle(img,pos,(pos[0]+width,pos[1]+height), (255, 0, 255), 2)
    cv2.imshow("image", img)
    cv2.setMouseCallback("image",mouseClick)
    cv2.waitKey(1)

