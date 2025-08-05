import pytest
from unittest.mock import patch, MagicMock
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

# -------------------
# Test MongoDB Connection
# -------------------
@patch("app.mongo_client")
def test_mongo_connection(mock_mongo_client):
    assert app.mongo_db.name == "monitoringsystem"
    assert app.mongo_col.name == "app_usage_logs_2"

# -------------------
# Test Milvus Connection
# -------------------
@patch("app.connections.connect")
def test_milvus_connection(mock_connect):
    mock_connect.return_value = None
    connections.connect("default", host="localhost", port="19530")
    mock_connect.assert_called_with("default", host="localhost", port="19530")

# -------------------
# Test Insertion API
# -------------------
@patch("app.mongo_col.insert_one")
@patch("app.model.encode")
@patch("app.milvus_col.insert")
@patch("app.milvus_col.flush")
@patch("app.milvus_col.has_index", return_value=False)
@patch("app.milvus_col.create_index")
@patch("app.milvus_col.load")
@patch("app.milvus_col.query")
def test_log_usage_data(
    mock_query, mock_load, mock_create_index, mock_has_index, mock_flush,
    mock_insert, mock_encode, mock_insert_one, client
):
    mock_encode.return_value = [0.1] * 384
    mock_insert.return_value.primary_keys = [12345]
    mock_query.return_value = [{"id": 12345, "vector": [0.1] * 384}]
    
    payload = {
        "user_ip": "127.0.0.1",
        "user_name": "tester",
        "window_title": "Google Chrome",
        "process_name": "chrome.exe",
        "timestamp": "2024-05-01T10:00:00",
        "cpu_usage": 12.5,
        "ram_usage": 50.0,
        "duration": 300
    }

    response = client.post("/api/usage", json=payload)
    assert response.status_code == 201
    assert "Usage data logged" in response.get_json()["message"]

# -------------------
# Test Search API
# -------------------
@patch("app.model.encode")
@patch("app.milvus_col.search")
@patch("app.mongo_col.find")
@patch("app.milvus_col.has_index", return_value=True)
@patch("app.milvus_col.num_entities", new_callable=lambda: 1)
@patch("app.milvus_col.load")
def test_search_logs(
    mock_load, mock_num_entities, mock_has_index,
    mock_find, mock_search, mock_encode, client
):
    mock_encode.return_value = [0.1] * 384
    mock_search.return_value = [[MagicMock(id=12345, distance=0.05)]]
    mock_find.return_value = [{
        "user_ip": "127.0.0.1",
        "user_name": "tester",
        "window_title": "Google Chrome",
        "process_name": "chrome.exe",
        "milvus_id": 12345
    }]

    response = client.get("/api/search?query=chrome")
    data = response.get_json()
    assert response.status_code == 200
    assert data["matched_ids"] == [12345]
    assert len(data["results"]) == 1
