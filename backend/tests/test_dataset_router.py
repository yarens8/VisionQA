import os
import sys

from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main


def test_dataset_analysis_detects_core_signals():
    client = TestClient(main.app)
    payload = {
        "dataset_name": "Dataset QA",
        "records": [
            {"id": "1", "label": "cat", "text": "same text", "image_name": "a.jpg", "width": 640, "height": 480, "annotations": [{"label": "cat", "bbox": [10, 10, 100, 100]}]},
            {"id": "2", "label": "dog", "text": "same text", "image_name": "b.jpg", "width": 640, "height": 480, "annotations": [{"label": "dog", "bbox": [10, 10, 100, 100]}]},
            {"id": "3", "label": "", "text": "missing label", "image_name": "c.jpg", "width": 640, "height": 480, "annotations": []},
            {"id": "4", "label": "rare", "text": "rare thing", "image_name": "dup.jpg", "width": 640, "height": 480, "annotations": [{"label": "rare", "bbox": [10, 10, 100, 100]}]},
            {"id": "5", "label": "rare", "text": "rare thing", "image_name": "dup.jpg", "width": 640, "height": 480, "annotations": [{"label": "rare", "bbox": [10, 10, 100, 100]}]},
            {"id": "6", "label": "bird", "text": "bird", "image_name": "bad.jpg", "width": 0, "height": 480, "annotations": [{"label": "bird", "bbox": [10, 10, 100, 100]}]},
        ],
    }

    response = client.post("/dataset/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    categories = {item["category"] for item in data["findings"]}
    assert "missing-label" in categories
    assert "label-consistency" in categories
    assert "duplicate-signal" in categories
    assert "broken-record" in categories
    assert data["training_risks"]
    assert "score_breakdown" in data
