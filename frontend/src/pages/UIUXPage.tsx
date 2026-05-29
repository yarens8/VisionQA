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
        requested_platform: 'Istenen platform',
        detected_platform: 'Algilanan platform',
        platform_profile: 'Platform profili',
        platform_confidence: 'Platform guveni',
        platform_aspect_ratio: 'Ekran orani',
        dominant_contrast_ratio: 'Baskın kontrast',
        palette_consistency_score: 'Palet tutarlılığı',
        color_harmony_score: 'Renk uyumu',
        cta_visibility_score: 'CTA görünürlüğü',
        design_token_consistency: 'Design token uyumu',
        design_token_score: 'Design token skoru',
        spacing_token_fit_score: 'Spacing token uyumu',
        spacing_token_deviation_px: 'Token sapması',
        spacing_token_violations: 'Spacing ihlali',
        font_scale_score: 'Font scale uyumu',
        radius_consistency_score: 'Radius uyumu',
        radius_bucket_variance: 'Radius sapması',
        button_consistency_score: 'Buton standardı',
        button_height_variance_px: 'Buton yükseklik sapması',
        task_completion_score: 'Görev tamamlama skoru',
        task_friction_score: 'Görev sürtünmesi',
        task_confidence: 'Görev tahmin güveni',
        task_type: 'Görev tipi',
        hue_spread: 'Renk açısı dağılımı',
        recommended_accent_color: 'Önerilen accent',
        recommended_text_color: 'Önerilen metin rengi',
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
        dominant_contrast_ratio: 'Metin/zemin için 4.5+ hedeflenir',
        palette_consistency_score: 'Yüksek skor daha tutarlı palet',
        color_harmony_score: 'Yüksek skor daha uyumlu renk ailesi',
        cta_visibility_score: 'Yüksek skor daha görünür ana aksiyon',
        design_token_consistency: 'Yüksek skor daha tutarlı tasarım sistemi',
        design_token_score: 'Yüksek skor daha tutarlı token kullanımı',
        spacing_token_fit_score: '4/8 tabanlı token setine yakınlık',
        spacing_token_deviation_px: 'Düşük px daha iyi',
        spacing_token_violations: 'Düşük sayı daha iyi',
        font_scale_score: 'Yüksek skor daha tutarlı tipografi',
        radius_consistency_score: 'Yüksek skor daha tutarlı köşe dili',
        radius_bucket_variance: 'Düşük değer daha tutarlı radius',
        button_consistency_score: 'Yüksek skor daha tutarlı buton sistemi',
        button_height_variance_px: 'Düşük px daha tutarlı buton yüksekliği',
        task_completion_score: 'Yüksek skor daha net görev akışı',
        task_friction_score: 'Düşük skor daha az sürtünme',
        task_confidence: 'Yüksek değer daha güvenilir görev tahmini',
        task_type: 'Algılanan ekran görevi',
        hue_spread: 'Aşırı geniş dağılım paleti dağıtabilir',
        recommended_accent_color: 'CTA veya vurgu için öneri',
        recommended_text_color: 'CTA/metin okunurluğu için öneri',
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
    if (name === 'dominant_contrast_ratio') {
        if (value < 3) return 'Baskın renkler arasında ayrışma zayıf.';
        if (value < 4.5) return 'Kontrast orta seviyede; kritik metinlerde güçlendirilebilir.';
        return 'Baskın renk kontrastı güçlü.';
    }
    if (name === 'palette_consistency_score') {
        if (value < 65) return 'Palet fazla dağınık veya tutarsız görünüyor.';
        if (value < 80) return 'Palet orta seviyede tutarlı.';
        return 'Palet tutarlılığı iyi.';
    }
    if (name === 'color_harmony_score') {
        if (value < 65) return 'Renk aileleri birbirinden fazla uzaklaşıyor.';
        if (value < 80) return 'Renk uyumu orta seviyede.';
        return 'Renk uyumu dengeli.';
    }
    if (name === 'cta_visibility_score') {
        if (value < 60) return 'Ana aksiyon arka planda kaybolabilir.';
        if (value < 78) return 'CTA görünür ama daha güçlü ayrıştırılabilir.';
        return 'CTA görünürlüğü iyi.';
    }
    if (name === 'design_token_score' || name === 'design_token_consistency') {
        if (value < 65) return 'Tasarım token ritmi belirgin şekilde tutarsız.';
        if (value < 80) return 'Token uyumu orta seviyede; standardizasyon güçlendirilebilir.';
        return 'Tasarım token uyumu iyi.';
    }
    if (name === 'spacing_token_fit_score') {
        if (value < 65) return 'Boşluklar token ritminden belirgin sapıyor.';
        if (value < 82) return 'Boşluk token uyumu orta seviyede.';
        return 'Boşluklar token ritmine yakın.';
    }
    if (name === 'font_scale_score') {
        if (value < 65) return 'Tipografi ölçeği net ayrışmıyor.';
        if (value < 82) return 'Font scale orta seviyede tutarlı.';
        return 'Font scale uyumu iyi.';
    }
    if (name === 'radius_consistency_score') {
        if (value < 65) return 'Köşe radius dili dağınık görünüyor.';
        if (value < 82) return 'Radius uyumu orta seviyede.';
        return 'Radius dili tutarlı.';
    }
    if (name === 'button_consistency_score') {
        if (value < 65) return 'Buton boyut/padding standardı tutarsız.';
        if (value < 82) return 'Buton standardı orta seviyede tutarlı.';
        return 'Buton component standardı iyi.';
    }
    if (name === 'hue_spread') {
        if (value > 180) return 'Renk dağılımı geniş; palet dağınık hissedebilir.';
        if (value > 120) return 'Renk dağılımı orta genişlikte.';
        return 'Renk ailesi daha kontrollü görünüyor.';
    }
    if (name === 'task_completion_score') {
        if (value < 60) return 'Görev yolu belirgin şekilde sürtünmeli.';
        if (value < 82) return 'Görev tamamlanabilir ama akış daha net olabilir.';
        return 'Görev akışı güçlü görünüyor.';
    }
    if (name === 'task_friction_score') {
        if (value >= 60) return 'Kullanıcının görevi tamamlaması için yüksek sürtünme var.';
        if (value >= 35) return 'Orta seviyede görev sürtünmesi var.';
        return 'Görev sürtünmesi düşük.';
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
    const [platformMode, setPlatformMode] = useState<'auto' | 'web' | 'mobile'>('auto');
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
            const job = await api.startUiuxImageJob(preview, platformMode, typeof selectedProjectId === 'number' ? selectedProjectId : undefined);
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
    const colorIntel = analysis?.color_intelligence;
    const nestedDesignTokens = analysis?.image_processing_metrics?.design_tokens as UiuxAnalysisResponse['design_tokens'] | undefined;
    const designTokens = analysis?.design_tokens ?? nestedDesignTokens;
    const taskEvaluation = analysis?.task_evaluation;
    const personaRisk = analysis?.persona_risk;
    const visualRegression = analysis?.visual_regression;

    const heroStats = [
        { label: 'UX Skoru', value: analysis?.ux_score ?? analysis?.overall_score, tone: scoreTone(analysis?.ux_score ?? analysis?.overall_score), accent: 'from-cyan-300 to-emerald-300' },
        { label: 'Hiyerarsi', value: analysis?.visual_hierarchy_score, tone: scoreTone(analysis?.visual_hierarchy_score), accent: 'from-violet-300 to-sky-300' },
        { label: 'Surtunme', value: analysis?.friction_score, tone: scoreTone(analysis?.friction_score), accent: 'from-amber-300 to-rose-300' },
        { label: 'Odak', value: analysis?.focus_score, tone: scoreTone(analysis?.focus_score), accent: 'from-fuchsia-300 to-cyan-300' },
        { label: 'Token', value: designTokens?.design_token_score, tone: scoreTone(designTokens?.design_token_score), accent: 'from-lime-300 to-cyan-300' },
    ];
    const summaryScore = analysis?.ux_score ?? analysis?.overall_score;
    const findingCount = analysis?.findings.length ?? 0;
    const summaryStatus = !analysis ? 'Analiz bekliyor' : findingCount > 0 ? 'Inceleme gerekli' : 'Temiz ekran';
    const summaryStatusClass = !analysis
        ? 'border-slate-600 bg-slate-900 text-slate-300'
        : findingCount > 0
            ? 'border-amber-300/35 bg-amber-400/10 text-amber-100'
            : 'border-emerald-300/35 bg-emerald-400/10 text-emerald-100';
    const primaryActionText = selectedFinding?.recommendation
        || taskEvaluation?.recommendation
        || colorIntel?.recommendation
        || 'Screenshot yukleyip analizi baslat; bulgular ve aksiyonlar burada ozetlenir.';
    const primaryEvidenceText = selectedMetricName !== '--'
        ? `${metricLabel(selectedMetricName)}: ${selectedMetricValue ?? '--'}`
        : findingCount > 0
            ? 'Secili bulgu icin sayisal kanit incelenebilir.'
            : 'Kanit matrisi analiz sonrasinda dolacak.';
    const summaryHighlights = [
        { label: 'Bulgu', value: findingCount ? String(findingCount) : '--', detail: selectedFinding?.severity ? `${selectedFinding.severity} oncelik` : 'Analiz sonrasi' },
        { label: 'Platform', value: analysis?.detected_platform || analysis?.platform || '--', detail: analysis?.platform_profile || 'auto detect' },
        { label: 'Gorev', value: taskEvaluation?.task_score ?? '--', detail: taskEvaluation?.task_label || taskEvaluation?.task_type || 'task scoring' },
    ];

    return (
        <div className="relative mx-auto w-full max-w-[1620px] space-y-7 overflow-hidden px-1 pb-10">
            <div className="pointer-events-none absolute inset-0 -z-10 opacity-70 [background:radial-gradient(circle_at_18%_0%,rgba(34,211,238,0.16),transparent_28%),radial-gradient(circle_at_86%_6%,rgba(168,85,247,0.14),transparent_24%),linear-gradient(180deg,rgba(2,6,23,0.25),rgba(2,6,23,0.92))]" />

            <section className="overflow-hidden rounded-[2.25rem] border border-cyan-300/15 bg-[linear-gradient(145deg,rgba(8,47,73,0.34),rgba(2,6,23,0.98)_42%,rgba(15,23,42,0.94))] shadow-[0_28px_100px_rgba(2,6,23,0.55)]">
                <div className="relative isolate overflow-hidden px-6 py-7 md:px-8">
                    <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-cyan-200/70 to-transparent" />
                    <div className="absolute inset-x-8 bottom-0 h-px bg-gradient-to-r from-transparent via-violet-300/25 to-transparent" />
                    <div className="absolute right-[-8rem] top-[-10rem] h-72 w-72 rounded-full bg-cyan-300/10 blur-3xl" />
                    <div className="absolute left-[-10rem] bottom-[-12rem] h-80 w-80 rounded-full bg-violet-400/10 blur-3xl" />
                    <div className="relative z-10 flex flex-col gap-6 xl:flex-row xl:items-center xl:justify-between">
                        <div className="max-w-3xl">
                            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1 text-xs uppercase tracking-[0.24em] text-cyan-100 shadow-[0_0_24px_rgba(34,211,238,0.12)]">
                                <Sparkles className="h-3.5 w-3.5" />
                                4.3 AI UX Denetimi v1.2
                            </div>
                            <h1 className="mt-4 flex items-center gap-3 text-4xl font-black tracking-tight text-white md:text-5xl">
                                <span className="inline-flex h-14 w-14 items-center justify-center rounded-[1.35rem] border border-cyan-300/25 bg-cyan-300/10 shadow-[0_0_34px_rgba(34,211,238,0.16)]">
                                    <Layers3 className="h-8 w-8 text-cyan-200" />
                                </span>
                                AI UX Evidence Studio
                            </h1>
                            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">
                                Screenshot'i sayisal goruntu isleme, renk zekasi, gorev akisi, persona riski ve visual regression sinyalleriyle tek bir karar alaninda denetle.
                            </p>
                            <div className="mt-5 flex flex-wrap gap-2">
                                {['Image metrics', 'Color intelligence', 'Task UX', 'Persona risk', 'Regression'].map((label) => (
                                    <span key={label} className="rounded-full border border-white/10 bg-white/[0.055] px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-200">
                                        {label}
                                    </span>
                                ))}
                            </div>
                        </div>

                        <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-5 xl:max-w-3xl">
                            {heroStats.map((item) => (
                                <div key={item.label} className="group overflow-hidden rounded-[1.35rem] border border-white/10 bg-slate-950/55 px-5 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] transition hover:-translate-y-0.5 hover:border-cyan-200/30">
                                    <div className="text-[10px] uppercase tracking-[0.2em] text-slate-400">{item.label}</div>
                                    <div className={`mt-2 text-3xl font-black ${item.tone}`}>{item.value ?? '--'}</div>
                                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-950/70">
                                        <div
                                            className={`h-full rounded-full bg-gradient-to-r ${item.accent}`}
                                            style={{ width: `${Math.max(8, Math.min(100, Number(item.value) || 0))}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            <div className="grid items-stretch gap-6 xl:grid-cols-[minmax(0,1.36fr)_minmax(430px,0.64fr)]">
                <section className="flex h-[660px] flex-col overflow-hidden rounded-[2.25rem] border border-cyan-300/15 bg-[linear-gradient(155deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98)_48%,rgba(8,47,73,0.22))] shadow-[0_24px_80px_rgba(2,6,23,0.55)]">
                    <div className="h-px bg-gradient-to-r from-transparent via-cyan-300/70 to-transparent" />
                    <div className="flex min-h-0 flex-1 flex-col p-6">
                    <div className="flex flex-col gap-4 border-b border-cyan-300/10 pb-5 md:flex-row md:items-center md:justify-between">
                        <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Girdi</div>
                            <h2 className="mt-2 text-xl font-semibold text-white">Screenshot Yukle</h2>
                            <p className="mt-2 text-sm leading-6 text-slate-400">
                                Tek bir ekran goruntusu ile hizalama, spacing ve gorsel tutarlilik sinyallerini uret.
                            </p>
                        </div>
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                            <div className="min-w-[260px] rounded-[1.35rem] border border-cyan-300/20 bg-cyan-300/10 p-3 shadow-[0_0_28px_rgba(34,211,238,0.08)]">
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
                            <div className="min-w-[220px] rounded-[1.35rem] border border-violet-300/20 bg-violet-300/10 p-3">
                                <label className="block text-[10px] uppercase tracking-[0.2em] text-slate-400">
                                    Platform Mode
                                </label>
                                <select
                                    value={platformMode}
                                    onChange={(event) => setPlatformMode(event.target.value as 'auto' | 'web' | 'mobile')}
                                    className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-300"
                                >
                                    <option value="auto">Auto detect</option>
                                    <option value="web">Web / Desktop</option>
                                    <option value="mobile">Mobile</option>
                                </select>
                            </div>
                            <label className="inline-flex cursor-pointer items-center gap-2 rounded-[1rem] border border-slate-600 bg-slate-900/90 px-4 py-3 text-sm font-semibold text-slate-100 shadow-[0_10px_30px_rgba(15,23,42,0.35)] transition hover:-translate-y-0.5 hover:border-cyan-300/50 hover:bg-slate-800">
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

                    <div className="mt-5 min-h-0 flex-1 overflow-hidden rounded-[1.75rem] border border-dashed border-cyan-300/18 bg-[linear-gradient(160deg,rgba(15,23,42,0.72),rgba(2,6,23,0.95))] shadow-[inset_0_0_40px_rgba(2,6,23,0.65)]">
                        {imageSource ? (
                            <div className="relative flex h-full min-h-0 items-center justify-center overflow-hidden bg-slate-950">
                                <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(45deg,rgba(148,163,184,0.09)_25%,transparent_25%),linear-gradient(-45deg,rgba(148,163,184,0.09)_25%,transparent_25%)] [background-size:28px_28px]" />
                                <img src={imageSource} alt="UI/UX preview" className="relative z-10 h-full max-h-full w-full object-contain drop-shadow-[0_18px_36px_rgba(0,0,0,0.45)]" />
                            </div>
                        ) : (
                            <div className="flex h-full min-h-[260px] flex-col items-center justify-center px-6 text-center">
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

                    <div className="mt-4 flex shrink-0 flex-wrap items-center gap-3 border-t border-cyan-300/10 pt-4">
                        <button
                            type="button"
                            onClick={runAnalysis}
                            disabled={loading}
                            className="inline-flex items-center gap-2 rounded-[1rem] border border-cyan-300/40 bg-cyan-300/15 px-4 py-3 text-sm font-black text-cyan-50 shadow-[0_12px_34px_rgba(34,211,238,0.12)] transition hover:-translate-y-0.5 hover:border-cyan-200 hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:opacity-60"
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
                    </div>
                </section>

                <section className="h-[660px] overflow-hidden rounded-[2.25rem] border border-cyan-300/15 bg-[linear-gradient(160deg,rgba(8,47,73,0.28),rgba(2,6,23,0.98)_42%,rgba(15,23,42,0.96))] p-6 shadow-[0_24px_80px_rgba(2,6,23,0.55)]">
                    <article className="flex h-full flex-col overflow-y-auto pr-2">
                        <div className="flex items-start justify-between gap-5">
                            <div>
                                <div className="text-[11px] uppercase tracking-[0.24em] text-cyan-200">UX Snapshot</div>
                                <h2 className="mt-2 text-3xl font-black tracking-tight text-white">Analiz Karari</h2>
                                <p className="mt-3 text-sm leading-6 text-slate-300">
                                    {analysis?.overview ?? 'Screenshot analiz edilince ana karar, sayisal sinyaller ve ilk aksiyon burada tek bakista gorunur.'}
                                </p>
                            </div>
                            <span className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${summaryStatusClass}`}>
                                {summaryStatus}
                            </span>
                        </div>

                        <div className="mt-6 grid gap-5 lg:grid-cols-[180px_minmax(0,1fr)]">
                            <div className="relative flex aspect-square items-center justify-center rounded-full border border-cyan-300/20 bg-slate-950 shadow-[inset_0_0_40px_rgba(34,211,238,0.08)]">
                                <div
                                    className="absolute inset-3 rounded-full"
                                    style={{
                                        background: `conic-gradient(#67e8f9 ${Math.max(0, Math.min(100, Number(summaryScore) || 0)) * 3.6}deg, rgba(30,41,59,0.9) 0deg)`,
                                    }}
                                />
                                <div className="absolute inset-8 rounded-full bg-slate-950" />
                                <div className="relative text-center">
                                    <div className={`text-5xl font-black leading-none ${scoreTone(summaryScore)}`}>{summaryScore ?? '--'}</div>
                                    <div className="mt-2 text-[10px] uppercase tracking-[0.2em] text-slate-500">UX Score</div>
                                </div>
                            </div>

                            <div className="grid gap-3">
                                <div className="rounded-3xl border border-cyan-300/20 bg-cyan-300/10 px-5 py-4">
                                    <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-100">
                                        <Sparkles className="h-3.5 w-3.5" />
                                        Executive Signal
                                    </div>
                                    <p className="mt-3 text-sm leading-6 text-cyan-50">
                                        {analysis?.ai_critic_summary ?? 'AI yorum katmani analiz sonrasinda en onemli UX riskini ve ilk aksiyonu burada sade bir not olarak gosterir.'}
                                    </p>
                                </div>

                                <div className="grid grid-cols-3 gap-3">
                                    {summaryHighlights.map((item) => (
                                        <div key={item.label} className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3">
                                            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{item.label}</div>
                                            <div className="mt-1 break-words text-base font-black text-white">{item.value}</div>
                                            <div className="mt-1 break-words text-[11px] text-slate-500">{item.detail}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 grid gap-3">
                            {[
                                { label: 'Ana aksiyon', value: primaryActionText, tone: 'border-amber-300/20 bg-amber-300/10 text-amber-50' },
                                { label: 'Sayisal kanit', value: primaryEvidenceText, tone: 'border-sky-300/20 bg-sky-300/10 text-sky-50' },
                                { label: 'Kisa yorum', value: selectedFinding?.ai_critic || personaRisk?.summary || visualRegression?.summary || 'Detayli yorumlar asagidaki bulgu panellerinde incelenebilir.', tone: 'border-slate-700 bg-slate-900/80 text-slate-200' },
                            ].map((item) => (
                                <div key={item.label} className={`rounded-2xl border px-4 py-3 ${item.tone}`}>
                                    <div className="text-[10px] uppercase tracking-[0.18em] opacity-75">{item.label}</div>
                                    <p className="mt-1 text-sm leading-6">{item.value}</p>
                                </div>
                            ))}
                        </div>

                        <div className="mt-auto grid grid-cols-4 gap-3 pt-5">
                            {[
                                { label: 'Layout', value: analysis?.alignment_score },
                                { label: 'Spacing', value: analysis?.spacing_consistency_score },
                                { label: 'Color', value: colorIntel?.cta_visibility_score ?? colorIntel?.palette_consistency_score },
                                { label: 'Token', value: designTokens?.design_token_score },
                            ].map((item) => (
                                <div key={item.label} className="rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-3">
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="text-[10px] uppercase tracking-[0.16em] text-slate-500">{item.label}</span>
                                        <span className={`text-sm font-black ${scoreTone(item.value)}`}>{item.value ?? '--'}</span>
                                    </div>
                                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                                        <div
                                            className="h-full rounded-full bg-cyan-300"
                                            style={{ width: `${Math.max(0, Math.min(100, Number(item.value) || 0))}%` }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-5 space-y-4 border-t border-cyan-300/10 pt-5">
                        {analysis ? (
                            <div className="mt-4 rounded-2xl border border-sky-300/25 bg-sky-500/10 px-4 py-4 shadow-[0_10px_34px_rgba(14,165,233,0.08)]">
                                <div className="flex items-center justify-between gap-4">
                                    <div>
                                        <div className="text-xs uppercase tracking-[0.18em] text-sky-200">Platform-Aware Analysis</div>
                                        <div className="mt-2 text-sm font-semibold text-white">
                                            Detected: {(analysis.detected_platform || analysis.platform || 'web').toUpperCase()}
                                        </div>
                                    </div>
                                    <div className="rounded-full border border-sky-300/30 bg-sky-400/10 px-3 py-1 text-xs font-semibold text-sky-100">
                                        %{analysis.platform_confidence ?? '--'}
                                    </div>
                                </div>
                                <p className="mt-3 text-sm leading-6 text-sky-50">
                                    {analysis.platform_reason || 'Screenshot boyutu ve yerlesim sinyallerine gore platform profili secildi.'}
                                </p>
                                <div className="mt-3 flex flex-wrap gap-2">
                                    <span className="rounded-full border border-slate-700 bg-slate-950 px-2.5 py-1 text-[11px] text-slate-200">
                                        requested: {analysis.requested_platform || 'auto'}
                                    </span>
                                    <span className="rounded-full border border-slate-700 bg-slate-950 px-2.5 py-1 text-[11px] text-slate-200">
                                        profile: {analysis.platform_profile || 'unknown'}
                                    </span>
                                    {(analysis.platform_rules_applied || []).slice(0, 4).map((rule) => (
                                        <span key={rule} className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2.5 py-1 text-[11px] text-cyan-100">
                                            {rule}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        ) : null}

                        {taskEvaluation ? (
                            <div className="mt-4 rounded-2xl border border-violet-300/25 bg-violet-500/10 p-4 shadow-[0_10px_34px_rgba(139,92,246,0.08)]">
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <div className="text-xs uppercase tracking-[0.18em] text-violet-200">Task-Based UX Evaluation</div>
                                        <div className="mt-2 text-sm font-semibold text-white">
                                            {taskEvaluation.task_label || taskEvaluation.task_type}
                                        </div>
                                        <p className="mt-2 text-xs leading-5 text-violet-50/85">
                                            {taskEvaluation.summary}
                                        </p>
                                    </div>
                                    <span className="shrink-0 rounded-full border border-violet-300/30 bg-violet-400/10 px-3 py-1 text-xs font-semibold text-violet-100">
                                        %{taskEvaluation.confidence ?? '--'}
                                    </span>
                                </div>
                                <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Task Score</div>
                                        <div className={`mt-1 text-lg font-semibold ${scoreTone(taskEvaluation.task_score)}`}>{taskEvaluation.task_score ?? '--'}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Friction</div>
                                        <div className={`mt-1 text-lg font-semibold ${taskEvaluation.friction_score >= 50 ? 'text-red-200' : taskEvaluation.friction_score >= 35 ? 'text-amber-200' : 'text-emerald-200'}`}>
                                            {taskEvaluation.friction_score ?? '--'}
                                        </div>
                                    </div>
                                </div>
                                {taskEvaluation.checks?.length ? (
                                    <div className="mt-4 space-y-2">
                                        {taskEvaluation.checks.slice(0, 4).map((check) => (
                                            <div key={check.name} className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs">
                                                <span className="text-slate-200">{check.name}</span>
                                                <span className={check.status === 'pass' ? 'text-emerald-200' : 'text-amber-200'}>{check.status}</span>
                                            </div>
                                        ))}
                                    </div>
                                ) : null}
                                <div className="mt-4 rounded-xl border border-violet-300/20 bg-slate-950 px-3 py-3 text-xs leading-5 text-violet-50">
                                    {taskEvaluation.recommendation}
                                </div>
                            </div>
                        ) : null}

                        {personaRisk ? (
                            <div className="mt-4 rounded-2xl border border-rose-300/25 bg-rose-500/10 p-4 shadow-[0_10px_34px_rgba(244,63,94,0.08)]">
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <div className="text-xs uppercase tracking-[0.18em] text-rose-200">Persona-Based UX Risk</div>
                                        <div className="mt-2 text-sm font-semibold text-white">
                                            En riskli profil: {personaRisk.highest_risk_persona?.label || '--'}
                                        </div>
                                        <p className="mt-2 text-xs leading-5 text-rose-50/85">
                                            {personaRisk.summary}
                                        </p>
                                    </div>
                                    <span className="shrink-0 rounded-full border border-rose-300/30 bg-rose-400/10 px-3 py-1 text-xs font-semibold text-rose-100">
                                        %{personaRisk.overall_persona_risk ?? '--'}
                                    </span>
                                </div>
                                <div className="mt-4 grid gap-2 text-xs">
                                    {(personaRisk.personas || []).map((persona) => (
                                        <div key={persona.id} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3">
                                            <div className="flex items-center justify-between gap-3">
                                                <div className="font-semibold text-slate-100">{persona.label}</div>
                                                <div className={persona.risk_score >= 70 ? 'text-red-200' : persona.risk_score >= 45 ? 'text-amber-200' : 'text-emerald-200'}>
                                                    {persona.risk_score}
                                                </div>
                                            </div>
                                            <p className="mt-2 leading-5 text-slate-300">{persona.reason}</p>
                                            <div className="mt-2 flex flex-wrap gap-1.5">
                                                {persona.signals.slice(0, 3).map((signal) => (
                                                    <span key={signal} className="rounded-full border border-rose-300/20 bg-rose-400/10 px-2 py-0.5 text-[10px] text-rose-100">
                                                        {signal}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="mt-4 rounded-xl border border-rose-300/20 bg-slate-950 px-3 py-3 text-xs leading-5 text-rose-50">
                                    {personaRisk.highest_risk_persona?.recommendation || 'Persona bazli kritik akisi tekrar gozden gecir.'}
                                </div>
                            </div>
                        ) : null}

                        {visualRegression ? (
                            <div className={`mt-4 rounded-2xl border p-4 shadow-[0_10px_34px_rgba(15,23,42,0.28)] ${
                                visualRegression.status === 'regressed'
                                    ? 'border-red-400/20 bg-red-500/10'
                                    : visualRegression.status === 'improved'
                                        ? 'border-emerald-400/20 bg-emerald-500/10'
                                        : 'border-sky-400/20 bg-sky-500/10'
                            }`}>
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <div className="text-xs uppercase tracking-[0.18em] text-sky-100">Visual Regression</div>
                                        <div className="mt-2 text-sm font-semibold text-white">
                                            {visualRegression.status === 'no_baseline'
                                                ? 'Baseline bekleniyor'
                                                : visualRegression.status === 'regressed'
                                                    ? 'Onceki kayda gore gerileme var'
                                                    : visualRegression.status === 'improved'
                                                        ? 'Onceki kayda gore iyilesme var'
                                                        : 'Onceki kayda gore stabil'}
                                        </div>
                                        <p className="mt-2 text-xs leading-5 text-slate-100/85">
                                            {visualRegression.summary}
                                        </p>
                                    </div>
                                    <span className="shrink-0 rounded-full border border-white/20 bg-slate-950 px-3 py-1 text-xs font-semibold text-slate-100">
                                        {visualRegression.status}
                                    </span>
                                </div>

                                {visualRegression.status !== 'no_baseline' ? (
                                    <>
                                        <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
                                            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Baseline</div>
                                                <div className="mt-1 text-white">#{visualRegression.baseline_record_id ?? '--'}</div>
                                            </div>
                                            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Score Delta</div>
                                                <div className={`mt-1 font-semibold ${
                                                    (visualRegression.score_delta ?? 0) < 0 ? 'text-red-200' : (visualRegression.score_delta ?? 0) > 0 ? 'text-emerald-200' : 'text-slate-200'
                                                }`}>
                                                    {visualRegression.score_delta ?? '--'}
                                                </div>
                                            </div>
                                            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                                <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Pixel Change</div>
                                                <div className="mt-1 text-white">
                                                    {visualRegression.pixel_change_percent ?? '--'}%
                                                </div>
                                            </div>
                                        </div>

                                        {(visualRegression.regressions?.length || visualRegression.improvements?.length) ? (
                                            <div className="mt-4 space-y-2">
                                                {(visualRegression.regressions || visualRegression.improvements || []).slice(0, 3).map((item) => (
                                                    <div key={`${item.metric}-${item.delta}`} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-xs">
                                                        <div className="flex items-center justify-between gap-3">
                                                            <span className="text-slate-100">{item.label || metricLabel(item.metric)}</span>
                                                            <span className={item.delta < 0 ? 'text-red-200' : 'text-emerald-200'}>
                                                                {item.previous} {'->'} {item.current} ({item.delta > 0 ? '+' : ''}{item.delta})
                                                            </span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : null}
                                    </>
                                ) : null}

                                {visualRegression.recommendation ? (
                                    <div className="mt-4 rounded-xl border border-white/10 bg-slate-950 px-3 py-3 text-xs leading-5 text-slate-100">
                                        {visualRegression.recommendation}
                                    </div>
                                ) : null}
                            </div>
                        ) : null}

                        {designTokens ? (
                            <div className="mt-4 rounded-2xl border border-emerald-300/25 bg-emerald-500/10 p-4 shadow-[0_10px_34px_rgba(16,185,129,0.08)]">
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <div className="text-xs uppercase tracking-[0.18em] text-emerald-200">Design Token Consistency</div>
                                        <div className="mt-2 text-sm font-semibold text-white">
                                            Spacing, font, radius ve buton standardi
                                        </div>
                                        <p className="mt-2 text-xs leading-5 text-emerald-50/80">
                                            {designTokens.recommendation || 'Ekran tasarim sistemi tokenlariyla tutarlilik acisindan incelendi.'}
                                        </p>
                                    </div>
                                    <span className="shrink-0 rounded-full border border-emerald-300/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-100">
                                        %{designTokens.design_token_score ?? '--'}
                                    </span>
                                </div>
                                <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Spacing</div>
                                        <div className="mt-1 text-white">{designTokens.spacing_token_fit_score ?? '--'}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Font</div>
                                        <div className="mt-1 text-white">{designTokens.font_scale_score ?? '--'}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Radius</div>
                                        <div className="mt-1 text-white">{designTokens.radius_consistency_score ?? '--'}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Button</div>
                                        <div className="mt-1 text-white">{designTokens.button_consistency_score ?? '--'}</div>
                                    </div>
                                </div>
                            </div>
                        ) : null}

                        <div className="mt-5 grid grid-cols-2 gap-3">
                            <div className="rounded-2xl border border-slate-700/80 bg-slate-900/90 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Hizalama</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.alignment_score)}`}>{analysis?.alignment_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-700/80 bg-slate-900/90 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Bosluk</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.spacing_consistency_score)}`}>{analysis?.spacing_consistency_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-700/80 bg-slate-900/90 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Denge</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.layout_balance_score)}`}>{analysis?.layout_balance_score ?? '--'}</div>
                            </div>
                            <div className="rounded-2xl border border-slate-700/80 bg-slate-900/90 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
                                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Okunabilirlik</div>
                                <div className={`mt-2 text-2xl font-semibold ${scoreTone(analysis?.readability_score)}`}>{analysis?.readability_score ?? '--'}</div>
                            </div>
                        </div>
                        {analysis?.attention_prediction ? (
                            <div className="mt-5 rounded-2xl border border-slate-700/80 bg-slate-900/90 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
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

                        {colorIntel ? (
                            <div className="mt-5 rounded-2xl border border-fuchsia-300/25 bg-fuchsia-500/10 px-4 py-4 shadow-[0_10px_34px_rgba(217,70,239,0.08)]">
                                <div className="flex items-center justify-between gap-3">
                                    <div>
                                        <div className="text-xs uppercase tracking-[0.18em] text-fuchsia-200">Color Intelligence</div>
                                        <div className="mt-2 text-sm font-semibold text-white">Kontrast, CTA ve palet kontrolu</div>
                                    </div>
                                    <div className="rounded-full border border-fuchsia-300/30 bg-fuchsia-400/10 px-3 py-1 text-xs text-fuchsia-100">
                                        CTA {colorIntel.cta_visibility_score ?? '--'}
                                    </div>
                                </div>
                                <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Contrast</div>
                                        <div className="mt-1 text-white">{colorIntel.dominant_contrast_ratio ?? '--'}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Harmony</div>
                                        <div className="mt-1 text-white">{colorIntel.color_harmony_score ?? '--'}</div>
                                    </div>
                                    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">Palette</div>
                                        <div className="mt-1 text-white">{colorIntel.palette_consistency_score ?? '--'}</div>
                                    </div>
                                </div>
                                {(colorIntel.palette || colorIntel.dominant_palette || []).length ? (
                                    <div className="mt-4">
                                        <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Dominant palette</div>
                                        <div className="mt-2 flex flex-wrap gap-2">
                                            {(colorIntel.palette || colorIntel.dominant_palette || []).slice(0, 6).map((item) => (
                                                <span key={item.hex} className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-950 px-2.5 py-1 text-[11px] text-slate-200">
                                                    <span className="h-3 w-3 rounded-full border border-white/20" style={{ backgroundColor: item.hex }} />
                                                    {item.hex}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ) : null}
                                {(colorIntel.suggested_palette || []).length ? (
                                    <div className="mt-4">
                                        <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Suggested colors</div>
                                        <div className="mt-2 grid grid-cols-2 gap-2">
                                            {(colorIntel.suggested_palette || []).slice(0, 4).map((item) => (
                                                <div key={`${item.role}-${item.color}`} className="rounded-xl border border-slate-800 bg-slate-950 p-2">
                                                    <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{item.role}</div>
                                                    <div className="mt-1 flex items-center gap-2 text-xs text-white">
                                                        <span className="h-4 w-4 rounded border border-white/20" style={{ backgroundColor: item.color }} />
                                                        {item.color}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ) : null}
                                {colorIntel.recommendation ? (
                                    <div className="mt-4 rounded-xl border border-fuchsia-300/20 bg-slate-950 px-3 py-3 text-xs leading-5 text-fuchsia-50">
                                        {colorIntel.recommendation}
                                    </div>
                                ) : null}
                            </div>
                        ) : null}

                        {scoreBreakdownEntries.length ? (
                            <div className="mt-5 rounded-2xl border border-slate-700/80 bg-slate-900/90 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
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
                            <div className="mt-5 rounded-2xl border border-cyan-300/25 bg-cyan-400/10 px-4 py-4 shadow-[0_10px_34px_rgba(34,211,238,0.08)]">
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
                        </div>
                    </article>

                </section>
            </div>

            <section className="overflow-hidden rounded-[2.25rem] border border-cyan-300/15 bg-[linear-gradient(150deg,rgba(8,47,73,0.2),rgba(2,6,23,0.98)_50%,rgba(15,23,42,0.96))] shadow-[0_24px_80px_rgba(2,6,23,0.45)]">
                <div className="h-px bg-gradient-to-r from-transparent via-cyan-300/70 to-transparent" />
                <div className="p-6">
                <div className="flex items-center gap-3">
                    <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-2 text-cyan-100">
                        {selectedFinding ? <AlertTriangle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                    </div>
                    <div>
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Onizleme</div>
                        <h2 className="mt-1 text-xl font-semibold text-white">Secili Bulgu Detayi</h2>
                    </div>
                </div>

                {selectedFinding ? (
                    <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(300px,420px)_minmax(0,1fr)]">
                        <div className="overflow-hidden rounded-[1.75rem] border border-cyan-300/20 bg-slate-950 shadow-[0_18px_46px_rgba(2,6,23,0.55)]">
                            <img
                                src={`data:image/png;base64,${selectedFinding.crop_image_base64}`}
                                alt={`Finding ${selectedFinding.id}`}
                                className="h-full min-h-[260px] w-full object-contain"
                            />
                        </div>
                        <div className="grid gap-4 xl:grid-cols-3">
                            <div className="rounded-[1.35rem] border border-cyan-300/14 bg-slate-950/70 px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]">
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
                                <div className="mt-4 rounded-[1.15rem] border border-cyan-300/10 bg-slate-950 px-4 py-4">
                                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">AI UX Yorumu</div>
                                    <div className="mt-3 text-sm leading-6 text-slate-200">{selectedFinding.ai_critic}</div>
                                </div>
                            </div>
                            <div className="rounded-[1.35rem] border border-amber-300/20 bg-amber-500/10 px-4 py-4 shadow-[0_10px_34px_rgba(245,158,11,0.08)]">
                                <div className="text-xs uppercase tracking-[0.18em] text-amber-200">Neden Onemli</div>
                                <div className="mt-3 text-sm leading-6 text-amber-50">{selectedFinding.why_this_matters}</div>
                                <div className="mt-4 rounded-[1.15rem] border border-cyan-400/20 bg-cyan-400/10 px-4 py-4 text-sm leading-6 text-cyan-50">
                                    {selectedFinding.recommendation}
                                </div>
                            </div>
                            <div className="rounded-[1.35rem] border border-sky-300/20 bg-sky-400/10 px-4 py-4 shadow-[0_10px_34px_rgba(56,189,248,0.08)]">
                                <div className="text-xs uppercase tracking-[0.18em] text-sky-200">Sayisal Kanit</div>
                                <div className="mt-3 grid gap-3">
                                    <div className="rounded-[0.95rem] border border-slate-800 bg-slate-950 px-3 py-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Metrik</div>
                                        <div className="mt-1 text-xs text-white">{metricLabel(selectedMetricName)}</div>
                                    </div>
                                    <div className="rounded-[0.95rem] border border-slate-800 bg-slate-950 px-3 py-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Deger</div>
                                        <div className="mt-1 text-xs text-white">{evidenceValue(selectedFinding.numeric_evidence, 'value')}</div>
                                    </div>
                                    <div className="rounded-[0.95rem] border border-slate-800 bg-slate-950 px-3 py-3">
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
                </div>
            </section>

            <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                <article className="rounded-[2.25rem] border border-cyan-300/15 bg-[linear-gradient(155deg,rgba(8,47,73,0.16),rgba(2,6,23,0.98)_48%,rgba(15,23,42,0.96))] p-6 shadow-[0_20px_70px_rgba(2,6,23,0.42)]">
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
                                        ? 'border-cyan-300/50 bg-cyan-400/10 shadow-[0_0_28px_rgba(34,211,238,0.12)]'
                                        : 'border-cyan-300/10 bg-slate-950/65 hover:-translate-y-0.5 hover:border-cyan-300/25 hover:bg-slate-900/70'
                                }`}
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div>
                                        <div className="flex items-center gap-3">
                                            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-cyan-300/15 bg-cyan-300/10 text-sm font-semibold text-cyan-100">
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

                <article className="rounded-[2.25rem] border border-violet-300/15 bg-[linear-gradient(155deg,rgba(46,16,101,0.16),rgba(2,6,23,0.98)_45%,rgba(15,23,42,0.96))] p-6 shadow-[0_20px_70px_rgba(2,6,23,0.42)]">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Oneriler</div>
                    <h2 className="mt-2 text-xl font-semibold text-white">Hizli Iyilestirme Onerileri</h2>

                    <div className="mt-5 space-y-3">
                        {selectedFinding ? (
                            <>
                                    <div className="rounded-2xl border border-cyan-300/25 bg-cyan-400/10 px-4 py-4 shadow-[0_10px_34px_rgba(34,211,238,0.08)]">
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
                                    <div key={`recommendation-${finding.id}`} className="rounded-2xl border border-slate-800 bg-slate-900/90 px-4 py-4 transition hover:border-slate-600">
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
                                <div key={`${index}-${recommendation}`} className="rounded-2xl border border-violet-300/10 bg-slate-950/70 px-4 py-4 text-sm leading-6 text-slate-200">
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

            <section className="rounded-[2.25rem] border border-cyan-300/15 bg-[linear-gradient(155deg,rgba(8,47,73,0.14),rgba(2,6,23,0.98)_46%,rgba(15,23,42,0.96))] p-6 shadow-[0_20px_70px_rgba(2,6,23,0.42)]">
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
                        <div key={`${item.category}-${item.title}`} className="rounded-2xl border border-cyan-300/10 bg-slate-950/65 px-4 py-4 transition hover:-translate-y-0.5 hover:border-cyan-300/30">
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

            <section className="rounded-[2.25rem] border border-cyan-300/15 bg-[linear-gradient(155deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98)_50%,rgba(8,47,73,0.14))] p-6 shadow-[0_20px_70px_rgba(2,6,23,0.42)]">
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
                            className="overflow-hidden rounded-[1.5rem] border border-cyan-300/10 bg-slate-950/70 text-left shadow-[0_16px_42px_rgba(2,6,23,0.35)] transition hover:-translate-y-1 hover:border-cyan-300/35"
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
                                            className="h-full w-full object-cover transition duration-500 hover:scale-[1.03]"
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
