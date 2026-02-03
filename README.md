Gesture Controlled Presentation using OpenCV, Python, and MediaPipe

This project implements a real-time, gesture-controlled presentation system that allows users to navigate slides and annotate them using hand gestures captured via a webcam. The system leverages MediaPipe-based hand landmark detection (via cvzone) and deterministic gesture logic to provide a touchless, interactive presentation experience.

Features

Real-Time Hand Tracking:
Uses MediaPipe’s ML-based hand pose model to detect 21 hand landmarks per frame for accurate finger and gesture tracking.

Gesture-Based Slide Navigation:
Navigate between slides using pinch gestures, eliminating the need for keyboard or mouse input.

On-Slide Annotation:
Draw freehand annotations directly on slides using finger gestures during presentations.

Pointer Mode:
Use hand gestures to control a pointer for highlighting slide content.

Annotation Erase Support:
Remove the most recent annotation stroke using a dedicated erase gesture.

Webcam Overlay:
Displays a live webcam preview inset on the slide for better presenter context.

Requirements

Python 3.x

OpenCV
Install via:

pip install opencv-python


cvzone (for MediaPipe hand tracking wrapper)

pip install cvzone


MediaPipe

pip install mediapipe==0.10.9


NumPy

pip install numpy

Installation

Clone the repository:

git clone https://github.com/nitinsai04/HonorsMiniProject.git


Navigate to the project directory:

cd HonorsMiniProject


Install dependencies:

pip install -r requirements.txt

Usage

Place your presentation slides in the Resources folder.
Slides should be named in the format:

slide1.png, slide2.png, slide3.png, ...


Run the application:

python main.py


The presentation window will open in real time. You can now control slides and annotations using hand gestures.

Hand Gestures
Gesture	Description
Thumb + Index pinch (hand raised)	Go to previous slide
Thumb + Middle pinch (hand raised)	Go to next slide
Index finger only	Draw annotations on the slide
Index + Middle fingers	Pointer mode (cursor movement)
Index + Middle + Ring fingers	Erase the last annotation stroke
Slide change	Automatically clears all annotations

A vertical hand-position threshold is used to separate slide navigation gestures from annotation gestures to avoid accidental triggers.

Technical Notes

Gesture recognition uses geometry-based rules (finger states, pinch distances, hand position) on top of ML-based hand landmark detection.

A debounce mechanism is implemented to prevent repeated triggers from sustained gestures.

Annotations are rendered as vector strokes, enabling smooth and persistent drawing during a slide.

Applications

Classroom and academic presentations

Touchless presentations for accessibility

Interactive demos and live explanations
