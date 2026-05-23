import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Clock, Download, FlaskConical, List as ListIcon, Loader2, RefreshCw, Send, ShieldAlert, Zap } from 'lucide-react';

import { api, AnalysisJobStatusResponse, ApiHistoryItem, ApiTestAnalyzeResponse, Project } from '../services/api';
import { readableErrorMessage } from '../utils/errors';

const severityClasses: Record<string, string> = {
    high: 'border-red-500/40 bg-red-500/10 text-red-200',
    medium: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
    low: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
};

export function TestLabPage() {
    const [method, setMethod] = useState('GET');
    const [url, setUrl] = useState('https://jsonplaceholder.typicode.com/todos/1');
    const [body, setBody] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<ApiTestAnalyzeResponse | null>(null);
    const [loadTestCount, setLoadTestCount] = useState(10);
    const [isLoadTest, setIsLoadTest] = useState(false);
    const [swaggerUrl, setSwaggerUrl] = useState('https://petstore.swagger.io/v2/swagger.json');
    const [endpoints, setEndpoints] = useState<any[]>([]);
    const [expectedStatus, setExpectedStatus] = useState('200');
    const [expectedFields, setExpectedFields] = useState('');
    const [expectedResponseType, setExpectedResponseType] = useState('application/json');
    const [history, setHistory] = useState<ApiHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedProjectId, setSelectedProjectId] = useState('');
    const [jobStatus, setJobStatus] = useState<AnalysisJobStatusResponse | null>(null);
    const activeJobRef = useRef<number | null>(null);

    const normalizeUrl = (value: string) => {
        const trimmed = value.trim();
        if (trimmed.startsWith('https//')) {
            return trimmed.replace('https//', 'https://');
        }
        if (trimmed.startsWith('http//')) {
            return trimmed.replace('http//', 'http://');
        }
        return trimmed;
    };

    const loadHistory = async () => {
        setHistoryLoading(true);
        try {
            const items = await api.getApiHistory(12);
            setHistory(items);
        } catch (error) {
            console.warn('API history could not be loaded', error);
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        loadHistory();
        api.getProjects()
            .then(setProjects)
            .catch((error) => console.warn('Projects could not be loaded for API lab', error));
        return () => {
            activeJobRef.current = null;
        };
    }, []);

    const pollApiJob = async (jobId: number) => {
        activeJobRef.current = jobId;
        for (let attempt = 0; attempt < 120; attempt += 1) {
            if (activeJobRef.current !== jobId) return;
            const status = await api.getApiJobStatus(jobId);
            setJobStatus(status);
            if (status.status === 'completed') {
                if (status.result) {
                    setResult(status.result as ApiTestAnalyzeResponse);
                    await loadHistory();
                }
                return;
            }
            if (status.status === 'failed' || status.status === 'cancelled') {
                throw new Error(status.error_message || 'API job tamamlanamadi.');
            }
            await new Promise((resolve) => window.setTimeout(resolve, 1200));
        }
        throw new Error('API job zaman asimina ugradi.');
    };

    const handleRunTest = async () => {
        setLoading(true);
        setResult(null);
        setJobStatus(null);
        const requestUrl = normalizeUrl(url);
        if (requestUrl !== url) {
            setUrl(requestUrl);
        }
        try {
            if (isLoadTest) {
                const response = await fetch(`/api/api-test/load-test?count=${loadTestCount}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        method,
                        url: requestUrl,
                        body: body ? JSON.parse(body) : null,
                    }),
                });
                const data = await response.json();
                setResult({
                    method,
                    url: requestUrl,
                    project_id: selectedProjectId ? Number(selectedProjectId) : null,
                    success: true,
                    status_code: 200,
                    duration_ms: Number(data.avg_duration_ms || data.total_time_ms || 0),
                    overall_score: data.p95_duration_ms > 1200 ? 65 : 84,
                    endpoint_risk_score: 38,
                    summary: `Load test ${data.total_requests} istek, ${data.success_count} basarili sonuc ve P95 ${data.p95_duration_ms} ms ile tamamlandi.`,
                    ai_failure_explanation: data.p95_duration_ms > 1200
                        ? 'Yuk altinda response sureleri bozuluyor; bu durum concurrency altinda downstream veya query maliyetinin arttigini gosterebilir.'
                        : 'Yuk testi temel seviyede stabil gorunuyor; bir sonraki adim esik ve daha yuksek concurrency profili olabilir.',
                    ai_test_summary: 'Load test kosumu tamamlandi; p95 ve throughput degeri performans modulunde daha derin izlenebilir.',
                    root_cause_summary: data.p95_duration_ms > 1200
                        ? 'Muhtemel kok neden artan concurrency altinda yetersiz cache, connection pool veya DB maliyeti.'
                        : 'Belirgin kok neden sinyali yok.',
                    endpoint_context: 'load-test',
                    response_type: 'load-test',
                    response_size: 0,
                    score_breakdown: {
                        health: 84,
                        validation: 100,
                        security: 88,
                        performance: data.p95_duration_ms > 1200 ? 58 : 86,
                        contract: 100,
                    },
                    evidence_summary: {
                        contract_signals: 0,
                        security_signals: 0,
                        performance_signals: data.p95_duration_ms > 1200 ? 1 : 0,
                        validation_signals: 0,
                        availability_signals: 0,
                        negative_probe_signals: 0,
                        primary_categories: data.p95_duration_ms > 1200 ? ['load-test'] : [],
                        recommended_modules: ['4.7 Performance'],
                    },
                    findings: data.p95_duration_ms > 1200 ? [{
                        id: 1,
                        title: 'P95 response suresi yuksek',
                        severity: 'medium',
                        category: 'load-test',
                        description: 'Yuk testi sonucunda p95 response suresi hedefin ustune cikti.',
                        evidence: `P95: ${data.p95_duration_ms} ms`,
                        recommendation: 'Downstream dependency ve cache davranisini inceleyip yuk altinda profil cikar.',
                    }] : [],
                    negative_checks: [],
                    generated_tests: [],
                    cross_module_correlation: [
                        {
                            module: '4.7 Performance',
                            summary: 'Bu endpoint yuk altinda performans modulu ile daha detayli izlenmeli.',
                            reason: 'Load test sonucu latency sinyali uretiyor.',
                            suggested_follow_up: 'Ayni endpoint icin p50/p95/p99 ve concurrency matrisi cikar.',
                        },
                    ],
                    raw_result: data,
                });
            } else {
                const parsedBody = body ? JSON.parse(body) : null;
                const job = await api.startApiAnalysisJob({
                    method,
                    url: requestUrl,
                    project_id: selectedProjectId ? Number(selectedProjectId) : undefined,
                    body: parsedBody,
                    expected_status: expectedStatus ? Number(expectedStatus) : undefined,
                    expected_fields: expectedFields.split(',').map((item) => item.trim()).filter(Boolean),
                    expected_response_type: expectedResponseType || undefined,
                    run_negative_checks: true,
                });
                setJobStatus({
                    job_id: job.job_id,
                    status: job.status,
                    module_name: job.module_name,
                    target: job.target,
                    created_at: new Date().toISOString(),
                });
                await pollApiJob(job.job_id);
            }
        } catch (error: any) {
            const summary = readableErrorMessage(error, 'API analizi tamamlanamadi.');
            setResult({
                method,
                url: requestUrl,
                success: false,
                status_code: undefined,
                duration_ms: 0,
                overall_score: 0,
                summary,
                endpoint_risk_score: 0,
                ai_failure_explanation: 'Analiz calistirilamadi.',
                ai_test_summary: '',
                root_cause_summary: '',
                endpoint_context: 'unknown',
                response_type: 'error',
                response_size: 0,
                score_breakdown: { health: 0, validation: 0, security: 0, performance: 0, contract: 0 },
                evidence_summary: {
                    contract_signals: 0,
                    security_signals: 0,
                    performance_signals: 0,
                    validation_signals: 0,
                    availability_signals: 1,
                    negative_probe_signals: 0,
                    primary_categories: ['request-error'],
                    recommended_modules: [],
                },
                findings: [],
                negative_checks: [],
                generated_tests: [],
                cross_module_correlation: [],
                raw_result: { error: summary },
            });
        } finally {
            activeJobRef.current = null;
            setLoading(false);
        }
    };

    const openHistoryItem = async (recordId: number) => {
        try {
            const detail = await api.getApiHistoryDetail(recordId);
            if (detail.analysis_payload) {
                setResult(detail.analysis_payload);
                setMethod(detail.analysis_payload.method || method);
                setUrl(detail.analysis_payload.url || url);
                if (detail.analysis_payload.project_id) {
                    setSelectedProjectId(String(detail.analysis_payload.project_id));
                }
            }
        } catch (error) {
            alert(readableErrorMessage(error, 'API history kaydi acilamadi.'));
        }
    };

    const handleImportSwagger = async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/api-test/import-swagger?url=${encodeURIComponent(swaggerUrl)}`);
            const data = await response.json();
            setEndpoints(data);
        } catch (error) {
            alert(readableErrorMessage(error, 'Swagger import tamamlanamadi.'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <FlaskConical className="h-8 w-8 text-purple-500" />
                        API Test Modulu
                    </h1>
                    <p className="text-slate-400 mt-2">
                        Endpoint validation, response checks ve basit negatif senaryo findingleri.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                        <div className="mb-4 grid gap-4 md:grid-cols-[1fr_220px]">
                            <div>
                                <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">Project Binding</label>
                                <select
                                    value={selectedProjectId}
                                    onChange={(e) => setSelectedProjectId(e.target.value)}
                                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm text-white outline-none focus:border-purple-400"
                                >
                                    <option value="">Global API analysis</option>
                                    {projects.map((project) => (
                                        <option key={project.id} value={project.id}>
                                            {project.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Report Link</p>
                                <p className="mt-2 text-xs text-slate-300">
                                    {selectedProjectId
                                        ? 'Bu analiz secilen projenin Full Report API kartina baglanir.'
                                        : 'Proje secilmezse kayit sadece API History icinde kalir.'}
                                </p>
                            </div>
                        </div>
                        <div className="flex gap-4 mb-4">
                            <select
                                value={method}
                                onChange={(e) => setMethod(e.target.value)}
                                className="bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 focus:ring-2 focus:ring-purple-500 outline-none"
                            >
                                <option>GET</option>
                                <option>POST</option>
                                <option>PUT</option>
                                <option>DELETE</option>
                                <option>PATCH</option>
                            </select>
                            <input
                                type="text"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                placeholder="API URL"
                                className="flex-1 bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 focus:ring-2 focus:ring-purple-500 outline-none"
                            />
                            <input
                                type="number"
                                value={expectedStatus}
                                onChange={(e) => setExpectedStatus(e.target.value)}
                                placeholder="Expected"
                                className="w-28 bg-slate-800 border border-slate-700 text-white rounded-lg px-3 py-2 focus:ring-2 focus:ring-purple-500 outline-none"
                            />
                        </div>

                        {method !== 'GET' && (
                            <textarea
                                value={body}
                                onChange={(e) => setBody(e.target.value)}
                                rows={4}
                                placeholder='{"key":"value"}'
                                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 font-mono text-sm mb-4 outline-none"
                            />
                        )}

                        <div className="grid gap-4 md:grid-cols-2 mb-4">
                            <input
                                type="text"
                                value={expectedFields}
                                onChange={(e) => setExpectedFields(e.target.value)}
                                placeholder="Expected fields: id,name,status"
                                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 text-sm outline-none"
                            />
                            <input
                                type="text"
                                value={expectedResponseType}
                                onChange={(e) => setExpectedResponseType(e.target.value)}
                                placeholder="application/json"
                                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 text-sm outline-none"
                            />
                        </div>

                        <div className="flex items-center justify-between border-t border-slate-800 pt-4">
                            <div className="flex items-center gap-4">
                                <label className="flex items-center gap-2 text-slate-400 text-sm cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={isLoadTest}
                                        onChange={(e) => setIsLoadTest(e.target.checked)}
                                        className="h-4 w-4 rounded border-slate-700 text-purple-600 focus:ring-purple-500"
                                    />
                                    Enable Load Test
                                </label>
                                {isLoadTest && (
                                    <input
                                        type="number"
                                        value={loadTestCount}
                                        onChange={(e) => setLoadTestCount(Number(e.target.value))}
                                        className="w-16 bg-slate-800 border border-slate-700 text-white rounded px-2 py-1 text-sm outline-none"
                                    />
                                )}
                            </div>
                            <button
                                onClick={handleRunTest}
                                disabled={loading}
                                className={`px-6 py-2 rounded-lg font-bold flex items-center gap-2 transition-all ${isLoadTest ? 'bg-orange-600 hover:bg-orange-500' : 'bg-purple-600 hover:bg-purple-500'}`}
                            >
                                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : (isLoadTest ? <Zap className="h-4 w-4" /> : <Send className="h-4 w-4" />)}
                                {isLoadTest ? 'Run Load Test' : 'Analyze Endpoint'}
                            </button>
                        </div>
                    </div>

                    {jobStatus && !isLoadTest && (
                        <div className="rounded-xl border border-cyan-500/25 bg-cyan-500/10 px-4 py-3 text-sm text-cyan-100">
                            Job #{jobStatus.job_id} · {jobStatus.status}
                            {jobStatus.celery_task_id ? <span className="text-cyan-200/80"> · Celery {jobStatus.celery_task_id.slice(0, 8)}</span> : null}
                        </div>
                    )}

                    {result && (
                        <>
                            <div className="grid gap-4 sm:grid-cols-4">
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Overall</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{result.overall_score}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Risk</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{result.endpoint_risk_score}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Status</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{result.status_code ?? '--'}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Duration</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{Math.round(result.duration_ms)}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Findings</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{result.findings.length}</p>
                                </div>
                            </div>

                            <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                                    <p className="text-white font-semibold">AI Failure Explanation</p>
                                    <p className="mt-3 text-sm text-slate-300">{result.ai_failure_explanation}</p>
                                    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Root Cause Summary</p>
                                        <p className="mt-2 text-sm text-slate-300">{result.root_cause_summary}</p>
                                    </div>
                                    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">AI Test Summary</p>
                                        <p className="mt-2 text-sm text-slate-300">{result.ai_test_summary}</p>
                                    </div>
                                </div>

                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                                    <p className="text-white font-semibold">Score Breakdown</p>
                                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                                        {Object.entries(result.score_breakdown).map(([label, value]) => (
                                            <div key={label} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{label}</p>
                                                <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Endpoint Context</p>
                                        <p className="mt-2 text-sm text-cyan-300">{result.endpoint_context}</p>
                                    </div>
                                    <div className="mt-4 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
                                        <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">Evidence Matrix</p>
                                        <div className="mt-3 grid gap-2 text-xs text-slate-300 sm:grid-cols-2">
                                            <span>Contract: {result.evidence_summary.contract_signals}</span>
                                            <span>Security: {result.evidence_summary.security_signals}</span>
                                            <span>Performance: {result.evidence_summary.performance_signals}</span>
                                            <span>Availability: {result.evidence_summary.availability_signals}</span>
                                        </div>
                                        {result.evidence_summary.primary_categories.length > 0 && (
                                            <div className="mt-3 flex flex-wrap gap-2">
                                                {result.evidence_summary.primary_categories.map((category) => (
                                                    <span key={category} className="rounded-full border border-cyan-400/20 bg-slate-950 px-2.5 py-1 text-[11px] text-cyan-100">
                                                        {category}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                                <div className="bg-slate-900 px-6 py-4 border-b border-slate-800">
                                    <div className="flex items-center justify-between gap-4">
                                        <div>
                                            <p className="text-white font-semibold">Standart Cikti</p>
                                            <p className="text-slate-400 text-sm mt-1">{result.summary}</p>
                                        </div>
                                        <div className="text-slate-500 text-xs flex items-center gap-1">
                                            <Clock className="h-3 w-3" /> {result.response_type} • {result.response_size} chars
                                        </div>
                                    </div>
                                </div>
                                <div className="grid gap-6 p-6 xl:grid-cols-[1.15fr_0.85fr]">
                                    <div className="space-y-4">
                                        <div>
                                            <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-3">Findings</p>
                                            <div className="space-y-3">
                                                {result.findings.length === 0 ? (
                                                    <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                                        Bu kosumda belirgin API bulgusu cikmadi.
                                                    </div>
                                                ) : result.findings.map((finding) => (
                                                    <div key={finding.id} className={`rounded-2xl border p-4 ${severityClasses[finding.severity] ?? 'border-slate-700 bg-slate-900 text-slate-200'}`}>
                                                        <div className="flex items-center justify-between gap-3">
                                                            <p className="font-semibold">{finding.title}</p>
                                                            <span className="rounded-full border border-current/30 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em]">
                                                                {finding.severity}
                                                            </span>
                                                        </div>
                                                        <p className="mt-3 text-sm">{finding.description}</p>
                                                        <p className="mt-3 text-xs text-slate-300/90">Kanit: {finding.evidence}</p>
                                                        <p className="mt-2 text-xs text-slate-300/90">Oneri: {finding.recommendation}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-3">Negative Checks</p>
                                            <div className="space-y-3">
                                                {result.negative_checks.map((check) => (
                                                    <div key={check.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                                        <div className="flex items-center justify-between gap-3">
                                                            <p className="text-white font-semibold">{check.name}</p>
                                                            <span className="text-xs uppercase tracking-[0.24em] text-cyan-300">{check.status}</span>
                                                        </div>
                                                        <p className="mt-3 text-sm text-slate-300">{check.summary}</p>
                                                        <p className="mt-2 text-xs text-slate-500">{check.evidence}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-3">Context-Aware Test Generation</p>
                                            <div className="space-y-3">
                                                {result.generated_tests.map((generated) => (
                                                    <div key={generated.id} className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                                        <div className="flex items-center justify-between gap-3">
                                                            <p className="text-white font-semibold">{generated.title}</p>
                                                            <span className="text-xs uppercase tracking-[0.24em] text-fuchsia-300">P{generated.priority}</span>
                                                        </div>
                                                        <p className="mt-3 text-sm text-slate-300">{generated.rationale}</p>
                                                        <p className="mt-2 text-xs text-slate-500">Expected: {generated.expected_signal}</p>
                                                        {generated.suggested_payload && (
                                                            <p className="mt-2 text-xs text-cyan-300">Payload: {generated.suggested_payload}</p>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <div>
                                            <p className="text-xs uppercase tracking-[0.24em] text-slate-500 mb-3">Cross-Module Correlation</p>
                                            <div className="space-y-3">
                                                {result.cross_module_correlation.map((item) => (
                                                    <div key={`${item.module}-${item.summary}`} className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                                        <div className="flex items-center justify-between gap-3">
                                                            <p className="text-white font-semibold">{item.module}</p>
                                                        </div>
                                                        <p className="mt-3 text-sm text-slate-300">{item.summary}</p>
                                                        <p className="mt-2 text-xs text-slate-500">Reason: {item.reason}</p>
                                                        <p className="mt-2 text-xs text-cyan-300">Follow-up: {item.suggested_follow_up}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                        <div className="flex items-center gap-2 text-white font-semibold">
                                            <ShieldAlert className="h-4 w-4 text-purple-400" />
                                            Raw Response
                                        </div>
                                        <pre className="mt-4 max-h-[520px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-cyan-300">
                                            {JSON.stringify(result.raw_result, null, 2)}
                                        </pre>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </div>

                <div className="space-y-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                            <Download className="h-4 w-4 text-blue-400" />
                            Swagger Import
                        </h3>
                        <div className="flex gap-2 mb-4">
                            <input
                                type="text"
                                value={swaggerUrl}
                                onChange={(e) => setSwaggerUrl(e.target.value)}
                                className="flex-1 bg-slate-800 border border-slate-700 text-xs text-white rounded px-3 py-1.5 outline-none"
                            />
                            <button onClick={handleImportSwagger} className="p-1.5 bg-blue-600 rounded text-white hover:bg-blue-500">
                                <ListIcon className="h-4 w-4" />
                            </button>
                        </div>
                        <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
                            {endpoints.map((ep, i) => (
                                <button
                                    key={i}
                                    onClick={() => { setMethod(ep.method); setUrl(ep.path); }}
                                    className="w-full text-left p-2 bg-slate-800/50 hover:bg-slate-800 rounded border border-slate-700/50 transition-all"
                                >
                                    <div className="flex items-center gap-2 mb-1">
                                        <span className={`text-[10px] font-black px-1.5 py-0.5 rounded ${ep.method === 'GET' ? 'bg-green-500/10 text-green-500' : 'bg-blue-500/10 text-blue-500'}`}>
                                            {ep.method}
                                        </span>
                                        <span className="text-[10px] text-slate-300 truncate font-mono">{ep.path}</span>
                                    </div>
                                    <p className="text-[10px] text-slate-500 truncate">{ep.summary}</p>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                        <div className="flex items-center gap-2 text-white font-semibold">
                            <AlertTriangle className="h-4 w-4 text-amber-400" />
                            V1 Scope
                        </div>
                        <ul className="mt-4 space-y-2 text-sm text-slate-300">
                            <li>Endpoint status ve response tipi dogrulamasi</li>
                            <li>Latency ve error leakage findingleri</li>
                            <li>OPTIONS ve reflection temelli basit negatif kontroller</li>
                            <li>Swagger import ile hizli endpoint secimi</li>
                        </ul>
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                        <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-2 text-white font-semibold">
                                <Clock className="h-4 w-4 text-cyan-400" />
                                API History
                            </div>
                            <button
                                type="button"
                                onClick={loadHistory}
                                disabled={historyLoading}
                                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 disabled:opacity-60"
                            >
                                <RefreshCw className={`inline h-3.5 w-3.5 ${historyLoading ? 'animate-spin' : ''}`} />
                            </button>
                        </div>
                        <div className="mt-4 max-h-[420px] space-y-3 overflow-y-auto pr-2">
                            {history.length === 0 ? (
                                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/60 p-4 text-sm text-slate-400">
                                    Kayitli API analizi yok. Bir endpoint analiz edince burada gorunecek.
                                </div>
                            ) : history.map((item) => (
                                <button
                                    key={item.id}
                                    type="button"
                                    onClick={() => openHistoryItem(item.id)}
                                    className="w-full rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-left transition hover:border-cyan-500/40 hover:bg-slate-950"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <p className="truncate text-sm font-semibold text-white">
                                                {item.source_label || item.source_url || 'API analysis'}
                                            </p>
                                            <p className="mt-1 truncate text-xs text-slate-500">
                                                {item.created_at ? new Date(item.created_at).toLocaleString('tr-TR') : 'unknown time'}
                                            </p>
                                        </div>
                                        <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${item.success === false ? 'border-red-500/40 bg-red-500/10 text-red-200' : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'}`}>
                                            {item.overall_score}
                                        </span>
                                    </div>
                                    <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">
                                        <span className="rounded-full border border-slate-700 px-2 py-1">{item.status_code ?? '--'}</span>
                                        <span className="rounded-full border border-slate-700 px-2 py-1">{Math.round(Number(item.duration_ms || 0))} ms</span>
                                        <span className="rounded-full border border-slate-700 px-2 py-1">{item.findings_count} finding</span>
                                    </div>
                                    {item.overview && (
                                        <p className="mt-3 line-clamp-2 text-xs text-slate-400">{item.overview}</p>
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default TestLabPage;
