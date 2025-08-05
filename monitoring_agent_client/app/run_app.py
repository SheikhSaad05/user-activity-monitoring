import time
from datetime import datetime
import requests
import platform
import psutil
import socket
from flask import jsonify
import win32process
import os


def get_ip():
    try:
        host_name = socket.gethostname()
        ip_addr = socket.gethostbyname(host_name)
        user_name = os.getlogin() 
        return ip_addr, user_name
    except Exception as e:
        return "error -- {e}"


def get_user_window_information():
    try:
        if platform.system() == "Windows":
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name()
            return window_title, process_name
        
        elif platform.system() == "Linux":
            import subprocess
            win_id = subprocess.check_output([
                "xdotool","getactivewindow"
            ])
            win_name =  subprocess.check_output([
                "xdotool","getwindowname", win_id.strip()
            ])
            return win_name.decode("utf-8")
        else:
            return "Unknown OS"
    except Exception as e:
        return "Exception Occur -- {e}"
    
def log_software_usage(backend_url,interval, last_window, last_timestamp):
    active_window, process_name = get_user_window_information()
    timestamp = datetime.now()
    user_IP, user_name = get_ip()
    cpu_usage = psutil.cpu_percent(interval = 2)
    ram_usage = psutil.virtual_memory().percent


    # Calculate duration if the active window has changed
    if active_window != last_window:
        if last_window:  # Only calculate duration if last window exists
            duration = (timestamp - last_timestamp).total_seconds()
        else:
            duration = 0
        # Log duration for the previous window
        print(f"Window '{last_window}' was active for {duration:.2f} seconds.")

        # Update last_window and timestamp
        last_window = active_window
        last_timestamp = timestamp
    else:
        # If the window is still the same, use previous duration
        duration = (timestamp - last_timestamp).total_seconds()

    usage_data = {
        "user_ip" : user_IP,
        "user_name" : user_name,
        "window_title" : active_window,
        "process_name" : process_name,
        "timestamp" : timestamp,
        "cpu_usage" : cpu_usage,
        "ram_usage" : ram_usage,
        "duration" : duration
    }
    usage_data["timestamp"] = usage_data["timestamp"].isoformat()
    try:
        response = requests.post(backend_url, json=usage_data)
        response.raise_for_status()
        print(f"Sent usage data : {usage_data}")
    except Exception as e:
        print(f"Error Sending data: {e}")


    return last_window, last_timestamp

if __name__ == "__main__":
    backend_url = "http://192.168.1.100:8000/api/usage"
    interval = 5

    last_window = None
    last_timestamp = datetime.now()

    while True:
        last_window, last_timestamp = log_software_usage(backend_url, interval, last_window, last_timestamp)
        # log_software_usage(backend_url, interval)
        time.sleep(interval)
## ------------------------------ version 1 -----------------------------