# app.py

from flask import Flask, render_template, jsonify
from pymongo import MongoClient
import plotly.graph_objs as go
from config import MONGO_URI

app = Flask(__name__)

# MongoDB connection setup
client = MongoClient(MONGO_URI)
db = client['iot_database']
collection = db['iot_data']

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

@app.route('/data')
def get_data():
    # Fetch data from MongoDB
    data_from_mongo = collection.find()

    # Convert MongoDB data to JSON
    data = []
    for doc in data_from_mongo:
        data.append({
            'timestamp': doc['timestamp'],
            'sensor_value': doc['sensor_value']
        })

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
