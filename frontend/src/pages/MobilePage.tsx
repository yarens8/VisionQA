import { useEffect, useRef, useState } from 'react';
import { Clock, Loader2, RefreshCw, Smartphone, Sparkles, Wand2 } from 'lucide-react';

import { api, AnalysisJobStatusResponse, MobileAnalysisResponse, MobileHistoryItem, Project } from '../services/api';
import { readableErrorMessage } from '../utils/errors';

const severityClasses: Record<string, string> = {
    high: 'border-red-500/40 bg-red-500/10 text-red-200',
    medium: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
    low: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
};

const sampleMetadata = JSON.stringify(
    [
        { element_type: 'input', x: 20, y: 84, width: 280, height: 42, text_content: 'Email address' },
        { element_type: 'input', x: 20, y: 138, width: 280, height: 42, text_content: 'Password' },
        { element_type: 'button', x: 20, y: 196, width: 40, height: 38, text_content: 'Continue' },
        { element_type: 'button', x: 72, y: 196, width: 40, height: 38, text_content: 'Help' },
        { element_type: 'button', x: 124, y: 196, width: 40, height: 38, text_content: 'Google' },
        { element_type: 'button', x: 176, y: 196, width: 40, height: 38, text_content: 'Apple' },
        { element_type: 'link', x: 20, y: 258, width: 110, height: 24, text_content: 'Forgot password?' },
    ],
    null,
    2,
);

