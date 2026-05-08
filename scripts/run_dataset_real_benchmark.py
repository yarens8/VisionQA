import csv
import json
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
DATASETS_DIR = ROOT / "benchmark_dataset" / "extracted"
RESULTS_DIR = ROOT / "benchmark_results"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"

sys.path.append(str(BACKEND_DIR))

from routers.dataset_router import analyze_dataset  # noqa: E402
from schemas import DatasetAnalyzeRequest, DatasetRecord  # noqa: E402


def _clone(records: list[dict]) -> list[dict]:
    return [deepcopy(record) for record in records]


def _sorted_files(path: Path, patterns: tuple[str, ...]) -> list[Path]:
    items: list[Path] = []
    for pattern in patterns:
        items.extend(path.glob(pattern))
    return sorted(items)


def _to_dataset_records(records: list[dict]) -> list[DatasetRecord]:
    return [DatasetRecord(**record) for record in records]


def _assign_split(records: list[dict], train_count: int, val_count: int) -> list[dict]:
    cloned = _clone(records)
    for index, record in enumerate(cloned):
        if index < train_count:
            record["split"] = "train"
        elif index < train_count + val_count:
            record["split"] = "val"
        else:
            record["split"] = "test"
    return cloned


def _pick_grouped(records: list[dict], per_label: int, max_labels: int | None = None) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        label = (record.get("label") or "unlabeled").strip().lower()
        grouped[label].append(record)

    selected: list[dict] = []
    labels = sorted(grouped)
    if max_labels is not None:
        labels = labels[:max_labels]
    for label in labels:
        selected.extend(_clone(grouped[label][:per_label]))
    return selected


def _bbox_from_pascal(obj: ET.Element) -> list[float]:
    box = obj.find("bndbox")
    xmin = int(float(box.findtext("xmin", "0")))
    ymin = int(float(box.findtext("ymin", "0")))
    xmax = int(float(box.findtext("xmax", "0")))
    ymax = int(float(box.findtext("ymax", "0")))
    return [xmin, ymin, xmax - xmin, ymax - ymin]


def _parse_pascal_voc_dataset(dataset_dir: Path, id_prefix: str) -> list[dict]:
    annotations_dir = dataset_dir / "annotations"
    records: list[dict] = []
    for index, xml_path in enumerate(sorted(annotations_dir.glob("*.xml")), start=1):
        root = ET.parse(xml_path).getroot()
        width = int(root.findtext("./size/width", "0"))
        height = int(root.findtext("./size/height", "0"))
        filename = root.findtext("filename", xml_path.stem)
        objects = root.findall("object")
        annotations = []
        for obj in objects:
            annotations.append(
                {
                    "label": obj.findtext("name", "").strip(),
                    "bbox": _bbox_from_pascal(obj),
                }
            )
        records.append(
            {
                "id": f"{id_prefix}-{index}",
                "split": "unspecified",
                "label": annotations[0]["label"] if annotations else "",
                "text": "",
                "image_name": filename,
                "width": width,
                "height": height,
                "annotations": annotations,
                "metadata": {"source_dataset": id_prefix, "xml_file": xml_path.name},
            }
        )
    return records


def _parse_rice_dataset(dataset_dir: Path) -> list[dict]:
    records: list[dict] = []
    class_dirs = [path for path in sorted(dataset_dir.iterdir()) if path.is_dir()]
    for class_dir in class_dirs:
        for index, image_path in enumerate(_sorted_files(class_dir, ("*.jpg", "*.jpeg", "*.png")), start=1):
            records.append(
                {
                    "id": f"rice-{class_dir.name.lower()}-{index}",
                    "split": "unspecified",
                    "label": class_dir.name.lower(),
                    "text": "",
                    "image_name": f"{class_dir.name}/{image_path.name}",
                    "width": None,
                    "height": None,
                    "annotations": [],
                    "metadata": {"source_dataset": "rice", "class_name": class_dir.name},
                }
            )
    return records


