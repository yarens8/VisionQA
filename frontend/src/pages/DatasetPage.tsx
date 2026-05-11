import { useState } from 'react';
import { AlertCircle, BarChart3, CheckCircle2, Code2, DatabaseZap, FileArchive, Loader2, Sparkles, UploadCloud, X } from 'lucide-react';

import { api, DatasetAnalysisResponse } from '../services/api';

const severityClasses: Record<string, string> = {
    high: 'border-red-500/40 bg-red-500/10 text-red-200',
    medium: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
    low: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
};

const sampleDataset = JSON.stringify(
    {
        dataset_name: 'Sample Vision Dataset',
        records: [
            { id: '1', split: 'train', label: 'cat', text: 'cat sitting', image_name: 'cat-1.jpg', width: 640, height: 480, annotations: [{ label: 'cat', bbox: [20, 30, 180, 160] }] },
            { id: '2', split: 'train', label: 'cat', text: 'cat sitting', image_name: 'cat-1.jpg', width: 640, height: 480, annotations: [{ label: 'cat', bbox: [20, 30, 180, 160] }] },
            { id: '3', split: 'train', label: 'dog', text: 'cat sitting', image_name: 'mixup.jpg', width: 640, height: 480, annotations: [{ label: 'dog', bbox: [20, 20, 120, 100] }] },
            { id: '4', split: 'train', label: '', text: 'bird in sky', image_name: 'bird-1.jpg', width: 640, height: 480, annotations: [] },
            { id: '5', split: 'train', label: 'bird', text: 'bird in sky', image_name: 'bird-2.jpg', width: 0, height: 480, annotations: [{ label: 'bird', bbox: [10, 10, 50, 50] }] },
            { id: '6', split: 'val', label: 'rare-class', text: 'rare object', image_name: 'rare-1.jpg', width: 800, height: 600, annotations: [{ label: 'rare-class', bbox: [40, 40, 120, 90] }] },
        ],
    },
    null,
    2,
);

const getErrorMessage = (error: any) => {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((item) => {
                const path = Array.isArray(item.loc) ? item.loc.join('.') : item.loc;
                return path ? `${path}: ${item.msg}` : item.msg;
            })
            .filter(Boolean)
            .join(' | ');
    }
    if (detail && typeof detail === 'object') return JSON.stringify(detail);
    return error.message;
};

