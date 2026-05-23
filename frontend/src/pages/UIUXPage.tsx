import { useEffect, useRef, useState } from 'react';
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

import { api, AnalysisJobStatusResponse, Project, UiuxAnalysisResponse, UiuxHistoryItem } from '../services/api';

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

function evidenceValue(evidence: Record<string, unknown> | undefined, key: string, fallback = '--') {
    const value = evidence?.[key];
    if (typeof value === 'string' && value.trim()) return value;
    if (typeof value === 'number') return String(value);
    return fallback;
}

function metricLabel(name: string) {
    const labels: Record<string, string> = {
        layout_alignment: 'Yerleşim hizası',
        spacing_consistency: 'Boşluk tutarlılığı',
        visual_hierarchy: 'Görsel hiyerarşi',
        readability_flow: 'Okuma akışı',
        clutter_control: 'Karmaşıklık kontrolü',
        color_consistency: 'Renk tutarlılığı',
        responsive_risk: 'Responsive risk',
        candidate_count: 'Aday bileşen sayısı',
        edge_density: 'Kenar yoğunluğu',
        visual_clutter_score: 'Görsel karmaşıklık',
        spacing_variance_px: 'Boşluk sapması',
        grid_deviation_px: 'Grid sapması',
        primary_dominance: 'Birincil odak baskınlığı',
        primary_center_bias: 'Birincil odak konumu',
        attention_dispersion: 'Dikkat dağılması',
        whitespace_score: 'Boşluk dengesi',
        text_region_count: 'Metin bölgesi sayısı',
        small_text_regions: 'Küçük metin riski',
        long_text_lines: 'Uzun satır riski',
        text_density: 'Metin yoğunluğu',
        average_text_height_px: 'Ortalama metin yüksekliği',
        readability_risk_score: 'Okunabilirlik riski',
    };
    return labels[name] ?? name.replace(/_/g, ' ');
}

function sourceLabel(name: string) {
    const labels: Record<string, string> = {
        'image-processing': 'Sayisal goruntu isleme',
        'visual-analysis': 'Gorsel analiz',
        'rule-engine': 'Kural motoru',
    };
    return labels[name] ?? name;
}

function metricExpectation(name: string) {
    const expectations: Record<string, string> = {
        primary_dominance: 'Beklenen: 1.20+',
        visual_clutter_score: 'Düşük değer daha iyi',
        spacing_variance_px: 'Düşük px daha tutarlı',
        grid_deviation_px: '0 px ideal',
        edge_density: 'Düşük/orta aralık daha okunur',
        responsive_risk: 'Yüksek skor daha düşük risk',
        clutter_control: 'Yüksek skor daha sade ekran',
        whitespace_score: 'Yüksek skor daha dengeli boşluk',
        text_region_count: 'Metin benzeri alanların sayısı',
        small_text_regions: 'Düşük sayı daha okunur',
        long_text_lines: 'Düşük sayı daha iyi',
        text_density: 'Düşük/orta aralık daha rahat okunur',
        average_text_height_px: 'Daha büyük değer daha okunur',
        readability_risk_score: 'Düşük skor daha iyi',
    };
    return expectations[name] ?? 'Sayısal görüntü işleme metriği';
}