def _parse_ocr_receipts_dataset(dataset_dir: Path) -> list[dict]:
    csv_rows: list[dict] = []
    with (dataset_dir / "receipts.csv").open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        csv_rows.extend(reader)

    root = ET.parse(dataset_dir / "annotations.xml").getroot()
    image_map: dict[str, dict] = {}
    for image in root.findall("image"):
        image_name = image.get("name", "")
        width = int(float(image.get("width", "0") or 0))
        height = int(float(image.get("height", "0") or 0))
        annotations = []
        text_fragments: list[str] = []
        primary_label = ""
        for child in list(image):
            label = (child.get("label") or "").strip().lower()
            if not primary_label and label:
                primary_label = label
            if child.tag == "box":
                xtl = float(child.get("xtl", "0"))
                ytl = float(child.get("ytl", "0"))
                xbr = float(child.get("xbr", "0"))
                ybr = float(child.get("ybr", "0"))
                annotations.append({"label": label, "bbox": [xtl, ytl, xbr - xtl, ybr - ytl]})
                for attr in child.findall("attribute"):
                    if (attr.text or "").strip():
                        text_fragments.append(attr.text.strip())
            elif child.tag == "polygon":
                points = []
                for point in (child.get("points", "") or "").split(";"):
                    if not point.strip():
                        continue
                    x_value, y_value = point.split(",")
                    points.append((float(x_value), float(y_value)))
                if points:
                    xs = [value[0] for value in points]
                    ys = [value[1] for value in points]
                    annotations.append(
                        {
                            "label": label,
                            "bbox": [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)],
                        }
                    )
            elif child.tag == "tag" and label:
                annotations.append({"label": label, "bbox": None})
        image_map[image_name] = {
            "width": width,
            "height": height,
            "label": primary_label or "receipt",
            "text": " | ".join(text_fragments[:3]),
            "annotations": annotations,
        }

    records: list[dict] = []
    for row in csv_rows:
        image_name = row["image_name"].replace("images/", "", 1)
        parsed = image_map.get(image_name, {})
        records.append(
            {
                "id": f"ocr-{row['image_id']}",
                "split": "unspecified",
                "label": parsed.get("label", "receipt"),
                "text": parsed.get("text", ""),
                "image_name": row["image_name"],
                "width": parsed.get("width"),
                "height": parsed.get("height"),
                "annotations": parsed.get("annotations", []),
                "metadata": {"source_dataset": "ocr_receipts"},
            }
        )
    return records


def _parse_yolo_dataset(dataset_dir: Path, id_prefix: str) -> list[dict]:
    labels_root = dataset_dir / "Final Data" / "labels"
    images_root = dataset_dir / "Final Data" / "images"
    records: list[dict] = []
    for split_dir in sorted(path for path in labels_root.iterdir() if path.is_dir()):
        split_name = split_dir.name.lower()
        for index, label_path in enumerate(sorted(split_dir.glob("*.txt")), start=1):
            annotations = []
            first_label = ""
            for line in label_path.read_text(encoding="utf-8").splitlines():
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                class_id = parts[0]
                bbox = [float(value) for value in parts[1:5]]
                annotations.append({"label": class_id, "bbox": bbox})
                if not first_label:
                    first_label = class_id
            image_name = ""
            for extension in (".jpg", ".jpeg", ".png"):
                candidate = images_root / split_name / f"{label_path.stem}{extension}"
                if candidate.exists():
                    image_name = str(candidate.relative_to(dataset_dir / "Final Data")).replace("\\", "/")
                    break
            records.append(
                {
                    "id": f"{id_prefix}-{split_name}-{index}",
                    "split": split_name,
                    "label": first_label,
                    "text": "",
                    "image_name": image_name or f"images/{split_name}/{label_path.stem}",
                    "width": None,
                    "height": None,
                    "annotations": annotations,
                    "metadata": {"source_dataset": id_prefix, "label_file": label_path.name},
                }
            )
    return records


