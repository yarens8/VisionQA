# Dataset Benchmark

## Summary

| Metric | Value |
|---|---:|
| Total cases | 10 |
| TP | 0 |
| FP | 2 |
| FN | 5 |
| TN | 3 |
| Precision | 0.0 |
| Recall | 0.0 |
| Accuracy | 0.3 |
| Category recall | 0.0 |
| Exact case match rate | 0.3 |
| Avg time (ms) | 1100.13 |

## Case Results

| Case | Sources | Records | Expected Categories | Detected Categories | Overall Score | Grade | Time (ms) |
|---|---|---:|---|---|---:|---|---:|
| rice-clean-balanced | rice | 50 | none | broken-record, class-imbalance, missing-label, split-balance | 68 | D | 2204.02 |
| rice-imbalance-missing-duplicate | rice | 45 | class-imbalance, duplicate-signal, missing-label, rare-class, split-balance | none | 80 | B | 1025.86 |
| car-license-clean | car_license | 36 | none | none | 80 | B | 799.99 |
| car-license-broken-annotations | car_license | 24 | annotation-health, broken-record | none | 80 | B | 646.66 |
| road-sign-clean | road_sign | 24 | none | none | 80 | B | 767.72 |
| road-sign-imbalance-duplicate | road_sign | 47 | class-imbalance, duplicate-signal, rare-class, split-balance | none | 80 | B | 887.17 |
| ocr-receipts-clean | ocr_receipts | 20 | none | annotation-health, class-imbalance, missing-label, split-balance | 24 | E | 1933.69 |
| ocr-receipts-consistency-break | ocr_receipts | 20 | broken-record, class-imbalance, label-consistency, missing-label, rare-class, split-balance | none | 80 | B | 846.25 |
| recyclable-clean | recyclable_images | 32 | none | none | 80 | B | 882.06 |
| recyclable-broken-duplicate | recyclable_images | 31 | annotation-health, class-imbalance, duplicate-signal, rare-class, split-balance | none | 80 | B | 1007.93 |