function metricInterpretation(name: string, rawValue: unknown) {
    const value = typeof rawValue === 'number' ? rawValue : Number(rawValue);
    if (Number.isNaN(value)) return 'Yorum üretilemedi.';
    if (name === 'primary_dominance') {
        if (value < 1.2) return 'Ana odak ikincil odaklardan yeterince ayrışmıyor.';
        if (value < 1.8) return 'Ana odak orta seviyede ayrışıyor.';
        return 'Ana odak yeterince baskın.';
    }
    if (name === 'visual_clutter_score') {
        if (value >= 65) return 'Ekran kalabalık ve ilk tarama yükü yüksek.';
        if (value >= 40) return 'Orta seviyede görsel karmaşıklık var.';
        return 'Görsel karmaşıklık düşük.';
    }
    if (name === 'spacing_variance_px') {
        if (value >= 18) return 'Boşluk ritmi belirgin şekilde tutarsız.';
        if (value >= 8) return 'Boşluk ritminde orta seviye sapma var.';
        return 'Boşluk ritmi genel olarak tutarlı.';
    }
    if (name === 'grid_deviation_px') {
        if (value >= 18) return 'Hizalama sapması belirgin.';
        if (value >= 8) return 'Küçük hizalama sapmaları var.';
        return 'Hizalama temiz görünüyor.';
    }
    if (name === 'edge_density') {
        if (value >= 0.08) return 'Ekranda görsel kenar/ayrım yoğunluğu yüksek.';
        if (value >= 0.035) return 'Orta seviyede görsel yoğunluk var.';
        return 'Kenar yoğunluğu düşük.';
    }
    if (name === 'readability_risk_score') {
        if (value >= 70) return 'Metin okunabilirliği için yüksek risk var.';
        if (value >= 42) return 'Metin okunabilirliği için orta seviye risk var.';
        return 'Metin okunabilirliği riski düşük.';
    }
    if (name === 'small_text_regions') {
        if (value >= 3) return 'Ekranda küçük metin bölgeleri belirgin.';
        if (value >= 1) return 'Bazı metinler küçük görünebilir.';
        return 'Küçük metin sinyali düşük.';
    }
    if (name === 'long_text_lines') {
        if (value >= 2) return 'Uzun satırlar okuma hızını düşürebilir.';
        if (value >= 1) return 'Bir uzun satır riski var.';
        return 'Uzun satır riski düşük.';
    }
    if (name === 'text_region_count') {
        if (value >= 24) return 'Metin yükü yüksek; ekran taraması zorlaşabilir.';
        if (value >= 12) return 'Orta yoğunlukta metin alanı var.';
        return 'Metin yoğunluğu düşük.';
    }
    return 'Bu değer ilgili bulgunun sayısal dayanağı olarak kullanıldı.';
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
    const [jobStatus, setJobStatus] = useState<AnalysisJobStatusResponse | null>(null);
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState<number | ''>('');
    const activeJobRef = useRef<number | null>(null);

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

    const loadProjects = async () => {
        try {
            const projectItems = await api.getProjects();
            setProjects(projectItems);
        } catch (err) {
            console.warn('Projeler yuklenemedi:', err);
        }
    };

    const loadHistory = async (projectId: number | '' = selectedProjectId) => {
        setHistoryLoading(true);
        try {
            const items = await api.getUiuxHistory(6, typeof projectId === 'number' ? projectId : undefined);
            setHistoryItems(items);
        } catch (err) {
            console.warn('UI/UX history yuklenemedi:', err);
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        loadProjects();
        loadHistory();
    }, []);

    useEffect(() => {
        loadHistory(selectedProjectId);
    }, [selectedProjectId]);

    const applyAnalysisResult = async (result: UiuxAnalysisResponse) => {
        const sourceImage = result.artifacts.source_image_base64
            ? `data:image/png;base64,${result.artifacts.source_image_base64}`
            : preview;
        setPreview(sourceImage);
        setAnalysis(result);
        setSelectedFindingId(result.findings[0]?.id ?? null);
        setViewMode('annotated');
        await loadHistory();
    };

    const pollUiuxJob = async (jobId: number) => {
        activeJobRef.current = jobId;
        for (let attempt = 0; attempt < 90; attempt += 1) {
            const status = await api.getUiuxJobStatus(jobId);
            if (activeJobRef.current !== jobId) return;
            setJobStatus(status);

            if (status.status === 'completed') {
                if (status.result) {
                    await applyAnalysisResult(status.result as UiuxAnalysisResponse);
                }
                return;
            }

            if (status.status === 'failed') {
                throw new Error(status.error_message || 'UI/UX job basarisiz oldu.');
            }

            await new Promise((resolve) => window.setTimeout(resolve, 1500));
        }
        throw new Error('UI/UX job zaman asimina ugradi.');
    };

    const runAnalysis = async () => {
        if (!preview) {
            setError('Once analiz edilecek bir screenshot yukle.');
            return;
        }

        setLoading(true);
        setError(null);
        setJobStatus(null);
        try {
            const job = await api.startUiuxImageJob(preview, 'web', typeof selectedProjectId === 'number' ? selectedProjectId : undefined);
            setJobStatus({ ...job, job_id: job.job_id, celery_task_id: undefined, error_message: undefined, result: undefined, created_at: new Date().toISOString() });
            await pollUiuxJob(job.job_id);
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
    const scoreBreakdownEntries = Object.entries(analysis?.score_breakdown ?? {});
    const evidenceEntries = Object.entries(analysis?.evidence_matrix ?? {});
    const testSuggestions = analysis?.test_suggestions?.slice(0, 5) ?? [];
    const selectedMetricName = evidenceValue(selectedFinding?.numeric_evidence, 'metric');
    const selectedMetricValue = selectedFinding?.numeric_evidence?.value;

    return (
        <div className="mx-auto w-full max-w-[1760px] space-y-6">
            <section className="overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950">
                <div className="relative isolate overflow-hidden px-6 py-7 md:px-8">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.12),_transparent_34%)]" />
                    <div className="relative z-10 flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
                        <div className="max-w-3xl">
                            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.24em] text-cyan-100">
                                <Sparkles className="h-3.5 w-3.5" />
                                4.3 AI UX Denetimi v1.2
                            </div>
                            <h1 className="mt-4 flex items-center gap-3 text-3xl font-bold tracking-tight text-white">
                                <Layers3 className="h-8 w-8 text-cyan-300" />
                                Screenshot Tabanli UI/UX Denetimi
                            </h1>
                            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-300">
                                Layout, hiyerarsi, spacing, odak netligi ve kullanici surtunmesini screenshot uzerinden yorumlayarak incele.
                            </p>
                        </div>

                        <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-4 xl:max-w-2xl">
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">UX Skoru</div>
                                <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.ux_score ?? analysis?.overall_score)}`}>{analysis?.ux_score ?? analysis?.overall_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Hiyerarsi</div>
                                <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.visual_hierarchy_score)}`}>{analysis?.visual_hierarchy_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Surtunme</div>
                                <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.friction_score)}`}>{analysis?.friction_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-400">Odak</div>
                                <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.focus_score)}`}>{analysis?.focus_score ?? '--'}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <div className="grid items-stretch gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(420px,0.65fr)]">
                <section className="flex h-[620px] flex-col rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="flex flex-col gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-center md:justify-between">
                        <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Girdi</div>
                            <h2 className="mt-2 text-xl font-semibold text-white">Screenshot Yukle</h2>
                            <p className="mt-2 text-sm leading-6 text-slate-400">
                                Tek bir ekran goruntusu ile hizalama, spacing ve gorsel tutarlilik sinyallerini uret.
                            </p>
                        </div>
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                            <div className="min-w-[260px] rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3">
                                <label className="block text-[10px] uppercase tracking-[0.2em] text-cyan-200">
                                    Project Binding
                                </label>
                                <select
                                    value={selectedProjectId}
                                    onChange={(event) => setSelectedProjectId(event.target.value ? Number(event.target.value) : '')}
                                    className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-300"
                                >
                                    <option value="">Global analiz</option>
                                    {projects.map((project) => (
                                        <option key={project.id} value={project.id}>
                                            {project.name}
                                        </option>
                                    ))}
                                </select>
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
                    </div>

                    <div className="mt-6 flex-1 overflow-hidden rounded-[1.5rem] border border-dashed border-slate-700 bg-slate-900/50">
                        {imageSource ? (
                            <div className="relative flex h-full min-h-[420px] items-center justify-center bg-slate-950">
                                <img src={imageSource} alt="UI/UX preview" className="h-full max-h-[500px] w-full object-contain" />
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
                                    Isaretli Goruntu
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
                    {jobStatus && (
                        <div className="mt-4 rounded-2xl border border-cyan-400/25 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">
                            Job #{jobStatus.job_id} · {jobStatus.status}
                        </div>
                    )}
                </section>

                <section className="h-[620px] overflow-y-auto rounded-[2rem] border border-slate-800 bg-slate-950 p-6 pr-4 report-scrollbar">
                    <article>
                        <div className="flex items-center justify-between gap-4">
                            <div>
                                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Ozet</div>
                                <h2 className="mt-2 text-xl font-semibold text-white">Analiz Sonucu</h2>
                            </div>
                            <div className={`rounded-full border px-3 py-1 text-xs font-medium ${analysis?.findings.length ? 'border-amber-400/20 bg-amber-500/10 text-amber-200' : 'border-emerald-400/20 bg-emerald-500/10 text-emerald-200'}`}>
                                {analysis?.findings.length ? `${analysis.findings.length} bulgu` : 'Temiz ekran'}
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

                        <div className="mt-5 grid grid-cols-2 gap-3">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Hizalama</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.alignment_score)}`}>{analysis?.alignment_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Bosluk</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.spacing_consistency_score)}`}>{analysis?.spacing_consistency_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Denge</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.layout_balance_score)}`}>{analysis?.layout_balance_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Okunabilirlik</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.readability_score)}`}>{analysis?.readability_score ?? '--'}</div>
                            </div>
                        </div>
                        {analysis?.attention_prediction ? (
                            <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Dikkat Akisi Tahmini</div>
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

                        {scoreBreakdownEntries.length ? (
                            <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Sayisal Goruntu Isleme Skorlari</div>
                                <div className="mt-4 space-y-3">
                                    {scoreBreakdownEntries.map(([name, value]) => (
                                        <div key={name}>
                                            <div className="flex items-center justify-between text-xs">
                                                <span className="text-slate-300">{metricLabel(name)}</span>
                                                <span className={scoreTone(value)}>{value}</span>
                                            </div>
                                            <div className="mt-1 text-[11px] leading-4 text-slate-500">{metricExpectation(name)}</div>
                                            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-950">
                                                <div className="h-full rounded-full bg-cyan-300" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : null}

                        {evidenceEntries.length ? (
                            <div className="mt-5 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-cyan-200">Kanit Matrisi</div>
                                <div className="mt-4 grid grid-cols-2 gap-3">
                                    {evidenceEntries.map(([name, value]) => (
                                        <div key={name} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3">
                                            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{metricLabel(name)}</div>
                                            <div className="mt-1 text-sm font-semibold text-white">{String(value)}</div>
                                            <div className="mt-2 text-[11px] leading-4 text-slate-500">{metricInterpretation(name, value)}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : null}
                    </article>

                </section>
            </div>

            <section className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                <div className="flex items-center gap-3">
                    <div className="rounded-full border border-slate-700 bg-slate-900 p-2 text-slate-200">
                        {selectedFinding ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                    </div>
                    <div>
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Onizleme</div>
                        <h2 className="mt-1 text-xl font-semibold text-white">Secili Bulgu Detayi</h2>
                    </div>
                </div>

                {selectedFinding ? (
                    <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(300px,420px)_minmax(0,1fr)]">
                        <div className="overflow-hidden rounded-[1.5rem] border border-slate-800 bg-slate-900">
                            <img
                                src={`data:image/png;base64,${selectedFinding.crop_image_base64}`}
                                alt={`Finding ${selectedFinding.id}`}
                                className="h-full min-h-[260px] w-full object-contain"
                            />
                        </div>
                        <div className="grid gap-4 xl:grid-cols-3">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="flex items-start justify-between gap-4">
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
                                <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-4">
                                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">AI UX Yorumu</div>
                                    <div className="mt-3 text-sm leading-6 text-slate-200">{selectedFinding.ai_critic}</div>
                                </div>
                            </div>
                            <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-amber-200">Neden Onemli</div>
                                <div className="mt-3 text-sm leading-6 text-amber-50">{selectedFinding.why_this_matters}</div>
                                <div className="mt-4 rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-4 text-sm leading-6 text-cyan-50">
                                    {selectedFinding.recommendation}
                                </div>
                            </div>
                            <div className="rounded-2xl border border-sky-400/20 bg-sky-400/10 px-4 py-4">
                                <div className="text-xs uppercase tracking-[0.18em] text-sky-200">Sayisal Kanit</div>
                                <div className="mt-3 grid gap-3">
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Metrik</div>
                                        <div className="mt-1 text-xs text-white">{metricLabel(selectedMetricName)}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Deger</div>
                                        <div className="mt-1 text-xs text-white">{evidenceValue(selectedFinding.numeric_evidence, 'value')}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Kaynak</div>
                                        <div className="mt-1 text-xs text-white">{sourceLabel(evidenceValue(selectedFinding.numeric_evidence, 'source'))}</div>
                                    </div>
                                </div>
                                <div className="mt-3 grid gap-3">
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 text-sm leading-6 text-slate-200">
                                        {evidenceValue(selectedFinding.numeric_evidence, 'explanation')}
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 text-sm leading-6 text-slate-300">
                                        {metricInterpretation(selectedMetricName, selectedMetricValue)}
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 text-sm leading-6 text-slate-400">
                                        {metricExpectation(selectedMetricName)}
                                    </div>
                                </div>
                            </div>
                            {selectedFinding.test_suggestion && (
                                <div className="rounded-2xl border border-violet-400/20 bg-violet-400/10 px-4 py-4 xl:col-span-3">
                                    <div className="text-xs uppercase tracking-[0.18em] text-violet-200">Regresyon Test Onerisi</div>
                                    <div className="mt-3 text-sm leading-6 text-violet-50">{selectedFinding.test_suggestion}</div>
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="mt-5 rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                        Henuz secilecek bir bulgu yok.
                    </div>
                )}
            </section>

            <section className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
                <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Bulgular</div>
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
                                        {finding.numeric_evidence && (
                                            <div className="mt-3 flex flex-wrap gap-2">
                                                <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1 text-xs text-sky-100">
                                                    {metricLabel(evidenceValue(finding.numeric_evidence, 'metric'))}
                                                </span>
                                                <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-1 text-xs text-amber-100">
                                                    deger {evidenceValue(finding.numeric_evidence, 'value')}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                    <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(finding.severity)}`}>
                                        {finding.severity}
                                    </div>
                                </div>
                            </button>
                        )) : (
                            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                                Analiz sonrasi anlamli UI/UX bulgulari burada listelenecek.
                            </div>
                        )}
                    </div>
                </article>

                <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Oneriler</div>
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
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Dogrulama</div>
                        <h2 className="mt-2 text-xl font-semibold text-white">Sayisal Test Onerileri</h2>
                    </div>
                    <div className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs text-slate-300">
                        {testSuggestions.length} test
                    </div>
                </div>
                <div className="mt-5 grid gap-4 lg:grid-cols-2">
                    {testSuggestions.length ? testSuggestions.map((item) => (
                        <div key={`${item.category}-${item.title}`} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="flex items-center justify-between gap-3">
                                <div className="text-sm font-semibold text-white">{item.title}</div>
                                <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(item.priority ?? 'low')}`}>
                                    {item.priority ?? 'review'}
                                </div>
                            </div>
                            <div className="mt-2 text-xs uppercase tracking-[0.18em] text-cyan-200">{item.category}</div>
                            <p className="mt-3 text-sm leading-6 text-slate-300">{item.suggestion}</p>
                        </div>
                    )) : (
                        <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                            Analiz sonrasinda screenshot metriklerinden turetilen test onerileri burada gorunecek.
                        </div>
                    )}
                </div>
            </section>

            <section className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Gecmis</div>
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
                        onClick={() => loadHistory()}
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
                                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Gecmis Islemi</div>
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
