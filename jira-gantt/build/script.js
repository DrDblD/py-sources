var xhr = null;
var tasks = new Array();
var options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
var show_close_alert = true;

var ganttChart = new Gantt();
// let ganttChart = new Gantt();

function getXmlHttpRequestObject() {
    if (!xhr) {
        // Create a new XMLHttpRequest object 
        xhr = new XMLHttpRequest();
    }
    return xhr;
};
function getTasksCallback() {
    // Check response is ready or not
    if (xhr.readyState == 4 && xhr.status == 200) {
        console.log("User data received!");     
        output =  xhr.responseText;
        tasks = JSON.parse(output);

        ganttDiv = document.getElementById('gantt-all');
        // ganttDiv.style.visibility='visible'; 
        ganttDiv.hidden=false;

        let chart = new Gantt("#gantt", tasks, {
            on_view_change: function(mode) {
                document.getElementById("current-timescale").innerText = mode;
            },
            custom_popup_html: function(task) {
                return `
                  <div class="details-container">
                    <h5>${task.name}</h5>
                    <p>Task started on: ${task._start.toLocaleDateString("ru-RU", options)}</p>
                    <p>Expected to finish by ${task._end.toLocaleDateString("ru-RU", options)}</p>
                    <p>Status is "${task.status}"</p>

                  </div>
                `;
            }
        });
        ganttChart = chart;
}};
function getTasks() {
    console.log("Get users...");
    xhr = getXmlHttpRequestObject();
    xhr.onreadystatechange = getTasksCallback;
    // asynchronous requests
    xhr.open("GET", "http://localhost:6969/search", true);
    // Send the request over the network
    xhr.send(null);
};
function sendDataCallback() {
    // Check response is ready or not
    if (xhr.readyState == 4 && xhr.status == 201) {
        console.log("Data creation response received!");
        getDate();
        dataDiv = document.getElementById('sent-data-container');
        // Set current data text
        dataDiv.innerHTML = xhr.responseText;
    }
};
function sendQuery() {
    dataToSend = document.getElementById('data-input').value;
    if (!dataToSend) {
        console.log("Data is empty.");
        return;
    }
    console.log("Sending data: " + dataToSend);
    xhr = getXmlHttpRequestObject();
    xhr.onreadystatechange = sendDataCallback;
    // asynchronous requests
    xhr.open("POST", "http://localhost:6969/search", true);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    // Send the request over the network
    xhr.send(JSON.stringify({"query": dataToSend}));
};
function sendTasks() {
    dataToSend = tasks
    if (!dataToSend) {
        console.log("Data is empty.");
        return;
    }
    // console.log("Sending data: " + dataToSend);
    xhr = getXmlHttpRequestObject();
    xhr.onreadystatechange = sendDataCallback;
    // asynchronous requests
    xhr.open("POST", "http://localhost:6969/update", true);
    xhr.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    // Send the request over the network
    xhr.send(JSON.stringify(dataToSend));
};

function getDate() {
    date = new Date().toString();
    document.getElementById('time-container').textContent = date;
}
(function () {
    getDate();
})();
function changeViewGantt(mode) {
    ganttChart.change_view_mode(mode);
};

// window.onbeforeunload = function(){
//     alert('Are you sure you want to leave?');
//     return false;
// };

window.onbeforeunload = closingCode;
function closingCode(){
    alert('Are you sure you want to leave?');
    return null;
}