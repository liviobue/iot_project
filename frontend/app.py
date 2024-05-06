# app.py
from flask import Flask, render_template
from pymongo import MongoClient
import plotly.graph_objs as go
from config import MONGO_URI
import json
from bson import ObjectId  # Import ObjectId from bson library
from datetime import datetime

app = Flask(__name__)

# MongoDB connection setup
client = MongoClient(MONGO_URI)
db = client['IoT-Project']
collection = db['Raw-Data']

# Function to serialize datetime objects
def serialize_date(obj):
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

data_from_mongo = collection.find()

# Print each document in JSON format
for document in data_from_mongo:
    # Convert ObjectId to string
    document['_id'] = str(document['_id'])
    print(json.dumps(document, indent=4, default=serialize_date))

""" 
@app.route('/')
def index():
    # Fetch data from MongoDB
    data_from_mongo = collection.find()

    # Extract necessary data for plotting
    timestamps = []
    sensor_values = []
    for data in data_from_mongo:
        timestamps.append(data['timestamp'])
        sensor_values.append(data['sensor_value'])

    # Create a Plotly graph
    graph = go.Scatter(x=timestamps, y=sensor_values, mode='lines', name='Sensor Data')

    layout = go.Layout(title='IoT Sensor Data', xaxis=dict(title='Timestamp'), yaxis=dict(title='Sensor Value'))
    figure = go.Figure(data=[graph], layout=layout)

    # Convert Plotly graph to JSON for passing to the template
    graph_json = figure.to_json()

    return render_template('index.html', graph_json=graph_json)

if __name__ == '__main__':
    app.run(debug=True)
 """