import { useEffect, useState } from 'react';
import axios from 'axios';
import {
    AlertTriangle,
    Eye,
    FileImage,
    GitBranch,
    History,
    Lightbulb,
    Lock,
    Pencil,
    ScanSearch,
    ShieldAlert,
    Sparkles,
    Star,
    Trash2,
    X,
} from 'lucide-react';

import {
    api,
    SecurityAnalysisResponse,
    SecurityAttackChain,
    SecurityAttackHypothesis,
    SecurityFinding,
    SecurityHistoryItem,
    SecuritySimulationResponse,
    SecurityRootCause,
} from '../services/api';

type LayerTab = 'visual' | 'surface' | 'hypotheses' | 'correlation';

function severityBadge(severity: string) {
    if (severity === 'high') return 'border-red-400/40 bg-red-500/10 text-red-200';
    if (severity === 'medium') return 'border-amber-400/40 bg-amber-500/10 text-amber-200';
    if (severity === 'low') return 'border-sky-400/40 bg-sky-500/10 text-sky-200';
    return 'border-emerald-400/40 bg-emerald-500/10 text-emerald-200';
}

function scoreTone(score?: number) {
    if (score === undefined) return 'text-slate-200';
    if (score < 45) return 'text-red-200';
    if (score < 75) return 'text-amber-200';
    return 'text-emerald-200';
}

function layerButton(active: boolean) {
    return active
        ? 'border-red-400/30 bg-red-500/10 text-red-100'
        : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500';
}

