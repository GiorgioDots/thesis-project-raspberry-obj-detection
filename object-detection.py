
from imutils.video import VideoStream
from imutils.video import FPS
from imutils import adjust_brightness_contrast
from threading import Thread
from multiprocessing import Process

import numpy as np
import argparse
import imutils
import time
import cv2
import json
import requests
import uuid
import os
import sys

time.sleep(10)

backendUrl = "https://raspiface-backend.herokuapp.com"

with open('/home/pi/thesis-project-raspberry-ws/raspi-config.json', 'r') as f:
	config = json.load(f)
	raspiId = config["raspiId"]
	resolution = config["resolution"].split("x")
	confidence = config["confidence"]/100
	token = config["token"]
	isActive = config["isActive"]
	url = backendUrl+"/events/"

def sendLiveImage():
	print('Sending')
	img_path = "/home/pi/thesis-project-raspberry/tmp/%s.png" % uuid.uuid4()
	print("Sending live image: %s..." %img_path)
	frame = vs.read()
	cv2.imwrite(img_path, frame)
	#image = { "image": open(img_path, "rb") }
	image = { "image": (img_path, open(img_path,"rb"), 'image/png') }
	response = requests.put(backendUrl+"/raspberry/last-image", files = image, headers = { 'Authorization': 'Bearer ' + token  })
	print(response.text)
	if os.path.exists(img_path):
		os.remove(img_path)

def sendEvent():
	img_path = "/home/pi/thesis-project-raspberry/tmp/%s.png" % uuid.uuid4()
	print("Sending new event: %s..." %img_path)
	frame = vs.read()
	cv2.imwrite(img_path, frame)
	#image = { "image": open(img_path, "rb") }
	image = { "image": (img_path, open(img_path,"rb"), 'image/png') }
	response = requests.post(url, files = image, headers = { 'Authorization': 'Bearer ' + token  })
	print(response.text)
	if os.path.exists(img_path):
  		os.remove(img_path)

ap = argparse.ArgumentParser()
ap.add_argument("-p", "--prototxt", required=True,
	help="path to Caffe 'deploy' prototxt file")
ap.add_argument("-m", "--model", required=True,
	help="path to Caffe pre-trained model")
ap.add_argument("-c", "--confidence", type=float, default=confidence,
	help="minimum probability to filter weak detections")
args = vars(ap.parse_args())

# initialize the list of class labels MobileNet SSD was trained to
# detect, then generate a set of bounding box colors for each class
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
	"bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
	"dog", "horse", "motorbike", "person", "pottedplant", "sheep",
	"sofa", "train", "tvmonitor"]
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))

# load our serialized model from disk
print("[INFO] loading model...")
net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])
# initialize the video stream, allow the cammera sensor to warmup,
# and initialize the FPS counter
print("[INFO] starting video stream...")
print(resolution[0] + " - " + resolution[1])
vs = VideoStream(src=0, usePiCamera=True, resolution=(int(resolution[0]),int(resolution[1]))).start()

time.sleep(2.0)
# fps = FPS().start()

print('Object detection is: '+str(isActive))

# loop over the frames from the video stream
while True:
	now = time.time()
	if(int(now%60)==0):
		print("sending live image")
		sendLiveImage()
	if(not isActive):
		continue
	# grab the frame from the threaded video stream and resize it
	# to have a maximum width of 400 pixels
	frame = vs.read()
	# frame = adjust_brightness_contrast(frame, contrast=0, brightness=60)
	frame = imutils.resize(frame, width=400)
	# grab the frame dimensions and convert it to a blob
	(h, w) = frame.shape[:2]
	blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
		0.007843, (300, 300), 127.5)
	# pass the blob through the network and obtain the detections and
	# predictions
	net.setInput(blob)
	detections = net.forward()

		# loop over the detections
	for i in np.arange(0, detections.shape[2]):
		# extract the confidence (i.e., probability) associated with
		# the prediction
		confidence = detections[0, 0, i, 2]
		# filter out weak detections by ensuring the `confidence` is
		# greater than the minimum confidence
		if confidence > args["confidence"]:
			# extract the index of the class label from the
			# `detections`, then compute the (x, y)-coordinates of
			# the bounding box for the object
			idx = int(detections[0, 0, i, 1])
			if CLASSES[idx] == "person":
				sendEvent()
				time.sleep(2)
			box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
			(startX, startY, endX, endY) = box.astype("int")
			# draw the prediction on the frame
			label = "{}: {:.2f}%".format(CLASSES[idx],
				confidence * 100)
			cv2.rectangle(frame, (startX, startY), (endX, endY),
				COLORS[idx], 2)
			y = startY - 15 if startY - 15 > 15 else startY + 15
			cv2.putText(frame, label, (startX, y),
				cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)

		# show the output frame
	# cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF
	# if the `q` key was pressed, break from the loop
	# if key == ord("q"):
	# 	break
	# update the FPS counter
	# fps.update()

# fps.stop()
print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))
# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
