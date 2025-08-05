# from flask import Flask, request, jsonify
# from pymongo import MongoClient
# from datetime import datetime
# import json


# app = Flask(__name__)

# try:
#     client = MongoClient("mongodb://localhost:27017/?serverSelectionTimeoutMS=1000")# Replace localost with 10.10.10.10 
#     client.server_info()
#     db = client["monitoringsystem"]
#     logs_col = db['app_usage_logs']
# except:
#     print("Error Connecting Mongo --")
    
# # ---
# @app.route('/api/usage', methods = ['POST'])
# def log_usage_data():
#     try:
#         # Get Json Data from Client Side
#         data = request.get_json()
        
#         # Ensure required fields 
#         required_fields = [
#             "user_ip",
#             "user_name",
#             "window_title",
#             "process_name",
#             "timestamp",
#             "cpu_usage",
#             "ram_usage",
#             "duration"
#         ]
#         for field in required_fields:
#             if field not in data:
#                 return jsonify({
#                     "error": f"Missing Field : {field}"
#                 }), 400
            
#         # timestamp to Datetime format
#         data['timestamp'] = datetime.fromisoformat(data["timestamp"])
        
#         # data insertion
#         logs_col.insert_one(data)
        
#         return jsonify({"message":"Usage data logged successfully"}), 201
#     except Exception as e:
#         return jsonify({"error":f"Failed to store data -- {str(e)}"}), 500 
    
# if __name__ == "__main__":
#     app.run(host = "0.0.0.0", port = 8000)
    
# ## ------------------------- Version 1 - server side -----------