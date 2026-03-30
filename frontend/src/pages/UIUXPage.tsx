import { useEffect, useState } from 'react';
import axios from 'axios';
import {
    AlertTriangle,
    CheckCircle2,
    Eye,
    FileImage,
    History,
    Layers3,
    Pencil,
    ScanSearch,
    Sparkles,
    Star,
    Trash2,
    X,
} from 'lucide-react';

import { api, UiuxAnalysisResponse, UiuxHistoryItem } from '../services/api';

function severityBadge(severity: string) {
    if (severity === 'high') return 'border-red-400/40 bg-red-500/10 text-red-200';
    if (severity === 'medium') return 'border-amber-400/40 bg-amber-500/10 text-amber-200';
    if (severity === 'low') return 'border-sky-400/40 bg-sky-500/10 text-sky-200';
    return 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200';
}

function scoreTone(score?: number) {
    if (score === undefined) return 'text-slate-200';
    if (score < 55) return 'text-red-200';
    if (score < 75) return 'text-amber-200';
    return 'text-emerald-200';
}

export function UIUXPage() {
    const [preview, setPreview] = useState<string | null>(null);
    const [analysis, setAnalysis] = useState<UiuxAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedFindingId, setSelectedFindingId] = useState<number | null>(null);
    const [viewMode, setViewMode] = useState<'annotated' | 'attention' | 'source'>('annotated');
    const [historyItems, setHistoryItems] = useState<UiuxHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [renameTarget, setRenameTarget] = useState<UiuxHistoryItem | null>(null);
    const [renameValue, setRenameValue] = useState('');
    const [deleteTarget, setDeleteTarget] = useState<UiuxHistoryItem | null>(null);
    const [historyModalBusy, setHistoryModalBusy] = useState(false);

    const getRequestErrorMessage = (err: unknown, fallback: string) => {
        if (axios.isAxiosError(err)) {
            const detail = err.response?.data?.detail;
            if (typeof detail === 'string' && detail.trim()) return detail;
            if (typeof err.message === 'string' && err.message.trim()) return err.message;
        }
        if (err instanceof Error && err.message.trim()) return err.message;
        return fallback;
    };

    const handleFile = (file: File | null) => {
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            const result = typeof reader.result === 'string' ? reader.result : null;
            setPreview(result);
            setAnalysis(null);
            setError(null);
            setSelectedFindingId(null);
            setViewMode('annotated');
        };
        reader.readAsDataURL(file);
    };

    const loadHistory = async () => {
        setHistoryLoading(true);
        try {
            const items = await api.getUiuxHistory(6);
            setHistoryItems(items);
        } catch (err) {
            console.warn('UI/UX history yuklenemedi:', err);
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        loadHistory();
    }, []);

    const runAnalysis = async () => {
        if (!preview) {
            setError('Once analiz edilecek bir screenshot yukle.');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const result = await api.analyzeUiuxImage(preview, 'web');
            setAnalysis(result);
            setSelectedFindingId(result.findings[0]?.id ?? null);
            await loadHistory();
        } catch (err) {
            setError(getRequestErrorMessage(err, 'UI/UX analizi baslatilamadi.'));
        } finally {
            setLoading(false);
        }
    };

    const openHistoryRecord = async (recordId: number) => {
        setLoading(true);
        setError(null);
        try {
            const detail = await api.getUiuxHistoryDetail(recordId);
            const sourceImage = detail.analysis.artifacts.source_image_base64
                ? `data:image/png;base64,${detail.analysis.artifacts.source_image_base64}`
                : null;
            setPreview(sourceImage);
            setAnalysis(detail.analysis);
            setSelectedFindingId(detail.analysis.findings[0]?.id ?? null);
            setViewMode('annotated');
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Kayitli UI/UX analizi acilamadi.'));
        } finally {
            setLoading(false);
        }
    };

    const openRenameHistoryModal = (item: UiuxHistoryItem) => {
        setRenameTarget(item);
        setRenameValue(item.source_label ?? '');
    };

    const renameHistoryRecord = async () => {
        if (!renameTarget) return;
        try {
            setHistoryModalBusy(true);
            const updatedRecord = await api.updateUiuxHistory(renameTarget.id, { source_label: renameValue });
            setHistoryItems((currentItems) =>
                currentItems.map((item) => (item.id === updatedRecord.id ? updatedRecord : item))
            );
            setRenameTarget(null);
            setRenameValue('');
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Kayit adi guncellenemedi.'));
        } finally {
            setHistoryModalBusy(false);
        }
    };

    const toggleFavoriteHistoryRecord = async (item: UiuxHistoryItem) => {
        try {
            const updatedRecord = await api.updateUiuxHistory(item.id, { is_favorite: !item.is_favorite });
            setHistoryItems((currentItems) =>
                currentItems.map((historyItem) => (historyItem.id === updatedRecord.id ? updatedRecord : historyItem))
            );
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Favori durumu guncellenemedi.'));
        }
    };

    const openDeleteHistoryModal = (item: UiuxHistoryItem) => {
        setDeleteTarget(item);
    };

    const deleteHistoryRecord = async () => {
        if (!deleteTarget) return;
        try {
            setHistoryModalBusy(true);
            const deletedRecordId = deleteTarget.id;
            await api.deleteUiuxHistory(deletedRecordId);
            setHistoryItems((currentItems) =>
                currentItems.filter((historyItem) => historyItem.id !== deletedRecordId)
            );
            setDeleteTarget(null);
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Kayit silinemedi.'));
        } finally {
            setHistoryModalBusy(false);
        }
    };

    const imageSource = analysis
        ? `data:image/png;base64,${
            viewMode === 'annotated'
                ? analysis.artifacts.annotated_image_base64
                : viewMode === 'attention'
                    ? (analysis.artifacts.attention_overlay_image_base64 || analysis.artifacts.annotated_image_base64 || analysis.artifacts.source_image_base64)
                    : analysis.artifacts.source_image_base64
        }`
        : preview;
    const topFindings = analysis?.findings.slice(0, 5) ?? [];
    const selectedFinding = topFindings.find((finding) => finding.id === selectedFindingId) ?? topFindings[0] ?? null;
    const additionalFindings = topFindings.filter((finding) => finding.id !== selectedFinding?.id);

    return (
        <div className="space-y-8">
            <section className="overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950">
                <div className="relative isolate overflow-hidden px-8 py-10 md:px-10">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_36%),radial-gradient(circle_at_bottom_right,_rgba(249,115,22,0.16),_transparent_28%)]" />
                    <div className="relative z-10 flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
                        <div className="max-w-3xl">
                            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.24em] text-cyan-100">
                                <Sparkles className="h-3.5 w-3.5" />
                                4.3 AI UX Critic v1.2
                            </div>
                            <h1 className="mt-4 flex items-center gap-3 text-4xl font-bold tracking-tight text-white">
                                <Layers3 className="h-9 w-9 text-cyan-300" />
                                Screenshot Tabanli UI/UX Denetimi
                            </h1>
                            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-300">
                                Layout, hiyerarsi, spacing, odak netligi ve kullanici surtunmesini screenshot uzerinden yorumlayarak incele.
                            </p>
                        </div>

                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">UX Score</div>
                                <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.ux_score ?? analysis?.overall_score)}`}>{analysis?.ux_score ?? analysis?.overall_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Hierarchy</div>
                                <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.visual_hierarchy_score)}`}>{analysis?.visual_hierarchy_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Friction</div>
                                <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.friction_score)}`}>{analysis?.friction_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Focus</div>
                                <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.focus_score)}`}>{analysis?.focus_score ?? '--'}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <div className="grid items-start gap-8 xl:grid-cols-[1.25fr_0.95fr]">
                <section className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="flex flex-col gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-center md:justify-between">
                        <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Input</div>
                            <h2 className="mt-2 text-xl font-semibold text-white">Screenshot Yukle</h2>
                            <p className="mt-2 text-sm leading-6 text-slate-400">
                                Tek bir ekran goruntusu ile hizalama, spacing ve gorsel tutarlilik sinyallerini uret.
                            </p>
                        </div>
                        <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-slate-500">
                            <FileImage className="h-4 w-4" />
                            Screenshot Sec
                            <input
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={(event) => handleFile(event.target.files?.[0] ?? null)}
                            />
                        </label>
                    </div>

                    <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-dashed border-slate-700 bg-slate-900/50">
                        {imageSource ? (
                            <div className="relative">
                                <img src={imageSource} alt="UI/UX preview" className="w-full object-contain" />
                            </div>
                        ) : (
                            <div className="flex min-h-[360px] flex-col items-center justify-center px-6 text-center">
                                <div className="rounded-full border border-cyan-400/20 bg-cyan-400/10 p-5 text-cyan-200">
                                    <ScanSearch className="h-8 w-8" />
                                </div>
                                <div className="mt-5 text-lg font-semibold text-white">Bir screenshot ekle</div>
                                <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">
                                    Analiz sonrasinda annotated goruntu, secili finding crop preview ve net oneriler ayni ekranda acilacak.
                                </p>
                            </div>
                        )}
                    </div>

                    <div className="mt-5 flex flex-wrap items-center gap-3">
                        <button
                            type="button"
                            onClick={runAnalysis}
                            disabled={loading}
                            className="inline-flex items-center gap-2 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:border-cyan-300/50 hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <Sparkles className="h-4 w-4" />
                            {loading ? 'Analiz ediliyor...' : 'UI/UX Analizini Baslat'}
                        </button>

                        {analysis && (
                            <>
                                <button
                                    type="button"
                                    onClick={() => setViewMode('annotated')}
                                    className={`inline-flex items-center gap-2 rounded-xl border px-4 py-3 text-sm transition ${
                                        viewMode === 'annotated'
                                            ? 'border-cyan-400/30 bg-cyan-400/10 text-cyan-100'
                                            : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500'
                                    }`}
                                >
                                    <Eye className="h-4 w-4" />
                                    Annotated
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setViewMode('attention')}
                                    className={`inline-flex items-center gap-2 rounded-xl border px-4 py-3 text-sm transition ${
                                        viewMode === 'attention'
                                            ? 'border-cyan-400/30 bg-cyan-400/10 text-cyan-100'
                                            : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500'
                                    }`}
                                >
                                    <ScanSearch className="h-4 w-4" />
                                    Odak Akisi
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setViewMode('source')}
                                    className={`inline-flex items-center gap-2 rounded-xl border px-4 py-3 text-sm transition ${
                                        viewMode === 'source'
                                            ? 'border-cyan-400/30 bg-cyan-400/10 text-cyan-100'
                                            : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500'
                                    }`}
                                >
                                    <Eye className="h-4 w-4" />
                                    Temiz Screenshot
                                </button>
                            </>
                        )}
                    </div>

                    {error && (
                        <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                            {error}
                        </div>
                    )}
                </section>

                <section className="space-y-6">
                    <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                        <div className="flex items-center justify-between gap-4">
                            <div>
                                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Summary</div>
                                <h2 className="mt-2 text-xl font-semibold text-white">Standart Cikti</h2>
                            </div>
                            <div className={`rounded-full border px-3 py-1 text-xs font-medium ${analysis?.findings.length ? 'border-amber-400/20 bg-amber-500/10 text-amber-200' : 'border-emerald-400/20 bg-emerald-500/10 text-emerald-200'}`}>
                                {analysis?.findings.length ? `${analysis.findings.length} finding` : 'Temiz ekran'}
                            </div>
                        </div>
                        <p className="mt-4 text-sm leading-6 text-slate-300">
                            {analysis?.overview ?? 'Analiz sonrasinda overall score, finding listesi, crop preview ve oneriler burada gorunur.'}
                        </p>
                        {analysis?.ai_critic_summary ? (
                            <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-4 text-sm leading-6 text-cyan-50">
                                {analysis.ai_critic_summary}
                            </div>
                        ) : null}

                        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Alignment</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.alignment_score)}`}>{analysis?.alignment_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Spacing</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.spacing_consistency_score)}`}>{analysis?.spacing_consistency_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Balance</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.layout_balance_score)}`}>{analysis?.layout_balance_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Readability</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.readability_score)}`}>{analysis?.readability_score ?? '--'}</div>
                            </div>
                        </div>
                        {analysis?.attention_prediction ? (
                            <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Attention Prediction</div>
                                        <div className="mt-2 text-sm font-semibold text-white">
                                            Ilk odak: {analysis.attention_prediction.primary_focus_label}
                                        </div>
                                    </div>
                                    <div className={`text-2xl font-semibold ${scoreTone(analysis.attention_prediction.focus_score)}`}>
                                        %{analysis.attention_prediction.focus_score}
                                    </div>
                                </div>
                                <div className="mt-3 text-sm leading-6 text-slate-300">{analysis.attention_prediction.summary}</div>
                                <div className="mt-3 text-sm text-slate-200">
                                    {analysis.attention_prediction.attention_path.join(' -> ')}
                                </div>
                            </div>
                        ) : null}
                    </article>

                    <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                        <div className="flex items-center gap-3">
                            <div className="rounded-full border border-slate-700 bg-slate-900 p-2 text-slate-200">
                                {selectedFinding ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                            </div>
                            <div>
                                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Preview</div>
                                <h2 className="mt-1 text-xl font-semibold text-white">Secili Finding</h2>
                            </div>
                        </div>

                        {selectedFinding ? (
                            <div className="mt-5">
                                <div className="overflow-hidden rounded-[1.5rem] border border-slate-800 bg-slate-900">
                                    <img
                                        src={`data:image/png;base64,${selectedFinding.crop_image_base64}`}
                                        alt={`Finding ${selectedFinding.id}`}
                                        className="h-56 w-full object-cover"
                                    />
                                </div>
                                <div className="mt-4 flex items-start justify-between gap-4">
                                    <div>
                                        <div className="text-base font-semibold text-white">{selectedFinding.title}</div>
                                        <div className="mt-1 text-sm text-slate-400">
                                            Rol: {selectedFinding.affected_role} • Kategori: {selectedFinding.category}
                                        </div>
                                    </div>
                                    <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(selectedFinding.severity)}`}>
                                        {selectedFinding.severity}
                                    </div>
                                </div>
                                <p className="mt-4 text-sm leading-6 text-slate-300">{selectedFinding.description}</p>
                                <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">AI UX Critic</div>
                                    <div className="mt-3 text-sm leading-6 text-slate-200">
                                        {selectedFinding.ai_critic}
                                    </div>
                                </div>
                                <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-4">
                                    <div className="text-xs uppercase tracking-[0.18em] text-amber-200">Why This Matters</div>
                                    <div className="mt-3 text-sm leading-6 text-amber-50">
                                        {selectedFinding.why_this_matters}
                                    </div>
                                </div>
                                <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-4 text-sm leading-6 text-cyan-50">
                                    {selectedFinding.recommendation}
                                </div>
                            </div>
                        ) : (
                            <div className="mt-5 rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                                Henuz secilecek bir finding yok.
                            </div>
                        )}
                    </article>
                </section>
            </div>

            <section className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
                <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Findings</div>
                            <h2 className="mt-2 text-xl font-semibold text-white">Bulgu Listesi</h2>
                        </div>
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Screenshot tabanli v1</div>
                    </div>

                    <div className="mt-5 space-y-3">
                        {topFindings.length ? topFindings.map((finding) => (
                            <button
                                key={finding.id}
                                type="button"
                                onClick={() => setSelectedFindingId(finding.id)}
                                className={`w-full rounded-2xl border p-4 text-left transition ${
                                    selectedFinding?.id === finding.id
                                        ? 'border-cyan-300 bg-cyan-400/10'
                                        : 'border-slate-800 bg-slate-900 hover:border-slate-700'
                                }`}
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div>
                                        <div className="flex items-center gap-3">
                                            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800 text-sm font-semibold text-slate-100">
                                                {finding.id}
                                            </div>
                                            <div className="text-base font-semibold text-white">{finding.title}</div>
                                        </div>
                                        <div className="mt-2 text-sm leading-6 text-slate-300">{finding.description}</div>
                                    </div>
                                    <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(finding.severity)}`}>
                                        {finding.severity}
                                    </div>
                                </div>
                            </button>
                        )) : (
                            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                                Analiz sonrasi 2-3 anlamli layout finding'i burada listelenecek.
                            </div>
                        )}
                    </div>
                </article>

                <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Recommendations</div>
                    <h2 className="mt-2 text-xl font-semibold text-white">Hizli Iyilestirme Onerileri</h2>

                    <div className="mt-5 space-y-3">
                        {selectedFinding ? (
                            <>
                                <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-4">
                                    <div className="flex items-center justify-between gap-4">
                                        <div className="text-sm font-semibold text-white">Secili bulgu icin ana aksiyon</div>
                                        <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(selectedFinding.severity)}`}>
                                            {selectedFinding.category}
                                        </div>
                                    </div>
                                    <div className="mt-3 text-sm leading-6 text-cyan-50">
                                        {selectedFinding.recommendation}
                                    </div>
                                </div>

                                {additionalFindings.length ? additionalFindings.map((finding) => (
                                    <div key={`recommendation-${finding.id}`} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                        <div className="flex items-center justify-between gap-4">
                                            <div className="text-sm font-medium text-white">{finding.title}</div>
                                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">
                                                #{finding.id}
                                            </div>
                                        </div>
                                        <div className="mt-3 text-sm leading-6 text-slate-200">
                                            {finding.recommendation}
                                        </div>
                                    </div>
                                )) : null}
                            </>
                        ) : (analysis?.recommendations ?? []).length ? (
                            analysis?.recommendations.map((recommendation, index) => (
                                <div key={`${index}-${recommendation}`} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4 text-sm leading-6 text-slate-200">
                                    {recommendation}
                                </div>
                            ))
                        ) : (
                            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                                Analiz sonrasi en onemli UI/UX aksiyonlari burada ozetlenecek.
                            </div>
                        )}
                    </div>
                </article>
            </section>

            <section className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">History</div>
                        <h2 className="mt-2 flex items-center gap-3 text-xl font-semibold text-white">
                            <History className="h-5 w-5 text-cyan-300" />
                            Kaydedilen UI/UX Analizleri
                        </h2>
                        <p className="mt-2 text-sm leading-6 text-slate-400">
                            Yaptigin screenshot analizleri burada saklanir. Tiklayip tekrar acabilirsin.
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
                        <article
                            key={item.id}
                            className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 text-left transition hover:border-slate-700"
                        >
                            <button
                                type="button"
                                onClick={() => openHistoryRecord(item.id)}
                                className="block w-full text-left"
                            >
                                <div className="aspect-[16/9] overflow-hidden border-b border-slate-800 bg-slate-950">
                                    {item.thumbnail_base64 ? (
                                        <img
                                            src={`data:image/png;base64,${item.thumbnail_base64}`}
                                            alt={`UIUX history ${item.id}`}
                                            className="h-full w-full object-cover"
                                        />
                                    ) : (
                                        <div className="flex h-full items-center justify-center text-sm text-slate-500">
                                            Onizleme yok
                                        </div>
                                    )}
                                </div>
                                <div className="p-4">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="min-w-0">
                                            <div className="truncate text-sm font-semibold text-white">
                                                {item.source_label ?? 'Manuel screenshot analizi'}
                                            </div>
                                            <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                                                UI/UX screenshot analizi
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {item.is_favorite && (
                                                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-amber-400/40 bg-amber-500/10 text-amber-200">
                                                    <Star className="h-4 w-4 fill-current" />
                                                </span>
                                            )}
                                            <div className={`rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs font-medium ${scoreTone(item.overall_score)}`}>
                                                {item.overall_score}
                                            </div>
                                        </div>
                                    </div>
                                    <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-300">{item.overview}</p>
                                    <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                                        <span>{item.findings_count} bulgu</span>
                                        <span>{new Date(item.created_at).toLocaleString('tr-TR')}</span>
                                    </div>
                                </div>
                            </button>
                            <div className="border-t border-slate-800 px-4 py-4">
                                <div className="flex flex-wrap gap-2">
                                    <button
                                        type="button"
                                        onClick={() => toggleFavoriteHistoryRecord(item)}
                                        className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition ${
                                            item.is_favorite
                                                ? 'border-amber-400/40 bg-amber-500/10 text-amber-200'
                                                : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-500'
                                        }`}
                                    >
                                        <Star className={`h-3.5 w-3.5 ${item.is_favorite ? 'fill-current' : ''}`} />
                                        {item.is_favorite ? 'Favoriden Cikar' : 'Favorile'}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => openRenameHistoryModal(item)}
                                        className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 transition hover:border-slate-500"
                                    >
                                        <Pencil className="h-3.5 w-3.5" />
                                        Yeniden Adlandir
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => openDeleteHistoryModal(item)}
                                        className="inline-flex items-center gap-2 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200 transition hover:border-red-300/50"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                        Sil
                                    </button>
                                </div>
                            </div>
                        </article>
                    )) : (
                        <div className="col-span-full rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-8 text-center text-sm text-slate-500">
                            {historyLoading ? 'Kaydedilen UI/UX analizleri yukleniyor...' : 'Henuz kaydedilmis UI/UX analizi yok.'}
                        </div>
                    )}
                </div>
            </section>

            {(renameTarget || deleteTarget) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
                    <div className="w-full max-w-lg rounded-[2rem] border border-slate-800 bg-slate-950 p-6 shadow-2xl">
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">History Action</div>
                                <h2 className="mt-2 text-2xl font-semibold text-white">
                                    {renameTarget ? 'Kaydi Yeniden Adlandir' : 'Kaydi Sil'}
                                </h2>
                            </div>
                            <button
                                type="button"
                                onClick={() => {
                                    if (historyModalBusy) return;
                                    setRenameTarget(null);
                                    setDeleteTarget(null);
                                    setRenameValue('');
                                }}
                                className="rounded-full border border-slate-700 bg-slate-900 p-2 text-slate-400 transition hover:border-slate-500 hover:text-white"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>

                        {renameTarget ? (
                            <div className="mt-6 space-y-4">
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3">
                                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Mevcut Kayit</div>
                                    <div className="mt-2 truncate text-sm text-white">
                                        {renameTarget.source_label ?? 'Manuel screenshot analizi'}
                                    </div>
                                </div>
                                <input
                                    type="text"
                                    value={renameValue}
                                    onChange={(event) => setRenameValue(event.target.value)}
                                    className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-cyan-400/50"
                                    placeholder="Kayit adi"
                                />
                                <div className="flex justify-end gap-3">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setRenameTarget(null);
                                            setRenameValue('');
                                        }}
                                        disabled={historyModalBusy}
                                        className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-300 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        Vazgec
                                    </button>
                                    <button
                                        type="button"
                                        onClick={renameHistoryRecord}
                                        disabled={historyModalBusy}
                                        className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:border-cyan-300/50 hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {historyModalBusy ? 'Kaydediliyor...' : 'Kaydi Guncelle'}
                                    </button>
                                </div>
                            </div>
                        ) : deleteTarget ? (
                            <div className="mt-6 space-y-5">
                                <div className="rounded-2xl border border-red-400/20 bg-red-500/5 px-4 py-4 text-sm leading-6 text-slate-200">
                                    <span className="font-semibold text-white">
                                        {deleteTarget.source_label ?? 'Manuel screenshot analizi'}
                                    </span>{' '}
                                    kaydini silmek uzeresin. Bu islem geri alinmaz.
                                </div>
                                <div className="flex justify-end gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setDeleteTarget(null)}
                                        disabled={historyModalBusy}
                                        className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-300 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        Vazgec
                                    </button>
                                    <button
                                        type="button"
                                        onClick={deleteHistoryRecord}
                                        disabled={historyModalBusy}
                                        className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-200 transition hover:border-red-300/50 hover:bg-red-500/15 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        {historyModalBusy ? 'Siliniyor...' : 'Kaydi Sil'}
                                    </button>
                                </div>
                            </div>
                        ) : null}
                    </div>
                </div>
            )}
        </div>
    );
}

export default UIUXPage;
