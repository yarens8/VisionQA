import { useEffect, useState } from 'react';
import { AlertCircle, BarChart3, CheckCircle2, Code2, DatabaseZap, FileArchive, History, Loader2, Sparkles, UploadCloud, X } from 'lucide-react';

import { api, DatasetAnalysisResponse, DatasetHistoryItem, DatasetTicket } from '../services/api';

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
    const [ticketLoading, setTicketLoading] = useState<'jira' | null>(null);
    const [ticket, setTicket] = useState<DatasetTicket | null>(null);
    const [historyItems, setHistoryItems] = useState<DatasetHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);

    const loadHistory = async () => {
        setHistoryLoading(true);
        try {
            const items = await api.getDatasetHistory(6);
            setHistoryItems(items);
        } catch (error) {
            console.error('Dataset history yuklenemedi:', error);
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        loadHistory();
    }, []);

    const handleAnalyze = async () => {
        setLoading(true);
        setNotice(null);
        try {
            const parsed = JSON.parse(payload);
            const analysis = await api.analyzeDataset(parsed);
            setResult(analysis);
            setTicket(null);
            await loadHistory();
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
            setTicket(null);
            await loadHistory();
            setNotice({ type: 'success', message: 'ZIP dataset analizi tamamlandi.' });
        } catch (error: any) {
            setNotice({ type: 'error', message: getErrorMessage(error) });
            setResult(null);
        } finally {
            setLoading(false);
        }
    };

    const openHistoryRecord = async (recordId: number) => {
        setLoading(true);
        setNotice(null);
        try {
            const detail = await api.getDatasetHistoryDetail(recordId);
            setResult(detail.analysis);
            setTicket(null);
            setNotice({ type: 'success', message: 'Kaydedilen dataset analizi acildi.' });
        } catch (error: any) {
            setNotice({ type: 'error', message: getErrorMessage(error) });
        } finally {
            setLoading(false);
        }
    };

    const handleCreateDatasetTicket = async () => {
        if (!result) return;
        setTicketLoading('jira');
        setNotice(null);
        try {
            const response = await api.createDatasetJiraTicket(result);
            setTicket(response.ticket);
            setNotice({ type: 'success', message: response.message });
        } catch (error: any) {
            setNotice({ type: 'error', message: getErrorMessage(error) });
        } finally {
            setTicketLoading(null);
        }
    };

    const historySection = (
        <section className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
            <div className="flex items-center justify-between gap-4">
                <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">History</div>
                    <h2 className="mt-2 flex items-center gap-3 text-xl font-semibold text-white">
                        <History className="h-5 w-5 text-amber-300" />
                        Kaydedilen Dataset Analizleri
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                        Yaptigin JSON ve ZIP analizleri burada saklanir. Tiklayip tekrar acabilirsin.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={loadHistory}
                    className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-300 transition hover:border-slate-500"
                >
                    Yenile
                </button>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
                {historyItems.length ? historyItems.map((item) => (
                    <button
                        key={item.id}
                        type="button"
                        onClick={() => openHistoryRecord(item.id)}
                        className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 text-left transition hover:border-amber-500/40 focus:outline-none focus:ring-2 focus:ring-amber-500/30"
                    >
                        <div className="border-b border-slate-800 bg-slate-950 p-4">
                            <div className="flex items-start justify-between gap-4">
                                <div className="min-w-0">
                                    <div className="truncate text-sm font-semibold text-white">
                                        {item.source_label ?? item.dataset_name}
                                    </div>
                                    <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                                        {item.source_type.toUpperCase()} dataset analizi
                                    </div>
                                </div>
                                <div className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-medium text-amber-200">
                                    {item.quality_grade}
                                </div>
                            </div>
                        </div>
                        <div className="p-4">
                            <div className="grid grid-cols-3 gap-2 text-center">
                                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                    <div className="text-lg font-black text-white">{item.overall_score}</div>
                                    <div className="mt-1 text-[10px] uppercase tracking-widest text-slate-500">Score</div>
                                </div>
                                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                    <div className="text-lg font-black text-red-200">{item.findings_count}</div>
                                    <div className="mt-1 text-[10px] uppercase tracking-widest text-slate-500">Findings</div>
                                </div>
                                <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                    <div className="text-lg font-black text-amber-200">{item.detail_errors_count}</div>
                                    <div className="mt-1 text-[10px] uppercase tracking-widest text-slate-500">Errors</div>
                                </div>
                            </div>
                            <div className="mt-4 flex items-center justify-between gap-3 text-xs text-slate-500">
                                <span>{item.total_records} records</span>
                                <span>{new Date(item.created_at).toLocaleString('tr-TR')}</span>
                            </div>
                        </div>
                    </button>
                )) : (
                    <div className="col-span-full rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-8 text-center text-sm text-slate-500">
                        {historyLoading ? 'Kaydedilen dataset analizleri yukleniyor...' : 'Henuz kaydedilmis dataset analizi yok.'}
                    </div>
                )}
            </div>
        </section>
    );

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

            {notice && (
                <div className={`flex max-w-5xl items-start gap-3 rounded-xl border px-4 py-3 ${notice.type === 'error' ? 'border-red-500/30 bg-red-500/10 text-red-100' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100'}`}>
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

            <div className={`grid gap-6 items-start ${result ? 'xl:grid-cols-[minmax(360px,0.72fr)_minmax(0,1.45fr)]' : 'xl:grid-cols-[1.1fr_0.9fr]'}`}>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 shadow-2xl shadow-slate-950/20">
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
                    {result?.source_artifact && (
                        <div className="mt-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-100">
                            <p className="font-bold">Kaynak kaydedildi</p>
                            <p className="mt-1 break-all text-emerald-100/80">{result.source_artifact.path}</p>
                            <p className="mt-1 text-emerald-100/60">{Math.round(result.source_artifact.size_bytes / 1024)} KB • {result.source_artifact.sha256.slice(0, 12)}</p>
                        </div>
                    )}
                </div>

                {result && (
                    <div className="min-w-0 space-y-6">
                        <div className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-900">
                            <div className="flex flex-col gap-4 border-b border-slate-800 p-5 sm:flex-row sm:items-center sm:justify-between">
                                <div className="min-w-0">
                                    <p className="text-white font-semibold">Dataset Ticket Actions</p>
                                    <p className="mt-1 text-xs text-slate-500">Ticket içerigi bu analizde üretilen gerçek finding, validator error ve coverage sinyallerinden olusur.</p>
                                </div>
                                <div className="flex shrink-0 gap-3">
                                    <button
                                        type="button"
                                        onClick={handleCreateDatasetTicket}
                                        disabled={ticketLoading !== null}
                                        className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-blue-500/30 bg-blue-500/15 px-4 text-xs font-black uppercase tracking-widest text-blue-200 transition hover:bg-blue-500/25 disabled:opacity-50"
                                    >
                                        {ticketLoading === 'jira' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                                        Jira Ticket Aç
                                    </button>
                                </div>
                            </div>
                            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                            </div>
                            {ticket && (
                                <div className="m-5 rounded-2xl border border-slate-700 bg-slate-950 p-4">
                                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                                        <div className="min-w-0">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <span className={`rounded-md px-2 py-1 text-[10px] font-black uppercase tracking-widest ${ticket.provider === 'jira' ? 'bg-blue-500/15 text-blue-200' : 'bg-purple-500/15 text-purple-200'}`}>
                                                    {ticket.provider}
                                                </span>
                                                <span className="text-[10px] font-mono text-slate-500">{ticket.ticket_key}</span>
                                                <span className="rounded-md border border-amber-500/20 bg-amber-500/10 px-2 py-1 text-[10px] font-black uppercase tracking-widest text-amber-200">
                                                    {ticket.priority}
                                                </span>
                                            </div>
                                            <p className="mt-3 break-words text-sm font-black text-white">{ticket.title}</p>
                                            <p className="mt-2 text-xs leading-5 text-slate-400">{ticket.description}</p>
                                        </div>
                                        <div className="grid shrink-0 grid-cols-2 gap-2 text-right text-xs text-slate-400">
                                            <span>Findings: {ticket.summary.findings_count}</span>
                                            <span>Errors: {ticket.summary.detail_errors_count}</span>
                                            <span>Score: {ticket.overall_score}</span>
                                            <span>Grade: {ticket.quality_grade}</span>
                                        </div>
                                    </div>
                                    <div className="mt-4 grid max-h-[440px] gap-3 overflow-y-auto pr-1 xl:grid-cols-2">
                                        {ticket.work_items.map((item, index) => (
                                            <div key={`${item.source}-${index}`} className={`min-w-0 rounded-xl border p-4 ${severityClasses[item.severity] ?? 'border-slate-700 bg-slate-900 text-slate-200'}`}>
                                                <div className="flex items-center justify-between gap-3">
                                                    <p className="min-w-0 break-words text-sm font-bold">{item.title}</p>
                                                    <span className="shrink-0 rounded-full border border-current/30 px-2 py-1 text-[10px] uppercase tracking-[0.16em]">{item.source}</span>
                                                </div>
                                                <p className="mt-2 break-words text-xs leading-5">{item.description}</p>
                                                <p className="mt-2 break-words text-[11px] opacity-80">Kanıt: {item.evidence}</p>
                                                <p className="mt-2 break-words text-[11px] opacity-80">Öneri: {item.recommendation}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

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

            {historySection}

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

                    <div className="grid items-start gap-6 xl:grid-cols-2">
                        <div className="flex h-[620px] flex-col rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <div className="flex shrink-0 items-center justify-between gap-3">
                                <p className="text-white font-semibold">Dataset Findings</p>
                                <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300">{result.findings.length}</span>
                            </div>
                            <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-2">
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
                            <div className="flex h-[620px] flex-col rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <div className="flex shrink-0 items-center justify-between gap-3">
                                    <p className="text-white font-semibold">Detailed Validator Errors</p>
                                    <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300">{result.detail_errors.length}</span>
                                </div>
                                <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-2">
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