def _build_benchmark_cases(parsed: dict[str, list[dict]]) -> list[dict]:
    rice = parsed["rice"]
    car_license = parsed["car_license"]
    road_sign = parsed["road_sign"]
    ocr_receipts = parsed["ocr_receipts"]
    recyclable = parsed["recyclable_images"]

    cases: list[dict] = []

    rice_clean = _assign_split(_pick_grouped(rice, per_label=10, max_labels=5), train_count=35, val_count=10)
    cases.append(
        {
            "id": "dataset-01",
            "name": "rice-clean-balanced",
            "dataset_name": "Rice Clean Balanced",
            "source_datasets": ["rice"],
            "expected_has_issue": False,
            "expected_categories": [],
            "records": rice_clean,
        }
    )

    rice_issue = _pick_grouped(rice, per_label=1, max_labels=2)
    rice_issue = _clone([record for record in rice if record["label"] == "arborio"][:42] + rice_issue)
    rice_issue = _assign_split(rice_issue, train_count=43, val_count=2)
    rice_issue[0]["label"] = ""
    rice_issue.append(deepcopy(rice_issue[1]))
    cases.append(
        {
            "id": "dataset-02",
            "name": "rice-imbalance-missing-duplicate",
            "dataset_name": "Rice Imbalance Duplicate",
            "source_datasets": ["rice"],
            "expected_has_issue": True,
            "expected_categories": ["missing-label", "class-imbalance", "rare-class", "split-balance", "duplicate-signal"],
            "records": rice_issue,
        }
    )

    car_clean = _assign_split(_clone(car_license[:36]), train_count=24, val_count=6)
    cases.append(
        {
            "id": "dataset-03",
            "name": "car-license-clean",
            "dataset_name": "Car License Clean",
            "source_datasets": ["car_license"],
            "expected_has_issue": False,
            "expected_categories": [],
            "records": car_clean,
        }
    )

    car_issue = _assign_split(_clone(car_license[:24]), train_count=16, val_count=4)
    car_issue[0]["annotations"][0]["bbox"] = [12, 12, 30]
    car_issue[1]["annotations"][0]["bbox"] = [-5, 10, 25, 20]
    car_issue[2]["width"] = 0
    cases.append(
        {
            "id": "dataset-04",
            "name": "car-license-broken-annotations",
            "dataset_name": "Car License Broken Annotation",
            "source_datasets": ["car_license"],
            "expected_has_issue": True,
            "expected_categories": ["annotation-health", "broken-record"],
            "records": car_issue,
        }
    )

    road_clean = _assign_split(_pick_grouped(road_sign, per_label=6, max_labels=4), train_count=16, val_count=4)
    cases.append(
        {
            "id": "dataset-05",
            "name": "road-sign-clean",
            "dataset_name": "Road Sign Clean",
            "source_datasets": ["road_sign"],
            "expected_has_issue": False,
            "expected_categories": [],
            "records": road_clean,
        }
    )

    grouped_road: dict[str, list[dict]] = defaultdict(list)
    for record in road_sign:
        grouped_road[record["label"]].append(record)
    major_label = max(grouped_road, key=lambda key: len(grouped_road[key]))
    minor_labels = [label for label in sorted(grouped_road) if label != major_label][:2]
    road_issue = _clone(grouped_road[major_label][:42])
    for label in minor_labels:
        road_issue.extend(_clone(grouped_road[label][:2]))
    road_issue = _assign_split(road_issue, train_count=43, val_count=2)
    road_issue.append(deepcopy(road_issue[0]))
    cases.append(
        {
            "id": "dataset-06",
            "name": "road-sign-imbalance-duplicate",
            "dataset_name": "Road Sign Imbalance Duplicate",
            "source_datasets": ["road_sign"],
            "expected_has_issue": True,
            "expected_categories": ["class-imbalance", "rare-class", "split-balance", "duplicate-signal"],
            "records": road_issue,
        }
    )

    ocr_clean = _assign_split(_clone(ocr_receipts), train_count=14, val_count=3)
    cases.append(
        {
            "id": "dataset-07",
            "name": "ocr-receipts-clean",
            "dataset_name": "OCR Receipts Clean",
            "source_datasets": ["ocr_receipts"],
            "expected_has_issue": False,
            "expected_categories": [],
            "records": ocr_clean,
        }
    )

    ocr_issue = _assign_split(_clone(ocr_receipts), train_count=17, val_count=2)
    ocr_issue[0]["text"] = "istanbul market"
    ocr_issue[0]["label"] = "shop"
    ocr_issue[1]["text"] = "istanbul market"
    ocr_issue[1]["label"] = "total"
    ocr_issue[2]["label"] = ""
    ocr_issue[3]["width"] = 0
    cases.append(
        {
            "id": "dataset-08",
            "name": "ocr-receipts-consistency-break",
            "dataset_name": "OCR Receipts Consistency Break",
            "source_datasets": ["ocr_receipts"],
            "expected_has_issue": True,
            "expected_categories": ["label-consistency", "missing-label", "broken-record", "split-balance", "class-imbalance", "rare-class"],
            "records": ocr_issue,
        }
    )

    recyclable_clean = _assign_split(_pick_grouped(recyclable, per_label=8, max_labels=4), train_count=22, val_count=5)
    cases.append(
        {
            "id": "dataset-09",
            "name": "recyclable-clean",
            "dataset_name": "Recyclable Clean",
            "source_datasets": ["recyclable_images"],
            "expected_has_issue": False,
            "expected_categories": [],
            "records": recyclable_clean,
        }
    )

    recyclable_issue = _clone(recyclable[:30])
    recyclable_issue = _assign_split(recyclable_issue, train_count=28, val_count=1)
    recyclable_issue[0]["annotations"][0]["bbox"] = [0.4, 0.5, 0.2]
    recyclable_issue.append(deepcopy(recyclable_issue[1]))
    cases.append(
        {
            "id": "dataset-10",
            "name": "recyclable-broken-duplicate",
            "dataset_name": "Recyclable Broken Duplicate",
            "source_datasets": ["recyclable_images"],
            "expected_has_issue": True,
            "expected_categories": ["annotation-health", "duplicate-signal", "split-balance", "class-imbalance", "rare-class"],
            "records": recyclable_issue,
        }
    )

    return cases


