import json, os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from datetime import datetime
from sentence_transformers import SentenceTransformer

app = Flask(__name__)

# --- Read Configurations 
# Load configuration from JSON
with open("config.json", "r") as f:
    config = json.load(f)


# --- MongoDB Setup
mongo_conf = config["mongodb"]
mongo_client = MongoClient(f"mongodb://{mongo_conf['host']}:{mongo_conf['port']}/?serverSelectionTimeoutMS=3000")
mongo_db = mongo_client[mongo_conf["database"]]
mongo_col = mongo_db[mongo_conf["collection"]]

# --- Milvus Setup
milvus_conf = config["milvus"]
connections.connect("default", host=milvus_conf["host"], port=milvus_conf["port"])
milvus_collection_name = milvus_conf["collection_name"]

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384)  # Using BERT embeddings
]

schema = CollectionSchema(fields, description="App usage log vectors")

if not utility.has_collection(milvus_collection_name):
    Collection(name=milvus_collection_name, schema=schema)


milvus_col = Collection(milvus_collection_name)

# --- Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

@app.route("/api/usage", methods=["POST"])
def log_usage_data():
    try:
        data = request.get_json()

        required_fields = [
            "user_ip", "user_name", "window_title",
            "process_name", "timestamp", "cpu_usage",
            "ram_usage", "duration"
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        # Convert timestamp
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        # Vectorize `window_title` + `process_name`
        text_to_embed = f"{data['window_title']} {data['process_name']}"
        vector = model.encode(text_to_embed).tolist()

        # Insert vector into Milvus
        insert_result = milvus_col.insert([[vector]])

        # Get the auto-generated primary key (milvus_id)
        milvus_id = insert_result.primary_keys[0]
        print(f"Inserted vector with Milvus ID: {milvus_id}")

        # Add Milvus ID to MongoDB entry
        data["milvus_id"] = milvus_id
        mongo_col.insert_one(data)

        # Flush to make sure the data is persisted before querying
        milvus_col.flush()
        print(f"Total entities in collection: {milvus_col.num_entities}")

        # Create index (after inserting data)
        if not milvus_col.has_index():
            milvus_col.create_index(
                field_name="vector",
                index_params={
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
            )

        milvus_col.load()

        # Query the inserted record from Milvus
        results = milvus_col.query(
            expr=f"id == {milvus_id}",
            output_fields=["id", "vector"]
        )

        print("Inserted Record:")
        print(results[0])

        return jsonify({"message": "Usage data logged to Milvus and MongoDB"}), 201

    except Exception as e:
        return jsonify({"error": f"Failed to log data: {str(e)}"}), 500

# ---------

@app.route("/api/search", methods=["GET"])
def search_logs():
    try:
        query = request.args.get("query")
        # top_k = int(request.args.get("top_k", 3))  # default: return top 3 matches

        if not query:
            return jsonify({"error": "Missing 'query' parameter"}), 400

        # Vectorize the search query
        query_vector = model.encode(query).tolist()

        # Check if the collection has data
        if milvus_col.num_entities == 0:
            return jsonify({"error": "No data in Milvus collection"}), 404

        # Create index if not already created
        if not milvus_col.has_index():
            print("Creating index on 'vector' field...")
            milvus_col.create_index(
                field_name="vector",
                index_params={
                    "metric_type": "COSINE",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 128}
                }
            )

        # Load the collection into memory
        milvus_col.load()

        # Perform vector search
        results = milvus_col.search(
            data=[query_vector],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=3,
            output_fields=["id"]
        )

        if not results or not results[0]:
            return jsonify({"query": query, "results": [], "message": "No matches found"}), 200

        # Extract matched Milvus IDs
        matched_ids = [int(hit.id) for hit in results[0]]

        # Log matched scores (optional debug)
        for hit in results[0]:
            print(f"[Match] ID: {hit.id}, Score: {hit.distance:.4f}")

        # Query MongoDB for matching records
        mongo_results = list(mongo_col.find(
            {"milvus_id": {"$in": matched_ids}},
            {"_id": 0}
        ))

        return jsonify({
            "query": query,
            "matched_ids": matched_ids,
            "results": mongo_results
        }), 200

    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500
# #------



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
 