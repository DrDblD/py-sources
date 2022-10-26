from flask import Flask, request, Response, jsonify, send_file, send_from_directory
import json
import os
import tempfile
import logging
from flask_cors import CORS
from config_reader import Config
from jira import JIRA
from jira_query import JiraQueryData, JiraUpdateData
from base64 import b64encode, b64decode
from webbrowser import open as webopen


DEFAULT_LOGLEVEL = 'warning'

app = Flask(__name__)
CORS(app)

config = Config("jira-gantt.ini")

endpoint = config.getter("Endpoint")
token = b64decode(
        config.getter("Token").encode('utf-8')
        ).decode('utf-8')
workers = int(
        config.getter("Workers")
        )
log_level_comparsion = {
                    "50": "CRITICAL",
                    "40": "ERROR",
                    "30": "WARNING",
                    "20": "INFO",
                    "10": "DEBUG",
                    "0": "NOTSET"
}

# find numeric value of log level by it's string  
log_level = getattr(
    logging, 
    log_level_comparsion[ str (10 * int(
        config.getter("Logging") # [0..5] int
        ))], 
    None 
)
log_filename = config.getter("LogPath")

logging.basicConfig(filename=log_filename, encoding='utf-8', filemode='w', level=log_level)
app.logger.setLevel(level=log_level)

handler = JIRA(server = endpoint, token_auth = token, async_ = True, async_workers=workers)

build_path = "build" 

temp_file = tempfile.TemporaryFile()
         # seek() method is called to set the file pointer at the starting of the file 
         # takes as argument the index of the character before which we want to place the pointer
         # temp_file.seek(0) - after IO operation 
print(temp_file.name)

tasks = []
@app.route("/")
def hello():
    return open(os.path.join(app.root_path, build_path, "index.html"), "r").read()

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/build/<filename>")
def show_file(filename):
    return send_file(os.path.join(build_path, filename))

@app.route('/search', methods=["GET", "POST"])
def search():
    # logging.INFO("search endpoint reached...")
    
    if request.method == "GET":
        temp_data = temp_file.read().decode('utf-8')
        temp_file.seek(0)
        query = json.loads(temp_data)["query"]
        data = JiraQueryData(handler, query)
        tasks = data.generate_dataframe()
        return jsonify(tasks)

    if request.method == "POST":
        received_data = request.get_json()
        # logging.INFO(f"received data: {received_data}")
        temp_file.write(json.dumps(received_data).encode('utf-8'))
        temp_file.seek(0)
        
        return_data = {
            "status": "success",
            "message": f"received: {received_data}"
        }
        return Response(response=json.dumps(return_data), status=201)

@app.route('/update', methods=["POST"])
def update():
    # logging.INFO("update endpoint reached...")
    if request.method == "POST":
        received_data = request.get_json()
        dtasks = received_data
        
        return_data = JiraUpdateData(handler).update_tasks(dtasks)
        return Response(response=json.dumps(return_data), status=201)

if __name__ == "__main__":
    # webopen("build/index.html")
    app.run("localhost", 6969)
    webopen("http://localhost:6969")
    temp_file.close()