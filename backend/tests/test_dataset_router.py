import os
import sys
import json
import zipfile
from io import BytesIO

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


def test_dataset_analysis_accepts_raw_record_list():
    client = TestClient(main.app)
    payload = [
        {"id": "1", "label": "cat", "image_name": "cat.jpg", "width": 640, "height": 480},
        {"id": "2", "label": "", "image_name": "missing.jpg", "width": 640, "height": 480},
    ]

    response = client.post("/dataset/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_name"] == "Uploaded ZIP Dataset"
    assert data["total_records"] == 2


def test_dataset_analysis_accepts_coco_payload():
    client = TestClient(main.app)
    payload = {
        "info": {"description": "COCO sample"},
        "images": [
            {"id": 1, "file_name": "cat.jpg", "width": 640, "height": 480},
            {"id": 2, "file_name": "dog.jpg", "width": 640, "height": 480},
        ],
        "categories": [
            {"id": 10, "name": "cat"},
            {"id": 20, "name": "dog"},
        ],
        "annotations": [
            {"image_id": 1, "category_id": 10, "bbox": [10, 10, 100, 100]},
            {"image_id": 2, "category_id": 20, "bbox": [20, 20, 120, 100]},
        ],
    }

    response = client.post("/dataset/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_name"] == "COCO sample"
    assert data["total_records"] == 2
    assert {item["label"] for item in data["class_distribution"]} == {"cat", "dog"}


def test_dataset_analysis_reports_localized_coco_errors_and_history():
    client = TestClient(main.app)
    payload = {
        "dataset_name": "COCO localized errors",
        "images": [{"id": 1, "file_name": "bad.jpg", "width": 100, "height": 100}],
        "categories": [{"id": 1, "name": "cat"}],
        "annotations": [{"id": 7, "image_id": 1, "category_id": 999, "bbox": [90, 90, 30, 30]}],
    }

    response = client.post("/dataset/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    error_types = {item["error_type"] for item in data["detail_errors"]}
    assert "invalid_category_id" in error_types
    assert "out_of_bound_bbox" in error_types
    assert any(item["image_id"] == "1" and item["annotation_id"] == "7" for item in data["detail_errors"])

    history_response = client.get("/dataset/history?limit=1")
    assert history_response.status_code == 200
    assert history_response.json()


def test_dataset_analysis_detects_split_leakage_by_image_name():
    client = TestClient(main.app)
    payload = {
        "dataset_name": "Split leakage QA",
        "records": [
            {"id": "1", "split": "train", "label": "cat", "image_name": "same.jpg", "width": 100, "height": 100, "annotations": [{"label": "cat", "bbox": [1, 1, 10, 10]}]},
            {"id": "2", "split": "test", "label": "cat", "image_name": "same.jpg", "width": 100, "height": 100, "annotations": [{"label": "cat", "bbox": [2, 2, 10, 10]}]},
        ],
    }

    response = client.post("/dataset/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "split-leakage" in {item["category"] for item in data["findings"]}
    assert "split_leakage" in {item["error_type"] for item in data["detail_errors"]}


def test_dataset_zip_upload_reads_annotation_and_checks_images():
    client = TestClient(main.app)
    payload = {
        "dataset_name": "ZIP Dataset QA",
        "records": [
            {"id": "1", "label": "cat", "image_name": "cat-1.jpg", "width": 640, "height": 480, "annotations": [{"label": "cat", "bbox": [10, 10, 100, 100]}]},
            {"id": "2", "label": "dog", "image_name": "missing-dog.jpg", "width": 640, "height": 480, "annotations": [{"label": "dog", "bbox": [20, 20, 120, 100]}]},
        ],
    }
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("dataset.json", json.dumps(payload))
        archive.writestr("images/cat-1.jpg", b"fake-image")

    response = client.post(
        "/dataset/upload-analyze",
        files={"file": ("dataset.zip", buffer.getvalue(), "application/zip")},
    )

    assert response.status_code == 200
    data = response.json()
    categories = {item["category"] for item in data["findings"]}
    assert data["dataset_name"] == "ZIP Dataset QA"
    assert data["total_records"] == 2
    assert "missing-image" in categories


def test_dataset_zip_upload_reads_csv_annotations():
    client = TestClient(main.app)
    csv_payload = "\n".join(
        [
            "id,image_name,label,width,height,bbox,split",
            '1,cat.jpg,cat,100,100,"[1, 1, 10, 10]",train',
            '2,dog.jpg,dog,100,100,"[2, 2, 10, 10]",val',
        ]
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("annotations.csv", csv_payload)
        archive.writestr("images/cat.jpg", b"cat")
        archive.writestr("images/dog.jpg", b"dog")

    response = client.post(
        "/dataset/upload-analyze",
        files={"file": ("dataset.zip", buffer.getvalue(), "application/zip")},
    )

    assert response.status_code == 200
    assert response.json()["total_records"] == 2


def test_dataset_zip_upload_reads_pascal_voc_xml():
    client = TestClient(main.app)
    xml_payload = """
    <annotation>
      <filename>cat.jpg</filename>
      <size><width>100</width><height>100</height></size>
      <object><name>cat</name><bndbox><xmin>1</xmin><ymin>2</ymin><xmax>20</xmax><ymax>30</ymax></bndbox></object>
    </annotation>
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("annotations/cat.xml", xml_payload)
        archive.writestr("images/cat.jpg", b"cat")

    response = client.post(
        "/dataset/upload-analyze",
        files={"file": ("dataset.zip", buffer.getvalue(), "application/zip")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 1
    assert data["class_distribution"][0]["label"] == "cat"


def test_dataset_zip_upload_reads_yolo_labels():
    client = TestClient(main.app)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("train/labels/cat.txt", "0 0.5 0.5 0.2 0.2\n")
        archive.writestr("train/images/cat.jpg", b"cat")

    response = client.post(
        "/dataset/upload-analyze",
        files={"file": ("dataset.zip", buffer.getvalue(), "application/zip")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 1
    assert data["split_health"][0]["split"] == "train"