export function DatasetPage() {
    const [payload, setPayload] = useState(sampleDataset);
    const [loading, setLoading] = useState(false);
    const [zipFile, setZipFile] = useState<File | null>(null);
    const [inputMode, setInputMode] = useState<'zip' | 'json'>('zip');
    const [notice, setNotice] = useState<{ type: 'error' | 'success'; message: string } | null>(null);
    const [result, setResult] = useState<DatasetAnalysisResponse | null>(null);

    const handleAnalyze = async () => {
        setLoading(true);
        setNotice(null);
        try {
            const parsed = JSON.parse(payload);
            const analysis = await api.analyzeDataset(parsed);
            setResult(analysis);
            setNotice({ type: 'success', message: 'JSON dataset analizi tamamlandi.' });
        } catch (error: any) {
            setNotice({ type: 'error', message: getErrorMessage(error) });
            setResult(null);
        } finally {
            setLoading(false);
        }
    };

    const handleZipAnalyze = async () => {
        if (!zipFile) {
            setNotice({ type: 'error', message: 'Lutfen once bir ZIP dataset dosyasi sec.' });
            return;
        }
        setLoading(true);
        setNotice(null);
        try {
            const analysis = await api.analyzeDatasetZip(zipFile);
            setResult(analysis);
            setNotice({ type: 'success', message: 'ZIP dataset analizi tamamlandi.' });
        } catch (error: any) {
            setNotice({ type: 'error', message: getErrorMessage(error) });
            setResult(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                    <DatabaseZap className="h-8 w-8 text-amber-400" />
                    Dataset Kalite Modulu
                </h1>
                <p className="mt-2 text-slate-400">
                    Dataset validation, quality score, training risk ve synthetic suggestion analizleri.
                </p>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr] items-start">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-2xl shadow-slate-950/20">
                    {notice && (
                        <div className={`mb-4 flex items-start gap-3 rounded-xl border px-4 py-3 ${notice.type === 'error' ? 'border-red-500/30 bg-red-500/10 text-red-100' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100'}`}>
                            {notice.type === 'error' ? (
                                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                            ) : (
                                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                            )}
                            <p className="min-w-0 flex-1 text-sm leading-5">{notice.message}</p>
                            <button type="button" onClick={() => setNotice(null)} className="rounded-md p-1 text-current/70 transition hover:bg-white/10 hover:text-current">
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                    )}
                    <div className="flex flex-col gap-4 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                            <p className="text-sm font-semibold text-white">Dataset Source</p>
                            <p className="mt-1 text-xs text-slate-500">Annotation paketi veya ham JSON ile kalite analizi.</p>
                        </div>
                        <div className="grid grid-cols-2 rounded-lg border border-slate-800 bg-slate-950 p-1">
                            <button
                                type="button"
                                onClick={() => setInputMode('zip')}
                                className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition ${inputMode === 'zip' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`}
                            >
                                <FileArchive className="h-4 w-4" />
                                ZIP
                            </button>
                            <button
                                type="button"
                                onClick={() => setInputMode('json')}
                                className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition ${inputMode === 'json' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`}
                            >
                                <Code2 className="h-4 w-4" />
                                JSON
                            </button>
                        </div>
                    </div>

                    {inputMode === 'zip' ? (
                        <div className="space-y-4 pt-5">
                            <label className="flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/70 px-6 py-8 text-center transition hover:border-amber-400/70 hover:bg-slate-950">
                                <span className="flex h-12 w-12 items-center justify-center rounded-lg border border-slate-700 bg-slate-900">
                                    <UploadCloud className="h-6 w-6 text-amber-300" />
                                </span>
                                <span className="mt-4 text-sm font-semibold text-white">
                                    {zipFile ? zipFile.name : 'ZIP dataset dosyasi sec'}
                                </span>
                                <span className="mt-2 max-w-md text-xs leading-5 text-slate-500">
                                    JSON/COCO, CSV, Pascal VOC XML veya YOLO label yapisi desteklenir.
                                </span>
                                <input
                                    type="file"
                                    accept=".zip,application/zip,application/x-zip-compressed"
                                    className="hidden"
                                    onChange={(event) => setZipFile(event.target.files?.[0] ?? null)}
                                />
                            </label>
                            <button onClick={handleZipAnalyze} disabled={loading || !zipFile} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-amber-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-400 disabled:opacity-50 sm:w-auto">
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                                ZIP Analiz Et
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-4 pt-5">
                            <div className="flex items-center justify-between gap-3">
                                <p className="text-sm font-semibold text-white">Dataset JSON</p>
                                <p className="text-xs text-slate-500">records[]</p>
                            </div>
                            <textarea
                                value={payload}
                                onChange={(e) => setPayload(e.target.value)}
                                rows={18}
                                className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 font-mono text-sm text-cyan-300 outline-none transition focus:border-cyan-400/60"
                            />
                            <button onClick={handleAnalyze} disabled={loading} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-amber-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-400 disabled:opacity-50 sm:w-auto">
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                                JSON Analiz Et
                            </button>
                        </div>
                    )}
                </div>

                {result && (
                    <div className="space-y-6">
                        <div className="grid gap-4 sm:grid-cols-3">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Overall</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.overall_score}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Grade</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.quality_grade}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Records</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.total_records}</p>
                            </div>
                        </div>

                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">AI Interpretation</p>
                            <p className="mt-3 text-sm text-slate-300">{result.ai_interpretation}</p>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Training Risk Summary</p>
                                <p className="mt-2 text-sm text-slate-300">{result.training_risk_summary}</p>
                            </div>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Dataset → Model Impact</p>
                                <p className="mt-2 text-sm text-slate-300">{result.model_impact_summary}</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {result && (
                <>
                    <div className="grid gap-6 xl:grid-cols-3">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <div className="flex items-center gap-2 text-white font-semibold">
                                <BarChart3 className="h-4 w-4 text-amber-400" />
                                Score Breakdown
                            </div>
                            <div className="mt-4 grid gap-3">
                                {Object.entries(result.score_breakdown).map(([key, value]) => (
                                    <div key={key} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                        <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{key}</p>
                                        <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Class Distribution</p>
                            <div className="mt-4 space-y-3">
                                {result.class_distribution.map((item) => (
                                    <div key={item.label} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="font-semibold text-white">{item.label}</p>
                                            <p className="text-sm text-cyan-300">{item.count} • {(item.ratio * 100).toFixed(1)}%</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Split Health</p>
                            <div className="mt-4 space-y-3">
                                {result.split_health.map((item) => (
                                    <div key={item.split} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="font-semibold text-white">{item.split}</p>
                                            <p className="text-sm text-cyan-300">{item.count} • {(item.ratio * 100).toFixed(1)}%</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Training Risks</p>
                            <div className="mt-4 space-y-3">
                                {result.training_risks.map((item) => (
                                    <div key={item.summary} className={`rounded-2xl border p-4 ${severityClasses[item.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
                                        <p className="font-semibold">{item.summary}</p>
                                        <p className="mt-2 text-xs">{item.impacted_areas.join(' • ')}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Dataset Findings</p>
                            <div className="mt-4 space-y-3">
                                {result.findings.map((finding) => (
                                    <div key={finding.id} className={`rounded-2xl border p-4 ${severityClasses[finding.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="font-semibold">{finding.title}</p>
                                            <span className="rounded-full border border-current/30 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em]">{finding.severity}</span>
                                        </div>
                                        <p className="mt-3 text-sm">{finding.description}</p>
                                        <p className="mt-2 text-xs">Kanit: {finding.evidence}</p>
                                        <p className="mt-2 text-xs">Oneri: {finding.recommendation}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Detailed Validator Errors</p>
                                <div className="mt-4 space-y-3">
                                    {result.detail_errors.length === 0 ? (
                                        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                            Lokalize validator hatasi cikmadi.
                                        </div>
                                    ) : result.detail_errors.map((item) => (
                                        <div key={item.error_id} className={`rounded-2xl border p-4 ${severityClasses[item.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
                                            <div className="flex items-center justify-between gap-3">
                                                <p className="font-semibold">{item.error_type}</p>
                                                <span className="rounded-full border border-current/30 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em]">{item.severity}</span>
                                            </div>
                                            <p className="mt-2 text-sm">{item.message}</p>
                                            <div className="mt-3 grid gap-2 text-xs text-current/80 sm:grid-cols-2">
                                                <p>Image ID: {item.image_id ?? '-'}</p>
                                                <p>Annotation ID: {item.annotation_id ?? '-'}</p>
                                                <p>Field: {item.field}</p>
                                                <p>File: {item.file_name ?? '-'}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Coverage Gaps</p>
                                <div className="mt-4 space-y-3">
                                    {result.coverage_gaps.length === 0 ? (
                                        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                            Belirgin coverage gap sinyali cikmadi.
                                        </div>
                                    ) : result.coverage_gaps.map((item) => (
                                        <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                            <p className="text-sm font-semibold text-white">{item.title}</p>
                                            <p className="mt-2 text-sm text-slate-300">{item.summary}</p>
                                            <p className="mt-2 text-xs text-cyan-300">{item.impacted_labels.join(', ')}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Duplicate Signals</p>
                                <div className="mt-4 space-y-3">
                                    {result.duplicate_signals.length === 0 ? (
                                        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                            Duplicate sinyali cikmadi.
                                        </div>
                                    ) : result.duplicate_signals.map((item) => (
                                        <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                            <p>{item.reason}</p>
                                            <p className="mt-2 text-xs text-cyan-300">{item.record_ids.join(', ')}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Suspicious Label Signals</p>
                                <div className="mt-4 space-y-3">
                                    {result.suspicious_label_signals.length === 0 ? (
                                        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                            Supheli label sinyali cikmadi.
                                        </div>
                                    ) : result.suspicious_label_signals.map((item) => (
                                        <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                            <p className="text-sm font-semibold text-white">{item.record_id}</p>
                                            <p className="mt-2 text-sm text-slate-300">{item.reason}</p>
                                            <p className="mt-2 text-xs text-amber-300">Current label: {item.current_label}</p>
                                            <p className="mt-2 text-xs text-cyan-300">{item.suggested_review}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Synthetic Data Suggestions</p>
                                <div className="mt-4 space-y-3">
                                    {result.synthetic_data_suggestions.map((item) => (
                                        <div key={item} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Collection Targets</p>
                                <div className="mt-4 space-y-3">
                                    {result.collection_targets.length === 0 ? (
                                        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                            Acil collection target cikmadi.
                                        </div>
                                    ) : result.collection_targets.map((item) => (
                                        <div key={`${item.label}-${item.priority}`} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                            <div className="flex items-center justify-between gap-3">
                                                <p className="text-sm font-semibold text-white">{item.label}</p>
                                                <p className="text-xs uppercase tracking-[0.24em] text-amber-300">P{item.priority}</p>
                                            </div>
                                            <p className="mt-2 text-sm text-slate-300">{item.reason}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

export default DatasetPage;
