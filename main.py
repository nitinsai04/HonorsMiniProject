import os
import cv2
import numpy as np
from cvzone.HandTrackingModule import HandDetector

# -------------------- Helper: Pinch Detection --------------------
def pinch(lmList, id1, id2, threshold=40):
    x1, y1 = lmList[id1][0], lmList[id1][1]
    x2, y2 = lmList[id2][0], lmList[id2][1]
    dist = ((x1 - x2)**2 + (y1 - y2)**2) ** 0.5
    return dist < threshold

# -------------------- Variables --------------------
width, height = 1280, 720
folderPath = "Resources"
w, h = 960, 540

cap = cv2.VideoCapture(0)
cap.set(3, width)
cap.set(4, height)

pathImages = sorted(
    [f for f in os.listdir(folderPath) if f.startswith("slide") and f.endswith(".png")],
    key=lambda x: int(x.replace("slide", "").replace(".png", ""))
)
imgNumber = 0

gestureThreshold = 300
buttonPressed = False
buttonCounter = 0
buttonDelay = 20

annotations = [[]]
annotationNumber = 0
annotationStart = False

# -------------------- Hand Detector --------------------
detector = HandDetector(detectionCon=0.7, maxHands=1)

# -------------------- Main Loop --------------------
while True:
    success, img = cap.read()
    img = cv2.flip(img, 1)

    pathFullImage = os.path.join(folderPath, pathImages[imgNumber])
    imgCurrent = cv2.imread(pathFullImage)
    imgSlide = cv2.resize(imgCurrent, (w, h))

    hands, img = detector.findHands(img)
    cv2.line(img, (0, gestureThreshold), (width, gestureThreshold), (0, 255, 255), 5)

    if hands and not buttonPressed:
        hand = hands[0]
        lmList = hand["lmList"]
        fingers = detector.fingersUp(hand)
        cx, cy = hand["center"]

        xVal = int(np.interp(lmList[8][0], [width // 2, width], [0, w]))
        yVal = int(np.interp(lmList[8][1], [150, height - 150], [0, h]))
        indexFinger = (xVal, yVal)

        # -------------------- SLIDE CONTROL (PINCH) --------------------
        if cy <= gestureThreshold:

            annotationStart = False

            # Previous slide (Thumb + Index)
            if pinch(lmList, 4, 8):
                if imgNumber > 0:
                    buttonPressed = True
                    imgNumber -= 1
                    annotations = [[]]
                    annotationNumber = 0

            # Next slide (Thumb + Middle)
            elif pinch(lmList, 4, 12):
                if imgNumber < len(pathImages) - 1:
                    buttonPressed = True
                    imgNumber += 1
                    annotations = [[]]
                    annotationNumber = 0

        # -------------------- POINTER --------------------
        elif fingers == [0, 1, 1, 0, 0]:
            cv2.circle(imgSlide, indexFinger, 10, (0, 0, 255), cv2.FILLED)
            annotationStart = False

        # -------------------- DRAW --------------------
        elif fingers == [0, 1, 0, 0, 0]:
            if not annotationStart:
                annotationStart = True
                annotationNumber += 1
                annotations.append([])
            annotations[annotationNumber].append(indexFinger)
            cv2.circle(imgSlide, indexFinger, 5, (200, 200, 0), cv2.FILLED)

        else:
            annotationStart = False

        # -------------------- ERASE --------------------
        if fingers == [0, 1, 1, 1, 0]:
            if annotationNumber >= 0:
                annotations.pop(-1)
                annotationNumber -= 1
                buttonPressed = True

    # -------------------- Debounce --------------------
    if buttonPressed:
        buttonCounter += 1
        if buttonCounter > buttonDelay:
            buttonCounter = 0
            buttonPressed = False

    # -------------------- Draw Annotations --------------------
    for i in range(len(annotations)):
        for j in range(1, len(annotations[i])):
            cv2.line(imgSlide, annotations[i][j - 1],
                     annotations[i][j], (200, 200, 0), 5)

    # Webcam preview on slide
    imgSmall = cv2.resize(img, (213, 120))
    imgSlide[0:120, w - 213:w] = imgSmall

    cv2.imshow("Slides", imgSlide)
    cv2.imshow("Image", img)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