def _analyze_case(case: dict) -> dict:
    started = time.perf_counter()
    request = DatasetAnalyzeRequest(
        dataset_name=case["dataset_name"],
        records=_to_dataset_records(case["records"]),
    )
    response = analyze_dataset(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    categories = sorted({item.category for item in response.findings})
    expected_categories = sorted(case["expected_categories"])
    expected_has_issue = bool(case["expected_has_issue"])
    predicted_has_issue = len(categories) > 0

    matched_expected = sum(1 for category in expected_categories if category in categories)
    missing_expected = [category for category in expected_categories if category not in categories]
    unexpected_detected = [category for category in categories if category not in expected_categories]
    category_match = categories == expected_categories if not expected_categories else not missing_expected

    return {
        "id": case["id"],
        "name": case["name"],
        "dataset_name": case["dataset_name"],
        "source_datasets": case["source_datasets"],
        "record_count": len(case["records"]),
        "expected_has_issue": expected_has_issue,
        "predicted_has_issue": predicted_has_issue,
        "expected_categories": expected_categories,
        "detected_categories": categories,
        "missing_expected_categories": missing_expected,
        "unexpected_detected_categories": unexpected_detected,
        "category_match": category_match,
        "matched_expected_categories": matched_expected,
        "elapsed_ms": elapsed_ms,
        "overall_score": response.overall_score,
        "quality_grade": response.quality_grade,
        "findings_count": len(response.findings),
        "overview": response.overview,
        "execution_mode": "direct",
    }


def _analyze_case_via_api(base_url: str, case: dict) -> dict:
    started = time.perf_counter()
    response = requests.post(
        f"{base_url}/dataset/analyze",
        json={
            "dataset_name": case["dataset_name"],
            "records": case["records"],
        },
        timeout=180,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.raise_for_status()
    payload = response.json()
    categories = sorted({item["category"] for item in payload.get("findings", [])})
    expected_categories = sorted(case["expected_categories"])
    expected_has_issue = bool(case["expected_has_issue"])
    predicted_has_issue = len(categories) > 0

    matched_expected = sum(1 for category in expected_categories if category in categories)
    missing_expected = [category for category in expected_categories if category not in categories]
    unexpected_detected = [category for category in categories if category not in expected_categories]
    category_match = categories == expected_categories if not expected_categories else not missing_expected

    return {
        "id": case["id"],
        "name": case["name"],
        "dataset_name": case["dataset_name"],
        "source_datasets": case["source_datasets"],
        "record_count": len(case["records"]),
        "expected_has_issue": expected_has_issue,
        "predicted_has_issue": predicted_has_issue,
        "expected_categories": expected_categories,
        "detected_categories": categories,
        "missing_expected_categories": missing_expected,
        "unexpected_detected_categories": unexpected_detected,
        "category_match": category_match,
        "matched_expected_categories": matched_expected,
        "elapsed_ms": elapsed_ms,
        "overall_score": payload.get("overall_score"),
        "quality_grade": payload.get("quality_grade"),
        "findings_count": len(payload.get("findings", [])),
        "overview": payload.get("overview", ""),
        "execution_mode": "api",
    }


def _compute_metrics(results: list[dict]) -> dict:
    tp = fp = fn = tn = 0
    total_expected_categories = 0
    matched_categories = 0
    exact_case_matches = 0
    for item in results:
        expected = item["expected_has_issue"]
        predicted = item["predicted_has_issue"]
        if expected and predicted:
            tp += 1
        elif not expected and predicted:
            fp += 1
        elif expected and not predicted:
            fn += 1
        else:
            tn += 1

        total_expected_categories += len(item["expected_categories"])
        matched_categories += item["matched_expected_categories"]
        if not item["expected_categories"]:
            if not item["detected_categories"]:
                exact_case_matches += 1
        elif sorted(item["expected_categories"]) == sorted(item["detected_categories"]):
            exact_case_matches += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    accuracy = (tp + tn) / max(1, len(results))
    category_recall = matched_categories / max(1, total_expected_categories)
    exact_match_rate = exact_case_matches / max(1, len(results))

    return {
        "total_cases": len(results),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "accuracy": round(accuracy, 4),
        "category_recall": round(category_recall, 4),
        "exact_match_rate": round(exact_match_rate, 4),
        "avg_time_ms": round(sum(item["elapsed_ms"] for item in results) / max(1, len(results)), 2),
    }


def _render_markdown(summary: dict, results: list[dict]) -> str:
    lines = [
        "# Dataset Benchmark",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total cases | {summary['total_cases']} |",
        f"| TP | {summary['tp']} |",
        f"| FP | {summary['fp']} |",
        f"| FN | {summary['fn']} |",
        f"| TN | {summary['tn']} |",
        f"| Precision | {summary['precision']} |",
        f"| Recall | {summary['recall']} |",
        f"| Accuracy | {summary['accuracy']} |",
        f"| Category recall | {summary['category_recall']} |",
        f"| Exact case match rate | {summary['exact_match_rate']} |",
        f"| Avg time (ms) | {summary['avg_time_ms']} |",
        "",
        "## Case Results",
        "",
        "| Case | Sources | Records | Expected Categories | Detected Categories | Overall Score | Grade | Time (ms) |",
        "|---|---|---:|---|---|---:|---|---:|",
    ]
    for item in results:
        expected = ", ".join(item["expected_categories"]) if item["expected_categories"] else "none"
        detected = ", ".join(item["detected_categories"]) if item["detected_categories"] else "none"
        sources = ", ".join(item["source_datasets"])
        lines.append(
            f"| {item['name']} | {sources} | {item['record_count']} | {expected} | {detected} | "
            f"{item['overall_score']} | {item['quality_grade']} | {item['elapsed_ms']} |"
        )
    return "\n".join(lines) + "\n"


def _render_paper_table(summary: dict) -> str:
    return "\n".join(
        [
            "# Dataset Benchmark Table",
            "",
            "## Table X. Preliminary Dataset Benchmark Results on Real Extracted Datasets",
            "",
            "| Metric | Result |",
            "|---|---:|",
            f"| Number of benchmark cases | {summary['total_cases']} |",
            f"| Precision | {summary['precision'] * 100:.2f}% |",
            f"| Recall | {summary['recall'] * 100:.2f}% |",
            f"| Accuracy | {summary['accuracy'] * 100:.2f}% |",
            f"| Expected-category recall | {summary['category_recall'] * 100:.2f}% |",
            f"| Exact case match rate | {summary['exact_match_rate'] * 100:.2f}% |",
            f"| Average processing time per case | {summary['avg_time_ms']:.2f} ms |",
            "",
            "Aciklama:",
            "",
            "Dataset modulu; classification, Pascal VOC detection, YOLO detection ve XML/CSV receipt tiplerini kapsayan gercek benchmark subsetleri uzerinde degerlendirildi. Her dataset icin clean ve issue-heavy alt kume olusturularak hem false positive davranisi hem de kalite sinyali yakalama kabiliyeti olculdu.",
            "",
        ]
    )


def _render_paper_csv(summary: dict) -> str:
    return "\n".join(
        [
            "Metric,Result",
            f"Number of benchmark cases,{summary['total_cases']}",
            f"Precision,{summary['precision'] * 100:.2f}%",
            f"Recall,{summary['recall'] * 100:.2f}%",
            f"Accuracy,{summary['accuracy'] * 100:.2f}%",
            f"Expected-category recall,{summary['category_recall'] * 100:.2f}%",
            f"Exact case match rate,{summary['exact_match_rate'] * 100:.2f}%",
            f"Average processing time per case,{summary['avg_time_ms']:.2f} ms",
            "",
        ]
    )


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base_url = DEFAULT_BASE_URL
    parsed = {
        "rice": _parse_rice_dataset(DATASETS_DIR / "rice"),
        "car_license": _parse_pascal_voc_dataset(DATASETS_DIR / "car_license", "car-license"),
        "road_sign": _parse_pascal_voc_dataset(DATASETS_DIR / "road_sign", "road-sign"),
        "ocr_receipts": _parse_ocr_receipts_dataset(DATASETS_DIR / "ocr_receipts"),
        "recyclable_images": _parse_yolo_dataset(DATASETS_DIR / "recyclable_images", "recyclable"),
    }
    cases = _build_benchmark_cases(parsed)
    results = []

    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['name']} ({len(case['records'])} records)")
        try:
            results.append(_analyze_case_via_api(base_url, case))
        except Exception as exc:
            print(f"  API mode failed, falling back to direct mode: {exc}")
            results.append(_analyze_case(case))
        
        # Groq API token ve RPM limitine takılmamak için bekleyelim
        time.sleep(5)

    summary = _compute_metrics(results)
    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_url": base_url,
        "summary": summary,
        "results": results,
        "case_manifest": [
            {
                "id": case["id"],
                "name": case["name"],
                "dataset_name": case["dataset_name"],
                "source_datasets": case["source_datasets"],
                "record_count": len(case["records"]),
                "expected_has_issue": case["expected_has_issue"],
                "expected_categories": case["expected_categories"],
            }
            for case in cases
        ],
    }

    json_path = RESULTS_DIR / "dataset_real_benchmark.json"
    md_path = RESULTS_DIR / "dataset_real_benchmark.md"
    paper_md_path = RESULTS_DIR / "dataset_paper_table.md"
    paper_csv_path = RESULTS_DIR / "dataset_paper_table.csv"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(summary, results), encoding="utf-8")
    paper_md_path.write_text(_render_paper_table(summary), encoding="utf-8")
    paper_csv_path.write_text(_render_paper_csv(summary), encoding="utf-8")

    print(f"\nJSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    print(f"Paper table (md): {paper_md_path}")
    print(f"Paper table (csv): {paper_csv_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
