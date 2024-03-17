from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import json
import base64
import requests
import json
import subprocess
from bson import ObjectId
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, template_folder='/home/ubuntu/polygon')
width = 0
height = 0
mission_id = 0


# Function to capture a frame from the video stream
def capture_frame(camera_index):
    global height
    global width
    print(f"POLYGON {camera_index}")
    host = os.environ.get("HOST")
    cap = cv2.VideoCapture(f"rtmp://{host}:1935/live_hls/{camera_index}")
    if not cap.isOpened():
        print("Error opening video stream.")
        return None
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


# Function to save data to a JSON file

def retrieve_missions(camera_index):
    url_mission = f"http://localhost:5500/api/findRtmpCode/{camera_index}"
    payload_mission = json.dumps({})
    headers = {
        'Content-Type': 'application/json-patch+json',
        'Authorization': 'Basic YWRtaW46QXVndV8yMDIz'
    }

    response = requests.request("GET", url_mission, headers=headers, data=payload_mission)
    return json.loads(response.text)


def add_polygon(data):
    url = f"http://localhost:5500/api/addpolygon"
    payload = json.dumps(data)
    headers = {
        'Content-Type': 'application/json-patch+json',
        'Authorization': 'Basic YWRtaW46QXVndV8yMDIz'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.text)


def save_to_json(rect_coords, camera_index):
    global height
    global width
    global mission_id
    #
    # Calculate percentage of polygon within frame
    #
    x_min = rect_coords[0]
    y_min = rect_coords[1]
    x_max = x_min + rect_coords[2]
    y_max = y_min + rect_coords[3]
    x_min_percentage = x_min / width
    y_min_percentage = y_min / height
    x_max_percentage = x_max / width
    y_max_percentage = y_max / height
    rect_coords_percentage = [x_min_percentage, y_min_percentage, x_max_percentage, y_max_percentage]
    file_name = f'{camera_index}_data.json'
    # Specify a directory you have write access to
    mission_det = retrieve_missions(camera_index)
    path = 'D:\\shared\\polygon\\' + file_name
    data = {"mission_id": mission_id,
            "camera_id": mission_det['camera_id'],
            "rtmpCode": camera_index, "rect_coords": rect_coords, "rect_percentage": rect_coords_percentage}
    add_polygon(data)
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)


@app.route('/')
def index():
    command = f"cat /home/ubuntu/livestream/cameras.dat | awk '{{print $(NF-2)}}' | sort -u"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    cameras = result.stdout.splitlines()

    split_cameras = [camera.split(",") for camera in cameras]
    print(result)
    return render_template('email.html', result=split_cameras)


@app.route('/cameras', methods=['POST'])
def index_c():
    user_email = request.form.get('user_email')
    command = f"cat /home/ubuntu/livestream/cameras.dat | awk '{{print $1,\",\",$3,\",\",$NF,\",\",$(NF-1),\",\",$(NF-3)}}' | grep {user_email}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    cameras = result.stdout.splitlines()

    split_cameras = [camera.split(",") for camera in cameras]
    print(f"cameras_split={split_cameras}")
    print(result)
    return render_template('index.html', result=split_cameras)


@app.route('/capture', methods=['POST'])
def capture():
    global mission_id
    camera_index = request.form.get('camera_index')
    mission_id = request.form.get('mission_id')
    print(f"POLYGON=camera_index={camera_index} mission_id={mission_id}")
    frame = capture_frame(camera_index)

    if frame is not None:
        _, buffer = cv2.imencode('.jpg', frame)
        frame_encoded = base64.b64encode(buffer).decode('utf-8')
        return render_template('display_frame.html', frame_encoded=frame_encoded, camera_index=camera_index)
    else:
        return "Failed to capture frame from the video stream."

@app.route('/captureimage/<mission_id>/<rtmpCode>', methods=['GET'])
def captureimage(mission_id,rtmpCode):
    #data = request.json
    #mission_id = data.get("name")
    #rtmpCode = data.get('rtmpCode')

    print(f"POLYGON=camera_index={rtmpCode} mission_id={mission_id}")
    frame = capture_frame(rtmpCode)

    if frame is not None:
        _, buffer = cv2.imencode('.jpg', frame)
        frame_encoded = base64.b64encode(buffer).decode('utf-8')
        return render_template('display_frame.html', frame_encoded=frame_encoded, camera_index=rtmpCode)
    else:
        return "Failed to capture frame from the video stream."

@app.route('/save_coords', methods=['POST'])
def save_coords():
    data = request.get_json()
    print(width)
    rect_coords = data['rect_coords']
    camera_index = data['camera_index']
    save_to_json(rect_coords, camera_index)
    return jsonify({"message": "Coordinates saved successfully"})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5600)
