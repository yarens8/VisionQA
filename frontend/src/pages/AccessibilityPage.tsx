import { useEffect, useState } from 'react';
import axios from 'axios';
import {
    Accessibility,
    AlertTriangle,
    CheckCircle2,
    Eye,
    FileImage,
    History,
    Layers3,
    Palette,
    Pencil,
    ScanSearch,
    Sparkles,
    Star,
    Trash2,
    X,
} from 'lucide-react';
import { api, AccessibilityAnalysisResponse, AccessibilityHistoryItem } from '../services/api';

function severityBadge(severity: string) {
    if (severity === 'high') return 'border-red-400/40 bg-red-500/10 text-red-200';
    if (severity === 'medium') return 'border-amber-400/40 bg-amber-500/10 text-amber-200';
    if (severity === 'low') return 'border-sky-400/40 bg-sky-500/10 text-sky-200';
    return 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200';
}

function scoreTone(score?: number) {
    if (score === undefined) return 'text-slate-200';
    if (score < 40) return 'text-red-200';
    if (score < 70) return 'text-amber-200';
    return 'text-emerald-200';
}

function heatmapStyle(severity: string) {
    if (severity === 'high') {
        return 'bg-red-500/10 border-red-400/35';
    }
    if (severity === 'medium') {
        return 'bg-amber-500/10 border-amber-400/30';
    }
    if (severity === 'low') {
        return 'bg-sky-500/8 border-sky-400/25';
    }
    return 'bg-emerald-500/5 border-emerald-400/15';
}

