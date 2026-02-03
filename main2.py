import os
import cv2
import numpy as np
from enum import Enum
from cvzone.HandTrackingModule import HandDetector

# =========================================================
# Helper: Pinch Detection
# =========================================================
def pinch(lmList, id1, id2, threshold=40):
    x1, y1 = lmList[id1][0], lmList[id1][1]
    x2, y2 = lmList[id2][0], lmList[id2][1]
    dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
    return dist < threshold


# =========================================================
# Gesture Abstraction (UML: Gesture)
# =========================================================
class Gesture(Enum):
    NEXT = 1
    PREVIOUS = 2
    DRAW = 3
    POINTER = 4
    ERASE = 5
    NONE = 0


# =========================================================
# Camera Handler (UML: CameraHandler)
# =========================================================
class CameraHandler:
    def __init__(self, width, height, source=0):
        self.videoSource = source
        self.cap = cv2.VideoCapture(source)
        self.cap.set(3, width)
        self.cap.set(4, height)

    def captureFrame(self):
        success, frame = self.cap.read()
        if not success:
            return None
        return cv2.flip(frame, 1)


# =========================================================
# Hand Tracker (UML: HandTracker)
# Uses MediaPipe internally via cvzone
# =========================================================
class HandTracker:
    def __init__(self, detectionCon=0.7, maxHands=1):
        self.handModel = HandDetector(
            detectionCon=detectionCon, maxHands=maxHands
        )

    def detectLandmarks(self, frame):
        hands, annotatedFrame = self.handModel.findHands(frame)
        return hands, annotatedFrame


# =========================================================
# Gesture Classifier (UML: GestureClassifier)
# =========================================================
class GestureClassifier:
    def __init__(self, gestureThreshold=300):
        self.gestureRules = {}
        self.gestureThreshold = gestureThreshold

    def classifyGesture(self, hand, detector):
        lmList = hand["lmList"]
        fingers = detector.fingersUp(hand)
        _, cy = hand["center"]

        # Slide control region
        if cy <= self.gestureThreshold:
            if pinch(lmList, 4, 8):
                return Gesture.PREVIOUS
            if pinch(lmList, 4, 12):
                return Gesture.NEXT

        # Drawing / pointer / erase
        if fingers == [0, 1, 0, 0, 0]:
            return Gesture.DRAW

        if fingers == [0, 1, 1, 0, 0]:
            return Gesture.POINTER

        if fingers == [0, 1, 1, 1, 0]:
            return Gesture.ERASE

        return Gesture.NONE


# =========================================================
# Action Controller (UML: ActionController)
# =========================================================
class ActionController:
    def __init__(self, slidePaths):
        self.actionMap = {}
        self.slidePaths = slidePaths
        self.currentSlide = 0

        self.annotations = [[]]
        self.annotationIndex = 0
        self.annotationActive = False

    def nextSlide(self):
        if self.currentSlide < len(self.slidePaths) - 1:
            self.currentSlide += 1
            self.clearAnnotations()


    def previousSlide(self):
        if self.currentSlide > 0:
            self.currentSlide -= 1
            self.clearAnnotations()


    def draw(self, point):
        if not self.annotationActive:
            self.annotationActive = True
            self.annotationIndex += 1
            self.annotations.append([])
        self.annotations[self.annotationIndex].append(point)

    def stopDrawing(self):
        self.annotationActive = False

    def erase(self):
    # Only erase if there is an actual stroke
        if len(self.annotations) > 1:
            self.annotations.pop()
            self.annotationIndex -= 1

        # Clamp state
        self.annotationIndex = max(self.annotationIndex, 0)
        self.annotationActive = False

    def clearAnnotations(self):
        self.annotations = [[]]
        self.annotationIndex = 0
        self.annotationActive = False


# =========================================================
# MAIN APPLICATION (Module Pipeline)
# =========================================================
def main():
    # ---------------- Configuration ----------------
    WIDTH, HEIGHT = 1280, 720
    SLIDE_W, SLIDE_H = 960, 540
    folderPath = "Resources"
    gestureThreshold = 300
    buttonDelay = 20

    # ---------------- Initialization ----------------
    camera = CameraHandler(WIDTH, HEIGHT)
    tracker = HandTracker()
    classifier = GestureClassifier(gestureThreshold)

    slidePaths = sorted(
    [f for f in os.listdir(folderPath) if f.startswith("slide") and f.endswith(".png")],
    key=lambda x: int(x.replace("slide", "").replace(".png", ""))
)

    controller = ActionController(slidePaths)

    buttonPressed = False
    buttonCounter = 0

    # ---------------- Main Loop ----------------
    while True:
        frame = camera.captureFrame()
        if frame is None:
            break

        slidePath = os.path.join(
            folderPath, slidePaths[controller.currentSlide]
        )
        slideImg = cv2.resize(
            cv2.imread(slidePath), (SLIDE_W, SLIDE_H)
        )

        hands, annotatedFrame = tracker.detectLandmarks(frame)
        cv2.line(
            annotatedFrame,
            (0, gestureThreshold),
            (WIDTH, gestureThreshold),
            (0, 255, 255),
            5,
        )

        if hands and not buttonPressed:
            hand = hands[0]
            gesture = classifier.classifyGesture(
                hand, tracker.handModel
            )

            lmList = hand["lmList"]
            xVal = int(
                np.interp(lmList[8][0], [WIDTH // 2, WIDTH], [0, SLIDE_W])
            )
            yVal = int(
                np.interp(
                    lmList[8][1], [150, HEIGHT - 150], [0, SLIDE_H]
                )
            )
            indexPoint = (xVal, yVal)

            if gesture == Gesture.NEXT:
                controller.nextSlide()
                buttonPressed = True

            elif gesture == Gesture.PREVIOUS:
                controller.previousSlide()
                buttonPressed = True

            elif gesture == Gesture.DRAW:
                controller.draw(indexPoint)

            elif gesture == Gesture.POINTER:
                controller.stopDrawing()
                cv2.circle(
                    slideImg, indexPoint, 10, (0, 0, 255), cv2.FILLED
                )

            elif gesture == Gesture.ERASE:
                controller.erase()
                buttonPressed = True

            else:
                controller.stopDrawing()

        # ---------------- Debounce ----------------
        if buttonPressed:
            buttonCounter += 1
            if buttonCounter > buttonDelay:
                buttonPressed = False
                buttonCounter = 0

        # ---------------- Render Annotations ----------------
        for stroke in controller.annotations:
            for i in range(1, len(stroke)):
                cv2.line(
                    slideImg,
                    stroke[i - 1],
                    stroke[i],
                    (200, 200, 0),
                    5,
                )

        # Webcam preview
        webcamSmall = cv2.resize(annotatedFrame, (213, 120))
        slideImg[0:120, SLIDE_W - 213 : SLIDE_W] = webcamSmall

        cv2.imshow("Slides", slideImg)
        cv2.imshow("Camera", annotatedFrame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


if __name__ == "__main__":
    main()