export function MobilePage() {
    const [platform, setPlatform] = useState('android');
    const [screenName, setScreenName] = useState('Login Screen');
    const [metadata, setMetadata] = useState(sampleMetadata);
    const [imageBase64, setImageBase64] = useState<string | undefined>(undefined);
    const [preview, setPreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<MobileAnalysisResponse | null>(null);
    const [jobStatus, setJobStatus] = useState<AnalysisJobStatusResponse | null>(null);
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState('');
    const [historyItems, setHistoryItems] = useState<MobileHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const activeJobRef = useRef<number | null>(null);
    const selectedProject = projects.find((project) => String(project.id) === selectedProjectId);

    const loadHistory = async (projectId = selectedProjectId) => {
        setHistoryLoading(true);
        try {
            const items = await api.getMobileHistory(projectId ? Number(projectId) : undefined, 12);
            setHistoryItems(items);
        } catch (error) {
            console.warn('Mobile history could not be loaded', error);
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        api.getProjects()
            .then(setProjects)
            .catch((error) => console.warn('Projects could not be loaded for mobile module', error));
        loadHistory('');
        return () => {
            activeJobRef.current = null;
        };
    }, []);

    useEffect(() => {
        loadHistory(selectedProjectId);
    }, [selectedProjectId]);

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) {
            setImageBase64(undefined);
            setPreview(null);
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            const output = String(reader.result || '');
            const [, base64] = output.split(',');
            setPreview(output);
            setImageBase64(base64);
        };
        reader.readAsDataURL(file);
    };

    const handleAnalyze = async () => {
        setLoading(true);
        setJobStatus(null);
        try {
            const parsedMetadata = metadata.trim() ? JSON.parse(metadata) : [];
            const job = await api.startMobileAnalysisJob({
                platform,
                project_id: selectedProjectId ? Number(selectedProjectId) : undefined,
                screen_name: screenName,
                image_base64: imageBase64,
                element_metadata: parsedMetadata,
            });
            setJobStatus({ ...job, job_id: job.job_id, celery_task_id: undefined, error_message: undefined, result: undefined, created_at: new Date().toISOString() });
            activeJobRef.current = job.job_id;

            for (let attempt = 0; attempt < 60; attempt += 1) {
                const status = await api.getMobileJobStatus(job.job_id);
                if (activeJobRef.current !== job.job_id) return;
                setJobStatus(status);

                if (status.status === 'completed') {
                    setResult(status.result as MobileAnalysisResponse);
                    await loadHistory();
                    return;
                }

                if (status.status === 'failed') {
                    throw new Error(status.error_message || 'Mobile job basarisiz oldu.');
                }

                await new Promise((resolve) => window.setTimeout(resolve, 1200));
            }
            throw new Error('Mobile job zaman asimina ugradi.');
        } catch (error: any) {
            setResult(null);
            alert(readableErrorMessage(error, 'Mobil analizi tamamlanamadi.'));
        } finally {
            setLoading(false);
        }
    };

    const openHistoryItem = async (recordId: number) => {
        try {
            const detail = await api.getMobileHistoryDetail(recordId);
            setResult(detail.analysis);
            if (detail.project_id) {
                setSelectedProjectId(String(detail.project_id));
            }
            if (detail.analysis.image_base64) {
                setImageBase64(detail.analysis.image_base64);
                setPreview(`data:image/png;base64,${detail.analysis.image_base64}`);
            }
            if (detail.analysis.platform) {
                setPlatform(detail.analysis.platform);
            }
        } catch (error) {
            alert(readableErrorMessage(error, 'Mobile history kaydi acilamadi.'));
        }
    };

    return (
        <div className="mx-auto max-w-7xl space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6">
                <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-start gap-4">
                        <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-sky-400/25 bg-sky-500/10">
                            <Smartphone className="h-7 w-7 text-sky-300" />
                        </div>
                        <div>
                            <p className="text-[11px] uppercase tracking-[0.28em] text-sky-300">Mobile Intelligence</p>
                            <h1 className="mt-1 text-3xl font-bold text-white">Mobil Test Modulu</h1>
                            <p className="mt-2 max-w-2xl text-sm text-slate-400">
                                Screenshot ve element metadata bilgisini birlikte yorumlayarak mobil UX, touch target,
                                responsive risk ve platform uyumlulugu sinyalleri uretir.
                            </p>
                        </div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3 lg:min-w-[420px]">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                            <p className="text-[10px] uppercase tracking-[0.24em] text-slate-500">Project</p>
                            <p className="mt-2 truncate text-sm font-semibold text-white">{selectedProject?.name || 'Global'}</p>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                            <p className="text-[10px] uppercase tracking-[0.24em] text-slate-500">History</p>
                            <p className="mt-2 text-sm font-semibold text-white">{historyItems.length} kayıt</p>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                            <p className="text-[10px] uppercase tracking-[0.24em] text-slate-500">Last Score</p>
                            <p className="mt-2 text-sm font-semibold text-white">{result ? result.overall_score : '--'}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.12fr)_minmax(380px,0.88fr)] items-start">
                <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 shadow-2xl shadow-slate-950/40">
                    <div>
                        <p className="mb-2 text-[11px] uppercase tracking-[0.24em] text-cyan-300">Project Binding</p>
                        <select value={selectedProjectId} onChange={(e) => setSelectedProjectId(e.target.value)} className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none">
                            <option value="">Global mobile analysis</option>
                            {projects.map((project) => (
                                <option key={project.id} value={project.id}>{project.name}</option>
                            ))}
                        </select>
                        <p className="mt-2 text-xs text-slate-500">
                            Proje seçersen kayıt Full Report içindeki Mobile kartına bağlanır.
                        </p>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                        <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none">
                            <option value="android">Android</option>
                            <option value="ios">iOS</option>
                        </select>
                        <input value={screenName} onChange={(e) => setScreenName(e.target.value)} placeholder="Screen name" className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none" />
                    </div>

                    <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <p className="text-sm font-semibold text-white">Mobil Screenshot</p>
                                <p className="mt-1 text-xs text-slate-500">Ekran goruntusu varsa gorsel kanit olarak saklanir.</p>
                            </div>
                            <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:border-sky-400/50 hover:text-sky-300">
                                <Wand2 className="h-4 w-4" />
                                Screenshot Sec
                                <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
                            </label>
                        </div>
                        {preview && (
                            <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
                                <img src={preview} alt="Mobile preview" className="max-h-[320px] w-full object-contain" />
                            </div>
                        )}
                    </div>

                    <div className="mt-5">
                        <p className="mb-3 text-sm font-semibold text-white">Element Metadata</p>
                        <textarea
                            value={metadata}
                            onChange={(e) => setMetadata(e.target.value)}
                            rows={12}
                            className="w-full rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 font-mono text-sm text-cyan-300 outline-none"
                        />
                    </div>

                    <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
                        <button onClick={handleAnalyze} disabled={loading} className="inline-flex items-center justify-center gap-2 rounded-xl bg-sky-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:opacity-50">
                            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                            Mobil Analizini Baslat
                        </button>
                        {jobStatus && (
                            <div className="rounded-2xl border border-sky-400/25 bg-sky-400/10 px-4 py-3 text-sm text-sky-100">
                                Job #{jobStatus.job_id} · {jobStatus.status}
                            </div>
                        )}
                    </div>
                </div>

                <aside className="space-y-6">
                    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <p className="text-[11px] uppercase tracking-[0.24em] text-cyan-300">Live Result</p>
                                <p className="mt-1 text-lg font-semibold text-white">{result ? 'Son analiz sonucu' : 'Analiz bekleniyor'}</p>
                            </div>
                            {result && (
                                <span className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-3 py-1 text-sm font-semibold text-cyan-100">
                                    {result.overall_score}
                                </span>
                            )}
                        </div>

                        {!result ? (
                            <div className="mt-4 rounded-2xl border border-dashed border-slate-700 bg-slate-950 p-5 text-sm text-slate-400">
                                Mobil analiz calistirildiginda skorlar, AI yorumu ve risk ozeti burada gorunur.
                            </div>
                        ) : (
                            <div className="mt-4 space-y-4">
                        <div className="grid gap-4 sm:grid-cols-3">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Overall</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.overall_score}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Screen Type</p>
                                <p className="mt-3 text-3xl font-semibold text-white capitalize">{result.context_profile.screen_type}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Patterns</p>
                                <p className="mt-3 text-sm font-semibold text-cyan-300">{result.context_profile.detected_patterns.join(' • ')}</p>
                            </div>
                        </div>

                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Task Friction</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.task_completion_friction}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Parity</p>
                                <p className="mt-3 text-sm font-semibold text-cyan-300">{result.cross_platform_parity_summary}</p>
                            </div>
                        </div>

                        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
                            <p className="text-white font-semibold">AI Mobile Interpretation</p>
                            <p className="mt-3 text-sm text-slate-300">{result.ai_interpretation}</p>
                            <div className="mt-4 rounded-2xl border border-sky-500/20 bg-sky-500/10 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-sky-300">AI Mobile Critic</p>
                                <p className="mt-2 text-sm text-sky-100">{result.ai_mobile_critic}</p>
                            </div>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Root Cause Summary</p>
                                <p className="mt-2 text-sm text-slate-300">{result.root_cause_summary}</p>
                            </div>
                            <div className="mt-4 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">Cross-Platform Signal</p>
                                <p className="mt-2 text-sm text-cyan-100">{result.context_profile.cross_platform_consistency_signal}</p>
                            </div>
                        </div>
                            </div>
                        )}
                    </div>

                    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5">
                        <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2 text-white font-semibold">
                                <Clock className="h-4 w-4 text-cyan-400" />
                                Mobile History
                            </div>
                            <button onClick={() => loadHistory()} className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-slate-700 text-slate-300 hover:border-cyan-400/50 hover:text-cyan-200">
                                <RefreshCw className={`h-4 w-4 ${historyLoading ? 'animate-spin' : ''}`} />
                            </button>
                        </div>
                        <div className="mt-4 max-h-[520px] space-y-3 overflow-y-auto pr-2">
                            {historyItems.length === 0 ? (
                                <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950 p-4 text-sm text-slate-400">
                                    Kayıtlı mobil analiz yok. Proje seçip mobil analiz çalıştırınca burada görünür.
                                </div>
                            ) : historyItems.map((item) => (
                                <button
                                    key={item.id}
                                    onClick={() => openHistoryItem(item.id)}
                                    className="w-full rounded-2xl border border-slate-800 bg-slate-950 p-4 text-left transition hover:border-cyan-400/50"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <p className="font-semibold text-white">{item.source_label || 'Mobile analysis'}</p>
                                            <p className="mt-1 text-xs uppercase tracking-[0.18em] text-slate-500">{item.platform} / {item.screen_type || item.source_type}</p>
                                        </div>
                                        <span className="rounded-full border border-cyan-400/30 bg-cyan-500/10 px-2.5 py-1 text-xs font-semibold text-cyan-100">{item.overall_score}</span>
                                    </div>
                                    <p className="mt-3 line-clamp-2 text-sm text-slate-300">{item.overview}</p>
                                    <p className="mt-3 text-xs text-slate-500">{item.findings_count} finding · {new Date(item.created_at).toLocaleString('tr-TR')}</p>
                                </button>
                            ))}
                        </div>
                    </div>
                </aside>
            </div>

            {result && (
                <>
                    <div className="grid gap-6 xl:grid-cols-3">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Score Breakdown</p>
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
                            <p className="text-white font-semibold">Supported Now</p>
                            <div className="mt-4 space-y-3">
                                {result.supported_now.map((item) => (
                                    <div key={item.title} className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="text-sm font-semibold text-emerald-100">{item.title}</p>
                                            <span className="rounded-full border border-emerald-300/20 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em] text-emerald-200">{item.status}</span>
                                        </div>
                                        <p className="mt-2 text-sm text-emerald-50/90">{item.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Next Phase</p>
                            <div className="mt-4 space-y-3">
                                {result.next_phase.map((item) => (
                                    <div key={item.title} className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4">
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="text-sm font-semibold text-amber-100">{item.title}</p>
                                            <span className="rounded-full border border-amber-300/20 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em] text-amber-200">{item.status}</span>
                                        </div>
                                        <p className="mt-2 text-sm text-amber-50/90">{item.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="grid gap-6 xl:grid-cols-3">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Thumb Zone</p>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                {result.thumb_zone_summary}
                            </div>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Keyboard Overlap</p>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                {result.keyboard_overlap_signal}
                            </div>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Safe Area & Gesture</p>
                            <div className="mt-4 space-y-3">
                                <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                    {result.safe_area_signal}
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                    {result.gesture_friction_summary}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Mobile Findings</p>
                            <div className="mt-4 space-y-3">
                                {result.findings.length === 0 ? (
                                    <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                        Bu kosumda belirgin mobil UX bulgusu cikmadi.
                                    </div>
                                ) : result.findings.map((finding) => (
                                    <div key={finding.id} className={`rounded-2xl border p-4 ${severityClasses[finding.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="font-semibold">{finding.title}</p>
                                            <span className="rounded-full border border-current/30 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em]">{finding.severity}</span>
                                        </div>
                                        <p className="mt-3 text-sm">{finding.description}</p>
                                        <p className="mt-2 text-xs text-slate-300/90">Kanit: {finding.evidence}</p>
                                        <p className="mt-2 text-xs text-slate-300/90">Oneri: {finding.recommendation}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Context Playbook</p>
                                <div className="mt-4 space-y-3">
                                    {result.context_playbook.map((item) => (
                                        <div key={item} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Recommendations</p>
                                <div className="mt-4 space-y-3">
                                    {result.recommendations.map((item) => (
                                        <div key={item} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                            {item}
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

export default MobilePage;