export function AccessibilityPage() {
    const [preview, setPreview] = useState<string | null>(null);
    const [analysis, setAnalysis] = useState<AccessibilityAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [urlInput, setUrlInput] = useState('');
    const [fullPageUrlCapture, setFullPageUrlCapture] = useState(false);
    const [showOverlay, setShowOverlay] = useState(true);
    const [showHeatmap, setShowHeatmap] = useState(false);
    const [selectedFindingId, setSelectedFindingId] = useState<number | null>(null);
    const [historyItems, setHistoryItems] = useState<AccessibilityHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [historyFilter, setHistoryFilter] = useState<'all' | 'favorites' | 'url' | 'upload'>('all');
    const [renameTarget, setRenameTarget] = useState<AccessibilityHistoryItem | null>(null);
    const [renameValue, setRenameValue] = useState('');
    const [deleteTarget, setDeleteTarget] = useState<AccessibilityHistoryItem | null>(null);
    const [historyModalBusy, setHistoryModalBusy] = useState(false);

    const getRequestErrorMessage = (err: unknown, fallback: string) => {
        if (axios.isAxiosError(err)) {
            const detail = err.response?.data?.detail;
            if (typeof detail === 'string' && detail.trim()) {
                return detail;
            }
            if (typeof err.message === 'string' && err.message.trim()) {
                return err.message;
            }
        }
        if (err instanceof Error && err.message.trim()) {
            return err.message;
        }
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
            setShowOverlay(true);
            setShowHeatmap(false);
            setSelectedFindingId(null);
        };
        reader.readAsDataURL(file);
    };

    const loadHistory = async () => {
        setHistoryLoading(true);
        try {
            const items = await api.getAccessibilityHistory(8);
            setHistoryItems(items);
        } catch (err) {
            console.warn('Accessibility history yüklenemedi:', err);
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        loadHistory();
    }, []);

    const runAnalysis = async () => {
        if (!preview) {
            setError('Önce analiz edilecek bir ekran görüntüsü yükle.');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const result = await api.analyzeAccessibilityImage(preview, 'web');
            setAnalysis(result);
            setSelectedFindingId(result.findings[0]?.id ?? null);
            await loadHistory();
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Accessibility analizi başlatılamadı.'));
        } finally {
            setLoading(false);
        }
    };

    const runUrlAnalysis = async () => {
        const trimmedUrl = urlInput.trim();
        if (!trimmedUrl) {
            setError('Önce analiz edilecek bir URL gir.');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const result = await api.analyzeAccessibilityUrl({
                url: trimmedUrl,
                platform: 'web',
                full_page: fullPageUrlCapture,
            });
            const sourceImage = result.artifacts.source_image_base64
                ? `data:image/png;base64,${result.artifacts.source_image_base64}`
                : null;

            setPreview(sourceImage);
            setAnalysis(result);
            setShowOverlay(true);
            setShowHeatmap(false);
            setSelectedFindingId(result.findings[0]?.id ?? null);
            await loadHistory();
        } catch (err) {
            setError(getRequestErrorMessage(err, 'URL tabanlı accessibility analizi başlatılamadı.'));
        } finally {
            setLoading(false);
        }
    };

    const openHistoryRecord = async (recordId: number) => {
        setLoading(true);
        setError(null);
        try {
            const detail = await api.getAccessibilityHistoryDetail(recordId);
            const sourceImage = detail.analysis.artifacts.source_image_base64
                ? `data:image/png;base64,${detail.analysis.artifacts.source_image_base64}`
                : null;

            setPreview(sourceImage);
            setAnalysis(detail.analysis);
            setUrlInput(detail.source_url ?? '');
            setShowOverlay(true);
            setShowHeatmap(false);
            setSelectedFindingId(detail.analysis.findings[0]?.id ?? null);
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Kayitli accessibility analizi acilamadi.'));
        } finally {
            setLoading(false);
        }
    };

    const openRenameHistoryModal = (item: AccessibilityHistoryItem) => {
        setRenameTarget(item);
        setRenameValue(item.source_label ?? item.source_url ?? '');
    };

    const renameHistoryRecord = async () => {
        if (!renameTarget) return;
        try {
            setHistoryModalBusy(true);
            const updatedRecord = await api.updateAccessibilityHistory(renameTarget.id, { source_label: renameValue });
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

    const toggleFavoriteHistoryRecord = async (item: AccessibilityHistoryItem) => {
        try {
            const updatedRecord = await api.updateAccessibilityHistory(item.id, { is_favorite: !item.is_favorite });
            setHistoryItems((currentItems) =>
                currentItems.map((historyItem) => (historyItem.id === updatedRecord.id ? updatedRecord : historyItem))
            );
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Favori durumu guncellenemedi.'));
        }
    };

    const openDeleteHistoryModal = (item: AccessibilityHistoryItem) => {
        setDeleteTarget(item);
    };

    const deleteHistoryRecord = async () => {
        if (!deleteTarget) return;
        try {
            setHistoryModalBusy(true);
            const deletedRecordId = deleteTarget.id;
            await api.deleteAccessibilityHistory(deletedRecordId);
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

    const topFindings = analysis?.findings.slice(0, 5) ?? [];
    const topComponents = analysis?.components.slice(0, 5) ?? [];
    const selectedFinding = topFindings.find((finding) => finding.id === selectedFindingId) ?? topFindings[0] ?? null;
    const filteredHistoryItems = historyItems.filter((item) => {
        if (historyFilter === 'favorites') return item.is_favorite;
        if (historyFilter === 'url') return item.source_type === 'url';
        if (historyFilter === 'upload') return item.source_type === 'upload';
        return true;
    });

    return (
        <div className="w-full min-w-0 space-y-6">
            <section className="overflow-hidden rounded-[28px] border border-cyan-500/20 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.18),_transparent_30%),linear-gradient(180deg,_#0b1120_0%,_#020617_100%)] p-8">
                <div className="flex flex-col gap-6">
                    <div className="max-w-3xl">
                        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-medium uppercase tracking-[0.22em] text-cyan-200">
                            <Sparkles className="h-3.5 w-3.5" />
                            Faz 1 Yerlesim Stabilizasyonu
                        </div>
                        <h1 className="mt-4 flex items-center gap-3 text-4xl font-bold tracking-tight text-white">
                            <Accessibility className="h-9 w-9 text-cyan-300" />
                            Universal Accessibility Expert
                        </h1>
                        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-300">
                            Gorsel-oncelikli erisilebilirlik alani. Ekran goruntusunu yukle, overlay ile incele ve
                            WCAG odakli kontrast bulgularini tek ekranda gor.
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Genel Skor</div>
                            <div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.overall_score)}`}>
                                {analysis?.overall_score ?? '--'}
                            </div>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">AA Gecti</div>
                            <div className="mt-2 text-3xl font-bold text-white">{analysis?.wcag_summary.aa_pass ?? 0}</div>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Basarisiz</div>
                            <div className="mt-2 text-3xl font-bold text-red-200">{analysis?.wcag_summary.fail ?? 0}</div>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Palet Skoru</div>
                            <div className="mt-2 text-3xl font-bold text-white">{analysis?.color_consistency_score ?? '--'}</div>
                        </div>
                    </div>
                </div>
            </section>

            <section className="rounded-[28px] border border-slate-800 bg-slate-950">
                <div className="flex flex-col gap-4 border-b border-slate-800 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <div className="text-lg font-semibold text-white">Analiz Alani</div>
                        <div className="mt-1 text-sm text-slate-400">
                            Görsel yükle, analizi başlat ve overlay ile orijinal görünüm arasında geçiş yap.
                        </div>
                        <div className="mt-2 text-xs text-slate-500">
                            URL analizinde varsayılan olarak görünen ekran alınır. Uzun sayfalar için istersen
                            <span className="mx-1 font-medium text-slate-300">Tam Sayfa</span>
                            seçeneğini açabilirsin.
                        </div>
                    </div>
                </div>

                <div className="border-b border-slate-800 px-6 py-5">
                    <div className="rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
                        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                            <div>
                                <div className="text-sm font-semibold text-white">Canli URL Analizi</div>
                                <div className="mt-1 text-sm text-slate-400">
                                    Bir web adresi gir, sayfa screenshot'i ve accessibility metadata'si otomatik toplansin.
                                </div>
                            </div>

                            <div className="flex w-full flex-col gap-3 lg:w-auto lg:min-w-[560px] lg:flex-row">
                                <input
                                    type="url"
                                    value={urlInput}
                                    onChange={(e) => setUrlInput(e.target.value)}
                                    placeholder="https://ornek-site.com"
                                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-200 outline-none placeholder:text-slate-500 focus:border-cyan-400/50"
                                />
                                <label className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-sm text-slate-300">
                                    <input
                                        type="checkbox"
                                        checked={fullPageUrlCapture}
                                        onChange={(e) => setFullPageUrlCapture(e.target.checked)}
                                        className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-cyan-400 focus:ring-cyan-400"
                                    />
                                    Tam Sayfa
                                </label>
                                <button
                                    type="button"
                                    onClick={runUrlAnalysis}
                                    disabled={loading}
                                    className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-3 text-sm font-semibold text-cyan-100 transition hover:border-cyan-300/50 hover:bg-cyan-400/15 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    URL Analiz
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="px-6 py-5">
                    <div className="flex flex-wrap items-center gap-3">
                        <div className="inline-flex rounded-xl border border-slate-700 bg-slate-900 p-1">
                            <button
                                type="button"
                                onClick={() => setShowOverlay(true)}
                                className={`rounded-lg px-3 py-2 text-sm transition ${showOverlay ? 'bg-cyan-500 text-slate-950' : 'text-slate-300'}`}
                            >
                                Overlay
                            </button>
                            <button
                                type="button"
                                onClick={() => setShowOverlay(false)}
                                className={`rounded-lg px-3 py-2 text-sm transition ${!showOverlay ? 'bg-cyan-500 text-slate-950' : 'text-slate-300'}`}
                            >
                                Original
                            </button>
                        </div>

                        <label className="cursor-pointer rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition hover:border-slate-500">
                            Screenshot Yükle
                            <input
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
                            />
                        </label>
                        <button
                            type="button"
                            onClick={runAnalysis}
                            disabled={loading}
                            className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {loading ? 'Analiz ediliyor...' : 'Tum Sayfayi Analiz Et'}
                        </button>
                    </div>
                </div>

                <div className="grid min-w-0 grid-cols-1 gap-6 p-6 xl:grid-cols-[minmax(0,1fr)_340px]">
                    <div className="min-w-0">
                        <div className="overflow-hidden rounded-[24px] border border-slate-800 bg-slate-900/70">
                            {preview ? (
                                <div className="relative">
                                    <img
                                        src={preview}
                                        alt="Erisilebilirlik onizlemesi"
                                        className="block max-h-[760px] w-full object-contain"
                                    />

                                    {showOverlay && analysis && (
                                        <div className="absolute inset-0">
                                            {analysis.heatmap.map((region, index) => (
                                                showHeatmap ? (
                                                    <div
                                                        key={`${region.x}-${region.y}-${index}`}
                                                        className={`absolute border ${heatmapStyle(region.severity)}`}
                                                        style={{
                                                            left: `${(region.x / analysis.image.width) * 100}%`,
                                                            top: `${(region.y / analysis.image.height) * 100}%`,
                                                            width: `${(region.width / analysis.image.width) * 100}%`,
                                                            height: `${(region.height / analysis.image.height) * 100}%`,
                                                        }}
                                                    />
                                                ) : null
                                            ))}

                                            {topFindings.map((finding) => (
                                                <div
                                                    key={`finding-${finding.id}`}
                                                    className={`absolute border-2 shadow-[0_0_0_1px_rgba(255,255,255,0.12)] ${
                                                        selectedFinding?.id === finding.id ? 'border-cyan-300' : 'border-white/75'
                                                    }`}
                                                    style={{
                                                        left: `${(finding.bounding_box.x / analysis.image.width) * 100}%`,
                                                        top: `${(finding.bounding_box.y / analysis.image.height) * 100}%`,
                                                        width: `${(finding.bounding_box.width / analysis.image.width) * 100}%`,
                                                        height: `${(finding.bounding_box.height / analysis.image.height) * 100}%`,
                                                    }}
                                                >
                                                    <div className={`absolute left-1 top-1 flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-[11px] font-bold ${
                                                        selectedFinding?.id === finding.id ? 'bg-cyan-300 text-slate-950' : 'bg-white text-slate-950'
                                                    }`}>
                                                        {finding.id}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="flex min-h-[520px] flex-col items-center justify-center px-6 text-center">
                                    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
                                        <FileImage className="mx-auto h-10 w-10 text-slate-500" />
                                    </div>
                                    <div className="mt-5 text-lg font-semibold text-white">Bir ekran görüntüsü yükle</div>
                                    <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">
                                        İstersen screenshot yükle, istersen URL ver. Sayfanın tamamını kontrast, renk ayrışması ve erişilebilirlik sinyalleri açısından analiz edeceğiz.
                                    </p>
                                </div>
                            )}
                        </div>

                        {analysis && (
                            <div className="mt-4 flex flex-wrap gap-3">
                                <div className="rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
                                    Katman: {showOverlay ? 'Acik' : 'Kapali'}
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setShowHeatmap((value) => !value)}
                                    className="rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300 transition hover:border-slate-500"
                                >
                                    Heatmap: {showHeatmap ? 'Acik' : 'Kapali'}
                                </button>
                                <div className="rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
                                    Overlay kutulari bulgu kartlariyla eslesir
                                </div>
                                <div className="rounded-full border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300">
                                    Beyaz kutular oncelikli bulgulari gosteriyor
                                </div>
                                {selectedFinding && (
                                    <div className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-100">
                                        Secili bulgu: #{selectedFinding.id}
                                    </div>
                                )}
                            </div>
                        )}

                        {selectedFinding && (
                            <div className="mt-4 rounded-2xl border border-cyan-500/20 bg-slate-900 p-4">
                                <div className="flex items-center justify-between gap-3">
                                    <div>
                                        <div className="text-sm font-semibold text-white">
                                            Secili Bulgu Onizlemesi #{selectedFinding.id}
                                        </div>
                                        <div className="mt-1 text-xs text-slate-400">
                                            Bu onizleme, screenshot uzerindeki ayni numarali kutuya karsilik gelir.
                                        </div>
                                    </div>
                                    <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(selectedFinding.severity)}`}>
                                        {selectedFinding.severity}
                                    </div>
                                </div>

                                <div className="mt-4 grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
                                    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
                                        {selectedFinding.crop_image_base64 ? (
                                            <img
                                                src={`data:image/png;base64,${selectedFinding.crop_image_base64}`}
                                                alt={`Secili bulgu ${selectedFinding.id}`}
                                                className="block h-full max-h-40 w-full object-contain"
                                            />
                                        ) : (
                                            <div className="flex h-40 items-center justify-center px-4 text-center text-xs text-slate-500">
                                                Crop preview gelmedi. Backend yeniden baslatilmadiysa eski response donuyor olabilir.
                                            </div>
                                        )}
                                    </div>

                                    <div className="min-w-0">
                                        <div className="text-sm font-semibold text-white">{selectedFinding.title}</div>
                                        <div className="mt-1 text-xs text-slate-500">
                                            Oran {selectedFinding.contrast_ratio} • {selectedFinding.wcag_status}
                                        </div>
                                        <div className="mt-3 flex flex-wrap gap-2">
                                            <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-300">
                                                <span className="h-3 w-3 rounded-full border border-white/10" style={{ backgroundColor: selectedFinding.dominant_dark }} />
                                                {selectedFinding.dominant_dark}
                                            </div>
                                            <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-300">
                                                <span className="h-3 w-3 rounded-full border border-white/10" style={{ backgroundColor: selectedFinding.dominant_light }} />
                                                {selectedFinding.dominant_light}
                                            </div>
                                        </div>
                                        <p className="mt-3 text-sm leading-6 text-slate-300">{selectedFinding.description}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {error && (
                            <div className="mt-4 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                                {error}
                            </div>
                        )}
                    </div>

                    <aside className="min-w-0 space-y-4">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                            <div className="flex items-center gap-3 text-white">
                                <ScanSearch className="h-5 w-5 text-cyan-300" />
                                <div>
                                    <div className="font-semibold">Ozet</div>
                                    <div className="text-sm text-slate-400">Analiz özeti</div>
                                </div>
                            </div>
                            <p className="mt-4 text-sm leading-6 text-slate-300">
                                {analysis?.overview ?? 'Henüz analiz sonucu yok.'}
                            </p>
                        </div>

                        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                            <div className="flex items-center gap-3 text-white">
                                <Palette className="h-5 w-5 text-fuchsia-300" />
                                <div>
                                    <div className="font-semibold">Renk Ozeti</div>
                                    <div className="text-sm text-slate-400">Baskın renkler</div>
                                </div>
                            </div>
                            <div className="mt-4 grid grid-cols-2 gap-3">
                                {analysis?.palette.length ? analysis.palette.slice(0, 4).map((item) => (
                                    <div key={`${item.color}-${item.coverage}`} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3">
                                        <div className="flex items-center gap-2">
                                            <div className="h-4 w-4 rounded-full border border-white/20" style={{ backgroundColor: item.color }} />
                                            <span className="text-sm text-white">{item.color}</span>
                                        </div>
                                        <div className="mt-2 text-xs text-slate-500">%{item.coverage}</div>
                                    </div>
                                )) : (
                                    <div className="col-span-2 text-sm text-slate-500">Palette analizi burada görünecek.</div>
                                )}
                            </div>
                        </div>
                    </aside>
                </div>
            </section>

            <section className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                <div className="min-w-0 rounded-[28px] border border-slate-800 bg-slate-950 p-6">
                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <div className="flex items-center gap-3 text-white">
                                <AlertTriangle className="h-5 w-5 text-amber-300" />
                                <h2 className="text-lg font-semibold">Oncelikli Bulgular</h2>
                            </div>
                            <p className="mt-1 text-sm text-slate-400">Öncelikli erişilebilirlik bulguları.</p>
                        </div>
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{topFindings.length} bulgu</div>
                    </div>

                    <div className="mt-5 grid gap-4">
                        {topFindings.length ? topFindings.map((finding) => (
                            <button
                                key={finding.id}
                                type="button"
                                onClick={() => setSelectedFindingId(finding.id)}
                                className={`w-full rounded-2xl border bg-slate-900 p-5 text-left transition ${
                                    selectedFinding?.id === finding.id
                                        ? 'border-cyan-400/50 shadow-[0_0_0_1px_rgba(34,211,238,0.15)]'
                                        : 'border-slate-800 hover:border-slate-700'
                                }`}
                            >
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className={`flex h-7 min-w-7 items-center justify-center rounded-full text-xs font-bold ${
                                                selectedFinding?.id === finding.id ? 'bg-cyan-300 text-slate-950' : 'bg-slate-800 text-slate-200'
                                            }`}>
                                                {finding.id}
                                            </span>
                                            <div className="text-base font-semibold text-white">{finding.title}</div>
                                        </div>
                                        <div className="mt-1 text-xs text-slate-500">
                                            Ratio {finding.contrast_ratio} • {finding.wcag_status}
                                        </div>
                                    </div>
                                    <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(finding.severity)}`}>
                                        {finding.severity}
                                    </div>
                                </div>
                                <div className="mt-3 flex flex-wrap gap-3">
                                    <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-300">
                                        <span className="h-3 w-3 rounded-full border border-white/10" style={{ backgroundColor: finding.dominant_dark }} />
                                        {finding.dominant_dark}
                                    </div>
                                    <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-slate-300">
                                        <span className="h-3 w-3 rounded-full border border-white/10" style={{ backgroundColor: finding.dominant_light }} />
                                        {finding.dominant_light}
                                    </div>
                                </div>
                                <div className="mt-4 overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
                                    <img
                                        src={`data:image/png;base64,${finding.crop_image_base64}`}
                                        alt={`Bulgu ${finding.id} onizlemesi`}
                                        className="block max-h-40 w-full object-contain"
                                    />
                                </div>
                                <p className="mt-3 text-sm leading-6 text-slate-300">{finding.description}</p>
                                <div className="mt-3 text-xs text-slate-500">
                                    Kutudaki etiket: #{finding.id} • Bu karttaki onizleme ilgili sorunlu alani gosterir.
                                </div>
                                <div className="mt-4 rounded-xl border border-cyan-400/15 bg-cyan-400/5 px-4 py-3 text-sm text-cyan-100">
                                    {finding.recommendation}
                                </div>
                            </button>
                        )) : (
                            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-8 text-center text-sm text-slate-500">
                                Analiz yapıldığında bulgular burada listelenecek.
                            </div>
                        )}
                    </div>
                </div>

                <div className="space-y-6">
                    <div className="rounded-[28px] border border-slate-800 bg-slate-950 p-6">
                        <div className="flex items-center gap-3 text-white">
                            <Layers3 className="h-5 w-5 text-sky-300" />
                            <div>
                                <div className="font-semibold">Tespit Edilen Bilesenler</div>
                                <div className="text-sm text-slate-400">Bulgu urettigimiz aday bilesenler</div>
                            </div>
                        </div>

                        <div className="mt-5 space-y-3">
                            {topComponents.length ? topComponents.map((component) => (
                                <div key={component.id} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                    <div className="flex items-center justify-between gap-3">
                                        <div>
                                            <div className="text-sm font-semibold capitalize text-white">{component.label}</div>
                                            <div className="mt-1 text-xs text-slate-500">Ort. oran {component.average_contrast_ratio}</div>
                                        </div>
                                        <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(component.severity)}`}>
                                            {component.severity}
                                        </div>
                                    </div>
                                </div>
                            )) : (
                                <div className="text-sm text-slate-500">Bileşen sinyalleri analizden sonra oluşacak.</div>
                            )}
                        </div>
                    </div>

                    <div className="rounded-[28px] border border-slate-800 bg-slate-950 p-6">
                        <div className="flex items-center gap-3 text-white">
                            <Eye className="h-5 w-5 text-emerald-300" />
                            <div>
                                <div className="font-semibold">Iyilestirme Onerileri</div>
                                <div className="text-sm text-slate-400">Kısa aksiyon listesi</div>
                            </div>
                        </div>

                        <div className="mt-5 space-y-3">
                            {analysis?.recommendations.length ? analysis.recommendations.slice(0, 4).map((item, index) => (
                                <div key={index} className="flex gap-3 rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
                                    <div className="text-sm leading-6 text-slate-300">{item}</div>
                                </div>
                            )) : (
                                <div className="text-sm text-slate-500">Öneriler analiz sonrası burada görünecek.</div>
                            )}
                        </div>
                    </div>
                </div>
            </section>

            <section className="rounded-[28px] border border-slate-800 bg-slate-950 p-6">
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-3 text-white">
                            <History className="h-5 w-5 text-violet-300" />
                            <h2 className="text-lg font-semibold">Kaydedilen Analizler</h2>
                        </div>
                        <p className="mt-1 text-sm text-slate-400">
                            Test ettiğin screenshot ve URL analizleri burada saklanır. Tıklayıp tekrar açabilirsin.
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

                <div className="mt-4 flex flex-wrap gap-2">
                    {[
                        { id: 'all', label: 'Tum Kayitlar' },
                        { id: 'favorites', label: 'Favoriler' },
                        { id: 'url', label: 'URL' },
                        { id: 'upload', label: 'Screenshot' },
                    ].map((filter) => (
                        <button
                            key={filter.id}
                            type="button"
                            onClick={() => setHistoryFilter(filter.id as typeof historyFilter)}
                            className={`rounded-full border px-3 py-2 text-xs transition ${
                                historyFilter === filter.id
                                    ? 'border-cyan-400/40 bg-cyan-400/10 text-cyan-100'
                                    : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500'
                            }`}
                        >
                            {filter.label}
                        </button>
                    ))}
                </div>

                <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2 2xl:grid-cols-3">
                    {filteredHistoryItems.length ? filteredHistoryItems.map((item) => (
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
                                            alt={`Kayitli analiz ${item.id}`}
                                            className="h-full w-full object-cover"
                                        />
                                    ) : (
                                        <div className="flex h-full items-center justify-center text-sm text-slate-500">
                                            Onizleme yok
                                        </div>
                                    )}
                                </div>
                                <div className="p-4">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <div className="truncate text-sm font-semibold text-white">
                                                {item.source_label ?? item.source_url ?? 'Manuel screenshot analizi'}
                                            </div>
                                            {item.source_label && item.source_url && (
                                                <div className="mt-1 truncate text-xs text-slate-500">{item.source_url}</div>
                                            )}
                                            <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">
                                                {item.source_type === 'url' ? 'URL analizi' : 'Screenshot analizi'}
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
                                <div className="flex items-start justify-between gap-3">
                                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">
                                        Kayit islemleri
                                    </div>
                                </div>
                                <div className="mt-3 flex flex-wrap gap-2">
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
                            {historyLoading
                                ? 'Kaydedilen analizler yükleniyor...'
                                : historyItems.length
                                    ? 'Secili filtre icin uygun kayit bulunamadi.'
                                    : 'Henüz kaydedilmiş accessibility analizi yok.'}
                        </div>
                    )}
                </div>
            </section>

            {(renameTarget || deleteTarget) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
                    <div className="w-full max-w-md rounded-[24px] border border-slate-800 bg-slate-950 p-6 shadow-2xl">
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <div className="flex items-center gap-3 text-white">
                                    {renameTarget ? (
                                        <Pencil className="h-5 w-5 text-cyan-300" />
                                    ) : (
                                        <Trash2 className="h-5 w-5 text-red-300" />
                                    )}
                                    <h3 className="text-lg font-semibold">
                                        {renameTarget ? 'Kaydi Yeniden Adlandir' : 'Kaydi Sil'}
                                    </h3>
                                </div>
                                <p className="mt-2 text-sm leading-6 text-slate-400">
                                    {renameTarget
                                        ? 'Kayit adi tarayici mesaji yerine burada duzenlenecek.'
                                        : 'Bu accessibility kaydini kalici olarak silecegiz.'}
                                </p>
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
                            <div className="mt-5 space-y-4">
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3">
                                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Mevcut Kayit</div>
                                    <div className="mt-2 truncate text-sm text-white">
                                        {renameTarget.source_label ?? renameTarget.source_url ?? 'Manuel screenshot analizi'}
                                    </div>
                                </div>
                                <div>
                                    <label className="mb-2 block text-sm font-medium text-slate-300">Yeni ad</label>
                                    <input
                                        type="text"
                                        value={renameValue}
                                        onChange={(event) => setRenameValue(event.target.value)}
                                        placeholder="Kayit icin yeni ad gir"
                                        className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-cyan-400/50"
                                        autoFocus
                                    />
                                </div>
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
                            <div className="mt-5 space-y-4">
                                <div className="rounded-2xl border border-red-400/20 bg-red-500/5 px-4 py-4">
                                    <div className="text-sm leading-6 text-slate-200">
                                        <span className="font-semibold text-white">
                                            {deleteTarget.source_label ?? deleteTarget.source_url ?? 'Manuel screenshot analizi'}
                                        </span>{' '}
                                        kaydini silmek uzeresin. Bu islem geri alinmaz.
                                    </div>
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

export default AccessibilityPage;