export function SecurityPage() {
    const [preview, setPreview] = useState<string | null>(null);
    const [analysis, setAnalysis] = useState<SecurityAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [urlInput, setUrlInput] = useState('');
    const [viewMode, setViewMode] = useState<'overlay' | 'source'>('overlay');
    const [activeTab, setActiveTab] = useState<LayerTab>('visual');
    const [selectedKey, setSelectedKey] = useState<string | null>(null);
    const [simulation, setSimulation] = useState<SecuritySimulationResponse | null>(null);
    const [simulating, setSimulating] = useState(false);
    const [historyItems, setHistoryItems] = useState<SecurityHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [renameTarget, setRenameTarget] = useState<SecurityHistoryItem | null>(null);
    const [renameValue, setRenameValue] = useState('');
    const [deleteTarget, setDeleteTarget] = useState<SecurityHistoryItem | null>(null);
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

    const resetSelection = (result: SecurityAnalysisResponse) => {
        setActiveTab('visual');
        setSelectedKey(result.visual_findings[0] ? `finding-${result.visual_findings[0].id}` : null);
    };

    const loadHistory = async () => {
        setHistoryLoading(true);
        try {
            const items = await api.getSecurityHistory(6);
            setHistoryItems(items);
        } catch (err) {
            console.warn('Security history yuklenemedi:', err);
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        loadHistory();
    }, []);

    const handleFile = (file: File | null) => {
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            const result = typeof reader.result === 'string' ? reader.result : null;
            setPreview(result);
            setAnalysis(null);
            setSimulation(null);
            setError(null);
            setSelectedKey(null);
            setViewMode('overlay');
            setActiveTab('visual');
        };
        reader.readAsDataURL(file);
    };

    const runImageAnalysis = async () => {
        if (!preview) {
            setError('Once analiz edilecek bir screenshot yukle.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const result = await api.analyzeSecurityImage(preview, 'web');
            setAnalysis(result);
            setSimulation(null);
            resetSelection(result);
            await loadHistory();
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Security analizi baslatilamadi.'));
        } finally {
            setLoading(false);
        }
    };

    const runUrlAnalysis = async () => {
        const trimmedUrl = urlInput.trim();
        if (!trimmedUrl) {
            setError('Once analiz edilecek bir URL gir.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const result = await api.analyzeSecurityUrl({
                url: trimmedUrl,
                platform: 'web',
                full_page: true,
            });
            const sourceImage = result.artifacts.source_image_base64 ? `data:image/png;base64,${result.artifacts.source_image_base64}` : null;
            setPreview(sourceImage);
            setAnalysis(result);
            setSimulation(null);
            resetSelection(result);
            setViewMode('overlay');
            await loadHistory();
        } catch (err) {
            setError(getRequestErrorMessage(err, 'URL tabanli security analizi baslatilamadi.'));
        } finally {
            setLoading(false);
        }
    };

    const openHistoryRecord = async (recordId: number) => {
        setLoading(true);
        setError(null);
        try {
            const detail = await api.getSecurityHistoryDetail(recordId);
            const sourceImage = detail.analysis.artifacts.source_image_base64 ? `data:image/png;base64,${detail.analysis.artifacts.source_image_base64}` : null;
            setPreview(sourceImage);
            setAnalysis(detail.analysis);
            setSimulation(null);
            resetSelection(detail.analysis);
            setViewMode('overlay');
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Kayitli security analizi acilamadi.'));
        } finally {
            setLoading(false);
        }
    };

    const openRenameHistoryModal = (item: SecurityHistoryItem) => {
        setRenameTarget(item);
        setRenameValue(item.source_label ?? '');
    };

    const renameHistoryRecord = async () => {
        if (!renameTarget) return;
        try {
            setHistoryModalBusy(true);
            const updatedRecord = await api.updateSecurityHistory(renameTarget.id, { source_label: renameValue });
            setHistoryItems((currentItems) => currentItems.map((item) => (item.id === updatedRecord.id ? updatedRecord : item)));
            setRenameTarget(null);
            setRenameValue('');
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Security kaydi guncellenemedi.'));
        } finally {
            setHistoryModalBusy(false);
        }
    };

    const toggleFavoriteHistoryRecord = async (item: SecurityHistoryItem) => {
        try {
            const updatedRecord = await api.updateSecurityHistory(item.id, { is_favorite: !item.is_favorite });
            setHistoryItems((currentItems) => currentItems.map((historyItem) => (historyItem.id === updatedRecord.id ? updatedRecord : historyItem)));
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Favori durumu guncellenemedi.'));
        }
    };

    const deleteHistoryRecord = async () => {
        if (!deleteTarget) return;
        try {
            setHistoryModalBusy(true);
            const deletedRecordId = deleteTarget.id;
            await api.deleteSecurityHistory(deletedRecordId);
            setHistoryItems((currentItems) => currentItems.filter((historyItem) => historyItem.id !== deletedRecordId));
            setDeleteTarget(null);
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Security kaydi silinemedi.'));
        } finally {
            setHistoryModalBusy(false);
        }
    };

    const runActiveSimulation = async () => {
        const targetUrl = urlInput.trim();
        if (!targetUrl) {
            setError('Active simulation icin once URL gir.');
            return;
        }
        setSimulating(true);
        setError(null);
        try {
            const result = await api.simulateSecurityUrl({
                url: targetUrl,
                platform: 'web',
                hypotheses: analysis?.attack_hypotheses.map((item) => item.attack_type) ?? [],
            });
            setSimulation(result);
        } catch (err) {
            setError(getRequestErrorMessage(err, 'Active simulation baslatilamadi.'));
        } finally {
            setSimulating(false);
        }
    };

    const imageSource = analysis
        ? `data:image/png;base64,${viewMode === 'overlay' ? analysis.artifacts.overlay_image_base64 : analysis.artifacts.source_image_base64}`
        : preview;

    const layerItems = analysis
        ? {
              visual: analysis.visual_findings.map((item) => ({ key: `finding-${item.id}`, item })),
              surface: analysis.surface_findings.map((item) => ({ key: `finding-${item.id}`, item })),
              hypotheses: analysis.attack_hypotheses.map((item) => ({ key: `hypothesis-${item.id}`, item })),
              correlation: [
                  ...analysis.attack_chains.map((item) => ({ key: `chain-${item.id}`, item })),
                  ...analysis.root_causes.map((item) => ({ key: `root-${item.id}`, item })),
              ],
          }
        : { visual: [], surface: [], hypotheses: [], correlation: [] };

    const currentItems = layerItems[activeTab];
    const selectedEntry = currentItems.find((entry) => entry.key === selectedKey) ?? currentItems[0] ?? null;
    const layerTabs: Array<{ key: LayerTab; label: string; score?: number; count?: number }> = [
        { key: 'visual', label: 'Visual', score: analysis?.visual_score, count: analysis?.visual_findings.length },
        { key: 'surface', label: 'Surface', score: analysis?.surface_score, count: analysis?.surface_findings.length },
        { key: 'hypotheses', label: 'Hypotheses', score: analysis?.hypothesis_score, count: analysis?.attack_hypotheses.length },
        { key: 'correlation', label: 'Correlation', score: analysis?.correlation_score, count: (analysis?.attack_chains.length ?? 0) + (analysis?.root_causes.length ?? 0) },
    ];

    const renderSelectedContent = () => {
        if (!selectedEntry) {
            return (
                <div className="mt-5 rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                    Henuz secilecek bir security intelligence kaydi yok.
                </div>
            );
        }

        if (selectedEntry.key.startsWith('finding-')) {
            const finding = selectedEntry.item as SecurityFinding;
            return (
                <div className="mt-5">
                    <div className="overflow-hidden rounded-[1.5rem] border border-slate-800 bg-slate-900">
                        <img src={`data:image/png;base64,${finding.crop_image_base64}`} alt={finding.title} className="h-56 w-full object-cover" />
                    </div>
                    <div className="mt-4 flex items-start justify-between gap-4">
                        <div>
                            <div className="text-base font-semibold text-white">{finding.title}</div>
                            <div className="mt-1 text-sm text-slate-400">Layer: {finding.layer} · Kategori: {finding.category}</div>
                        </div>
                        <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(finding.severity)}`}>{finding.severity}</div>
                    </div>
                    <p className="mt-4 text-sm leading-6 text-slate-300">{finding.description}</p>
                    {finding.evidence ? <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4 text-sm leading-6 text-slate-200">Kanit: {finding.evidence}</div> : null}
                    <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-4 text-sm leading-6 text-red-50">{finding.recommendation}</div>
                </div>
            );
        }

        if (selectedEntry.key.startsWith('hypothesis-')) {
            const hypothesis = selectedEntry.item as SecurityAttackHypothesis;
            return (
                <div className="mt-5 space-y-4">
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <div className="text-base font-semibold text-white">{hypothesis.title}</div>
                            <div className="mt-1 text-sm text-slate-400">Attack: {hypothesis.attack_type} · Context: {hypothesis.inferred_context} · Surface: {hypothesis.target_surface}</div>
                        </div>
                        <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(hypothesis.severity)}`}>{hypothesis.severity}</div>
                    </div>
                    <p className="text-sm leading-6 text-slate-300">{hypothesis.rationale}</p>
                    <div className="grid gap-3 lg:grid-cols-2">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Confidence</div>
                            <div className="mt-2 text-2xl font-semibold text-white">%{hypothesis.confidence}</div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Priority</div>
                            <div className="mt-2 text-2xl font-semibold text-white">P{hypothesis.priority}</div>
                        </div>
                    </div>
                    <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4 text-sm leading-6 text-slate-200">Onerilen test: {hypothesis.recommended_test}</div>
                    <div className="grid gap-3 lg:grid-cols-2">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Evidence</div>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{hypothesis.evidence.map((item, index) => <div key={`${index}-${item}`}>{item}</div>)}</div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Preconditions</div>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{hypothesis.preconditions.map((item, index) => <div key={`${index}-${item}`}>{item}</div>)}</div>
                        </div>
                    </div>
                    <div className="grid gap-3 lg:grid-cols-2">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Payload Families</div>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{hypothesis.payload_families.map((item, index) => <div key={`${index}-${item}`}>{item}</div>)}</div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Role Scenarios</div>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{hypothesis.role_scenarios.map((item, index) => <div key={`${index}-${item}`}>{item}</div>)}</div>
                        </div>
                    </div>
                    <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Attack Playbook</div>
                        <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{hypothesis.playbook_steps.map((item, index) => <div key={`${index}-${item}`}>{index + 1}. {item}</div>)}</div>
                    </div>
                </div>
            );
        }

        if (selectedEntry.key.startsWith('chain-')) {
            const chain = selectedEntry.item as SecurityAttackChain;
            return (
                <div className="mt-5 space-y-4">
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <div className="text-base font-semibold text-white">{chain.title}</div>
                            <div className="mt-1 text-sm text-slate-400">Layers: {chain.linked_layers.join(' -> ')} · Confidence: %{chain.confidence}</div>
                        </div>
                        <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(chain.severity)}`}>{chain.severity}</div>
                    </div>
                    <p className="text-sm leading-6 text-slate-300">{chain.summary}</p>
                    <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4 text-sm leading-6 text-slate-200">
                        Linked hypotheses: {chain.linked_hypothesis_ids.join(', ') || '--'} · Linked findings: {chain.linked_finding_ids.join(', ') || '--'} · Modules: {chain.linked_modules.join(', ') || '--'}
                    </div>
                    <div className="grid gap-3">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Attack Path</div>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{chain.attack_path.map((item, index) => <div key={`${index}-${item}`}>{index + 1}. {item}</div>)}</div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Remediation</div>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{chain.remediation_path.map((item, index) => <div key={`${index}-${item}`}>{item}</div>)}</div>
                        </div>
                    </div>
                </div>
            );
        }

        const rootCause = selectedEntry.item as SecurityRootCause;
        return (
            <div className="mt-5 space-y-4">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <div className="text-base font-semibold text-white">{rootCause.title}</div>
                        <div className="mt-1 text-sm text-slate-400">Taxonomy: {rootCause.taxonomy} · Confidence: %{rootCause.confidence}</div>
                    </div>
                    <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(rootCause.severity)}`}>{rootCause.severity}</div>
                </div>
                <p className="text-sm leading-6 text-slate-300">{rootCause.summary}</p>
                <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4 text-sm leading-6 text-slate-200">Linked categories: {rootCause.linked_categories.join(', ')}</div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Recommendations</div>
                    <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{rootCause.recommendations.map((item, index) => <div key={`${index}-${item}`}>{item}</div>)}</div>
                </div>
                <div className="grid gap-3 lg:grid-cols-3">
                    {Object.entries(rootCause.remediation_bundles).map(([bundle, items]) => (
                        <div key={bundle} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-500">{bundle}</div>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-200">{items.map((item, index) => <div key={`${index}-${item}`}>{item}</div>)}</div>
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-8">
            <section className="overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950">
                <div className="relative isolate overflow-hidden px-8 py-10 md:px-10">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(239,68,68,0.16),_transparent_34%),radial-gradient(circle_at_bottom_right,_rgba(251,191,36,0.14),_transparent_26%)]" />
                    <div className="relative z-10 flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
                        <div className="max-w-3xl">
                            <div className="inline-flex items-center gap-2 rounded-full border border-red-400/20 bg-red-500/10 px-3 py-1 text-xs uppercase tracking-[0.24em] text-red-100">
                                <Sparkles className="h-3.5 w-3.5" />
                                4.5 Security Intelligence Framework
                            </div>
                            <h1 className="mt-4 flex items-center gap-3 text-4xl font-bold tracking-tight text-white">
                                <ShieldAlert className="h-9 w-9 text-red-300" />
                                Katmanli Security Intelligence
                            </h1>
                            <p className="mt-3 max-w-2xl text-base leading-7 text-slate-300">
                                Visual exposure, surface audit, AI attack hypotheses ve attack correlation katmanlarini tek modulde birlestir.
                            </p>
                        </div>
                        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-400">Overall</div><div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.overall_score)}`}>{analysis?.overall_score ?? '--'}</div></div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-400">Visual</div><div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.visual_score)}`}>{analysis?.visual_score ?? '--'}</div></div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-400">Surface</div><div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.surface_score)}`}>{analysis?.surface_score ?? '--'}</div></div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-400">Hypotheses</div><div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.hypothesis_score)}`}>{analysis?.hypothesis_score ?? '--'}</div></div>
                            <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-400">Correlation</div><div className={`mt-2 text-3xl font-bold ${scoreTone(analysis?.correlation_score)}`}>{analysis?.correlation_score ?? '--'}</div></div>
                        </div>
                    </div>
                </div>
            </section>

            <div className="grid items-start gap-8 xl:grid-cols-[1.2fr_0.95fr]">
                <section className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="grid gap-5 border-b border-slate-800 pb-6 lg:grid-cols-[1fr_auto]">
                        <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Inputs</div>
                            <h2 className="mt-2 text-xl font-semibold text-white">Visual ve Surface toplama</h2>
                            <p className="mt-2 text-sm leading-6 text-slate-400">Screenshot tarafinda visual exposure, URL tarafinda response/header sinyalleri toplanir; ardindan hypotheses ve correlation katmani uretilir.</p>
                        </div>
                        <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm font-medium text-slate-200 transition hover:border-slate-500">
                            <FileImage className="h-4 w-4" />
                            Screenshot Sec
                            <input type="file" accept="image/*" className="hidden" onChange={(event) => handleFile(event.target.files?.[0] ?? null)} />
                        </label>
                    </div>

                    <div className="mt-5 grid gap-4 border-b border-slate-800 pb-6">
                        <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">URL v2</div>
                            <div className="mt-2 flex flex-col gap-3 lg:flex-row">
                                <input type="text" value={urlInput} onChange={(event) => setUrlInput(event.target.value)} placeholder="https://example.com/login" className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-red-400/40" />
                                <button type="button" onClick={runUrlAnalysis} disabled={loading} className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm font-semibold text-amber-100 transition hover:border-amber-300/50 hover:bg-amber-500/15 disabled:cursor-not-allowed disabled:opacity-60">
                                    URL Analizi
                                </button>
                                <button type="button" onClick={runActiveSimulation} disabled={simulating || !urlInput.trim()} className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm font-semibold text-red-100 transition hover:border-red-300/50 hover:bg-red-500/15 disabled:cursor-not-allowed disabled:opacity-60">
                                    {simulating ? 'Probe calisiyor...' : 'Active Simulation'}
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="mt-6 overflow-hidden rounded-[1.5rem] border border-dashed border-slate-700 bg-slate-900/50">
                        {imageSource ? (
                            <img src={imageSource} alt="Security preview" className="w-full object-contain" />
                        ) : (
                            <div className="flex min-h-[360px] flex-col items-center justify-center px-6 text-center">
                                <div className="rounded-full border border-red-400/20 bg-red-500/10 p-5 text-red-200"><ScanSearch className="h-8 w-8" /></div>
                                <div className="mt-5 text-lg font-semibold text-white">Bir screenshot veya URL ver</div>
                                <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">Modul once visual ve surface kanit toplar; sonra AI saldiri hipotezleri ve attack chain yorumlari uretir.</p>
                            </div>
                        )}
                    </div>

                    <div className="mt-5 flex flex-wrap gap-3">
                        <button type="button" onClick={runImageAnalysis} disabled={loading} className="inline-flex items-center gap-2 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm font-semibold text-red-100 transition hover:border-red-300/50 hover:bg-red-500/15 disabled:cursor-not-allowed disabled:opacity-60">
                            <Lock className="h-4 w-4" />
                            {loading ? 'Analiz ediliyor...' : 'Security Analizini Baslat'}
                        </button>
                        {analysis ? (
                            <>
                                <button type="button" onClick={() => setViewMode('overlay')} className={`inline-flex items-center gap-2 rounded-xl border px-4 py-3 text-sm transition ${layerButton(viewMode === 'overlay')}`}>
                                    <Eye className="h-4 w-4" />
                                    Overlay
                                </button>
                                <button type="button" onClick={() => setViewMode('source')} className={`inline-flex items-center gap-2 rounded-xl border px-4 py-3 text-sm transition ${layerButton(viewMode === 'source')}`}>
                                    <Eye className="h-4 w-4" />
                                    Temiz Screenshot
                                </button>
                            </>
                        ) : null}
                    </div>

                    {error ? <div className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</div> : null}
                </section>

                <section className="space-y-6">
                    <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Summary</div>
                        <h2 className="mt-2 text-xl font-semibold text-white">Standart Security Ciktisi</h2>
                        <p className="mt-4 text-sm leading-6 text-slate-300">{analysis?.overview ?? 'Bu alanda moduller birlestirilmis security intelligence ozetini goreceksin.'}</p>
                        <div className="mt-5 grid grid-cols-2 gap-3">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Findings</div><div className="mt-2 text-2xl font-semibold text-white">{analysis?.findings.length ?? '--'}</div></div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Missing Headers</div><div className="mt-2 text-2xl font-semibold text-amber-200">{analysis?.header_summary?.missing ?? '--'}</div></div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Hypotheses</div><div className="mt-2 text-2xl font-semibold text-white">{analysis?.attack_hypotheses.length ?? '--'}</div></div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Chains + Root Causes</div><div className="mt-2 text-2xl font-semibold text-white">{((analysis?.attack_chains.length ?? 0) + (analysis?.root_causes.length ?? 0)) || '--'}</div></div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Primary Context</div><div className="mt-2 text-lg font-semibold text-white">{analysis?.context_profile?.primary_context ?? '--'}</div></div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Attack Readiness</div><div className="mt-2 text-2xl font-semibold text-red-100">%{analysis?.context_profile?.attack_readiness ?? '--'}</div></div>
                        </div>
                    </article>

                    <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                        <div className="flex items-center gap-3">
                            <div className="rounded-full border border-slate-700 bg-slate-900 p-2 text-slate-200"><AlertTriangle className="h-4 w-4" /></div>
                            <div>
                                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Preview</div>
                                <h2 className="mt-1 text-xl font-semibold text-white">Secili Kayit</h2>
                            </div>
                        </div>
                        {renderSelectedContent()}
                    </article>
                </section>
            </div>

            <section className="grid gap-8 xl:grid-cols-[1.05fr_0.95fr]">
                <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Active Simulation</div>
                    <h2 className="mt-2 text-xl font-semibold text-white">Kontrollu probe starter</h2>
                    <p className="mt-3 text-sm leading-6 text-slate-300">
                        Bu katman hipotezlere gore guvenli ve hafif probe'lar calistirir. Tam exploit yapmaz; reflection, SQL-like davranis, method discovery ve bazi IDOR sinyallerini olcer.
                    </p>
                    <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Signal</div><div className={`mt-2 text-2xl font-semibold ${simulation?.overall_signal === 'high' ? 'text-red-200' : simulation?.overall_signal === 'medium' ? 'text-amber-200' : 'text-sky-200'}`}>{simulation?.overall_signal ?? '--'}</div></div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Executed</div><div className="mt-2 text-2xl font-semibold text-white">{simulation?.executed_count ?? '--'}</div></div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Blocked</div><div className="mt-2 text-2xl font-semibold text-amber-200">{simulation?.blocked_count ?? '--'}</div></div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4"><div className="text-xs uppercase tracking-[0.18em] text-slate-500">Probes</div><div className="mt-2 text-2xl font-semibold text-white">{simulation?.probes.length ?? '--'}</div></div>
                    </div>
                    <div className="mt-5 space-y-3">
                        {simulation?.probes.length ? simulation.probes.map((probe) => (
                            <div key={probe.id} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="flex items-start justify-between gap-4">
                                    <div>
                                        <div className="text-base font-semibold text-white">{probe.probe_type}</div>
                                        <div className="mt-2 text-sm leading-6 text-slate-300">{probe.summary}</div>
                                        <div className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">{probe.request_preview}</div>
                                        <div className="mt-3 space-y-1 text-sm text-slate-200">{probe.evidence.map((item, index) => <div key={`${probe.id}-${index}`}>{item}</div>)}</div>
                                    </div>
                                    <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge(probe.severity)}`}>{probe.status}</div>
                                </div>
                                <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm leading-6 text-slate-200">{probe.next_step}</div>
                            </div>
                        )) : (
                            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                                URL verdikten sonra `Active Simulation` ile kontrollu probe sonuclarini burada goreceksin.
                            </div>
                        )}
                    </div>
                </article>

                <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Probe Recommendations</div>
                    <h2 className="mt-2 text-xl font-semibold text-white">Derinlestirme adimlari</h2>
                    <div className="mt-5 space-y-3">
                        {(simulation?.recommendations ?? []).length ? simulation?.recommendations.map((recommendation, index) => (
                            <div key={`${index}-${recommendation}`} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4 text-sm leading-6 text-slate-200">
                                {recommendation}
                            </div>
                        )) : (
                            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                                Active simulation sonrasi takip probe onerileri burada listelenecek.
                            </div>
                        )}
                    </div>
                </article>
            </section>

            <section className="grid gap-8 xl:grid-cols-[1.05fr_0.95fr]">
                <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Cross-Module</div>
                    <h2 className="mt-2 text-xl font-semibold text-white">API / DB / Scenario baglari</h2>
                    <div className="mt-5 space-y-3">
                        {(analysis?.cross_module_hints ?? []).length ? analysis?.cross_module_hints.map((hint, index) => (
                            <div key={`${hint.module}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4">
                                <div className="flex items-start justify-between gap-4">
                                    <div>
                                        <div className="text-base font-semibold text-white">{hint.module}</div>
                                        <div className="mt-2 text-sm leading-6 text-slate-300">{hint.reason}</div>
                                    </div>
                                    <div className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs font-medium text-slate-200">P{hint.priority}</div>
                                </div>
                                <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm leading-6 text-slate-200">{hint.suggested_action}</div>
                            </div>
                        )) : (
                            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                                Security analizi sonrasi API ve DB tarafina yonelik takip modulleri burada onerilecek.
                            </div>
                        )}
                    </div>
                </article>

                <article className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                    <div className="flex items-center justify-between gap-4">
                        <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-slate-500">History</div>
                            <h2 className="mt-2 flex items-center gap-3 text-xl font-semibold text-white">
                                <History className="h-5 w-5 text-red-300" />
                                Kaydedilen Security Analizleri
                            </h2>
                        </div>
                        <button type="button" onClick={loadHistory} className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-300 transition hover:border-slate-500">Yenile</button>
                    </div>
                    <div className="mt-5 grid grid-cols-1 gap-4">
                        {historyItems.length ? historyItems.map((item) => (
                            <article key={item.id} className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
                                <button type="button" onClick={() => openHistoryRecord(item.id)} className="block w-full text-left">
                                    <div className="flex items-start justify-between gap-4 p-4">
                                        <div className="min-w-0">
                                            <div className="truncate text-sm font-semibold text-white">{item.source_label ?? item.source_url ?? 'Security analizi'}</div>
                                            <div className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{item.source_type}</div>
                                            <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-300">{item.overview}</p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {item.is_favorite ? <span className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-amber-400/40 bg-amber-500/10 text-amber-200"><Star className="h-4 w-4 fill-current" /></span> : null}
                                            <div className={`rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs font-medium ${scoreTone(item.overall_score)}`}>{item.overall_score}</div>
                                        </div>
                                    </div>
                                </button>
                                <div className="border-t border-slate-800 px-4 py-4">
                                    <div className="flex flex-wrap gap-2">
                                        <button type="button" onClick={() => toggleFavoriteHistoryRecord(item)} className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs transition ${item.is_favorite ? 'border-amber-400/40 bg-amber-500/10 text-amber-200' : 'border-slate-700 bg-slate-950 text-slate-300 hover:border-slate-500'}`}>
                                            <Star className={`h-3.5 w-3.5 ${item.is_favorite ? 'fill-current' : ''}`} />
                                            {item.is_favorite ? 'Favoriden Cikar' : 'Favorile'}
                                        </button>
                                        <button type="button" onClick={() => openRenameHistoryModal(item)} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 transition hover:border-slate-500"><Pencil className="h-3.5 w-3.5" />Yeniden Adlandir</button>
                                        <button type="button" onClick={() => setDeleteTarget(item)} className="inline-flex items-center gap-2 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-xs text-red-200 transition hover:border-red-300/50"><Trash2 className="h-3.5 w-3.5" />Sil</button>
                                    </div>
                                </div>
                            </article>
                        )) : (
                            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">
                                {historyLoading ? 'Kaydedilen security analizleri yukleniyor...' : 'Henuz kaydedilmis security analizi yok.'}
                            </div>
                        )}
                    </div>
                </article>
            </section>

            <section className="rounded-[2rem] border border-slate-800 bg-slate-950 p-6">
                <div className="flex flex-wrap gap-3">
                    {layerTabs.map((tab) => (
                        <button
                            key={tab.key}
                            type="button"
                            onClick={() => {
                                setActiveTab(tab.key);
                                setSelectedKey(layerItems[tab.key][0]?.key ?? null);
                            }}
                            className={`rounded-2xl border px-4 py-3 text-left transition ${layerButton(activeTab === tab.key)}`}
                        >
                            <div className="text-xs uppercase tracking-[0.18em] text-slate-400">{tab.label}</div>
                            <div className="mt-1 text-lg font-semibold text-white">{tab.count ?? '--'} kayit</div>
                            <div className={`text-sm ${scoreTone(tab.score)}`}>Skor {tab.score ?? '--'}</div>
                        </button>
                    ))}
                </div>

                <div className="mt-6 grid gap-8 xl:grid-cols-[1.05fr_0.95fr]">
                    <article className="rounded-[1.6rem] border border-slate-800 bg-slate-950/80 p-5">
                        <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Layer Summary</div>
                        <h3 className="mt-2 text-lg font-semibold text-white">{activeTab} layer</h3>
                        <p className="mt-3 text-sm leading-6 text-slate-300">{analysis?.layer_summary?.[activeTab]?.overview ?? 'Bu sekmede secili katmanin detayli security intelligence kayitlari listelenir.'}</p>
                        <div className="mt-5 space-y-3">
                            {currentItems.length ? currentItems.map((entry, index) => (
                                <button key={entry.key} type="button" onClick={() => setSelectedKey(entry.key)} className={`w-full rounded-2xl border p-4 text-left transition ${selectedKey === entry.key || (!selectedKey && index === 0) ? 'border-red-300 bg-red-500/10' : 'border-slate-800 bg-slate-900 hover:border-slate-700'}`}>
                                    {entry.key.startsWith('finding-') ? (
                                        <div className="flex items-start justify-between gap-4">
                                            <div>
                                                <div className="text-base font-semibold text-white">{(entry.item as SecurityFinding).title}</div>
                                                <div className="mt-2 text-sm leading-6 text-slate-300">{(entry.item as SecurityFinding).description}</div>
                                            </div>
                                            <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge((entry.item as SecurityFinding).severity)}`}>{(entry.item as SecurityFinding).severity}</div>
                                        </div>
                                    ) : entry.key.startsWith('hypothesis-') ? (
                                        <div className="flex items-start justify-between gap-4">
                                            <div>
                                                <div className="text-base font-semibold text-white">{(entry.item as SecurityAttackHypothesis).title}</div>
                                                <div className="mt-2 text-sm leading-6 text-slate-300">{(entry.item as SecurityAttackHypothesis).rationale}</div>
                                            </div>
                                            <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge((entry.item as SecurityAttackHypothesis).severity)}`}>{(entry.item as SecurityAttackHypothesis).severity}</div>
                                        </div>
                                    ) : entry.key.startsWith('chain-') ? (
                                        <div className="flex items-start justify-between gap-4">
                                            <div>
                                                <div className="text-base font-semibold text-white">{(entry.item as SecurityAttackChain).title}</div>
                                                <div className="mt-2 text-sm leading-6 text-slate-300">{(entry.item as SecurityAttackChain).summary}</div>
                                            </div>
                                            <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge((entry.item as SecurityAttackChain).severity)}`}>{(entry.item as SecurityAttackChain).severity}</div>
                                        </div>
                                    ) : (
                                        <div className="flex items-start justify-between gap-4">
                                            <div>
                                                <div className="text-base font-semibold text-white">{(entry.item as SecurityRootCause).title}</div>
                                                <div className="mt-2 text-sm leading-6 text-slate-300">{(entry.item as SecurityRootCause).summary}</div>
                                            </div>
                                            <div className={`rounded-full border px-3 py-1 text-xs font-medium ${severityBadge((entry.item as SecurityRootCause).severity)}`}>{(entry.item as SecurityRootCause).severity}</div>
                                        </div>
                                    )}
                                </button>
                            )) : (
                                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">Bu katmanda henuz kayit yok.</div>
                            )}
                        </div>
                    </article>

                    <article className="rounded-[1.6rem] border border-slate-800 bg-slate-950/80 p-5">
                        <div className="flex items-center gap-3">
                            <div className="rounded-full border border-slate-700 bg-slate-900 p-2 text-slate-200">{activeTab === 'correlation' ? <GitBranch className="h-4 w-4" /> : activeTab === 'hypotheses' ? <Lightbulb className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}</div>
                            <div>
                                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">Recommendations</div>
                                <h3 className="mt-1 text-lg font-semibold text-white">Oncelikli aksiyonlar</h3>
                            </div>
                        </div>
                        <div className="mt-5 space-y-3">
                            {(analysis?.recommendations ?? []).length ? analysis?.recommendations.map((recommendation, index) => (
                                <div key={`${index}-${recommendation}`} className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-4 text-sm leading-6 text-slate-200">{recommendation}</div>
                            )) : (
                                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 px-5 py-8 text-sm text-slate-500">Analiz sonrasi security aksiyonlari burada listelenecek.</div>
                            )}
                        </div>
                    </article>
                </div>
            </section>

            {(renameTarget || deleteTarget) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
                    <div className="w-full max-w-lg rounded-[2rem] border border-slate-800 bg-slate-950 p-6 shadow-2xl">
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <div className="text-xs uppercase tracking-[0.2em] text-slate-500">History Action</div>
                                <h2 className="mt-2 text-2xl font-semibold text-white">{renameTarget ? 'Kaydi Yeniden Adlandir' : 'Kaydi Sil'}</h2>
                            </div>
                            <button type="button" onClick={() => { if (historyModalBusy) return; setRenameTarget(null); setDeleteTarget(null); setRenameValue(''); }} className="rounded-full border border-slate-700 bg-slate-900 p-2 text-slate-400 transition hover:border-slate-500 hover:text-white">
                                <X className="h-4 w-4" />
                            </button>
                        </div>
                        {renameTarget ? (
                            <div className="mt-6 space-y-4">
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 px-4 py-3">
                                    <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Mevcut Kayit</div>
                                    <div className="mt-2 truncate text-sm text-white">{renameTarget.source_label ?? renameTarget.source_url ?? 'Security analizi'}</div>
                                </div>
                                <input type="text" value={renameValue} onChange={(event) => setRenameValue(event.target.value)} className="w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-red-400/50" placeholder="Kayit adi" />
                                <div className="flex justify-end gap-3">
                                    <button type="button" onClick={() => { setRenameTarget(null); setRenameValue(''); }} disabled={historyModalBusy} className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-300 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60">Vazgec</button>
                                    <button type="button" onClick={renameHistoryRecord} disabled={historyModalBusy} className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-100 transition hover:border-red-300/50 hover:bg-red-500/15 disabled:cursor-not-allowed disabled:opacity-60">{historyModalBusy ? 'Kaydediliyor...' : 'Kaydi Guncelle'}</button>
                                </div>
                            </div>
                        ) : deleteTarget ? (
                            <div className="mt-6 space-y-5">
                                <div className="rounded-2xl border border-red-400/20 bg-red-500/5 px-4 py-4 text-sm leading-6 text-slate-200">
                                    <span className="font-semibold text-white">{deleteTarget.source_label ?? deleteTarget.source_url ?? 'Security analizi'}</span> kaydini silmek uzeresin. Bu islem geri alinmaz.
                                </div>
                                <div className="flex justify-end gap-3">
                                    <button type="button" onClick={() => setDeleteTarget(null)} disabled={historyModalBusy} className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-300 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60">Vazgec</button>
                                    <button type="button" onClick={deleteHistoryRecord} disabled={historyModalBusy} className="rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-200 transition hover:border-red-300/50 hover:bg-red-500/15 disabled:cursor-not-allowed disabled:opacity-60">{historyModalBusy ? 'Siliniyor...' : 'Kaydi Sil'}</button>
                                </div>
                            </div>
                        ) : null}
                    </div>
                </div>
            )}
        </div>
    );
}

export default SecurityPage;
