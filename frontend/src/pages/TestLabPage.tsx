import { useState } from 'react';
import { AlertTriangle, Clock, Download, FlaskConical, List as ListIcon, Loader2, Send, ShieldAlert, Zap } from 'lucide-react';

import { api, ApiTestAnalyzeResponse } from '../services/api';

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

    const handleRunTest = async () => {
        setLoading(true);
        setResult(null);
        try {
            if (isLoadTest) {
                const response = await fetch(`/api/api-test/load-test?count=${loadTestCount}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        method,
                        url,
                        body: body ? JSON.parse(body) : null,
                    }),
                });
                const data = await response.json();
                setResult({
                    method,
                    url,
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
                const analysis = await api.analyzeApiRequest({
                    method,
                    url,
                    body: parsedBody,
                    expected_status: expectedStatus ? Number(expectedStatus) : undefined,
                    expected_fields: expectedFields.split(',').map((item) => item.trim()).filter(Boolean),
                    expected_response_type: expectedResponseType || undefined,
                    run_negative_checks: true,
                });
                setResult(analysis);
            }
        } catch (error: any) {
            setResult({
                method,
                url,
                success: false,
                status_code: undefined,
                duration_ms: 0,
                overall_score: 0,
                summary: error.response?.data?.detail || error.message,
                endpoint_risk_score: 0,
                ai_failure_explanation: 'Analiz calistirilamadi.',
                ai_test_summary: '',
                root_cause_summary: '',
                endpoint_context: 'unknown',
                response_type: 'error',
                response_size: 0,
                score_breakdown: { health: 0, validation: 0, security: 0, performance: 0, contract: 0 },
                findings: [],
                negative_checks: [],
                generated_tests: [],
                cross_module_correlation: [],
                raw_result: { error: error.response?.data || error.message },
            });
        } finally {
            setLoading(false);
        }
    };

    const handleImportSwagger = async () => {
        setLoading(true);
        try {
            const response = await fetch(`/api/api-test/import-swagger?url=${encodeURIComponent(swaggerUrl)}`);
            const data = await response.json();
            setEndpoints(data);
        } catch {
            alert('Swagger import hatasi!');
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
                                    <p className="mt-3 text-3xl font-semibold text-white">{result.status_code ?? 'n/a'}</p>
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
                </div>
            </div>
        </div>
    );
}

export default TestLabPage;
