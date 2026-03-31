import { useState } from 'react';
import { Activity, AlertTriangle, Gauge, Loader2, Timer } from 'lucide-react';

import { api, PerformanceAnalysisResponse } from '../services/api';

const severityClasses: Record<string, string> = {
    high: 'border-red-500/40 bg-red-500/10 text-red-200',
    medium: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
    low: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
};

export function PerformancePage() {
    const [url, setUrl] = useState('https://example.com');
    const [apiUrl, setApiUrl] = useState('https://jsonplaceholder.typicode.com/todos/1');
    const [apiMethod, setApiMethod] = useState('GET');
    const [dbConnection, setDbConnection] = useState('postgresql://visionqa:visionqa_dev_password@localhost:5432/visionqa_db');
    const [dbQuery, setDbQuery] = useState('SELECT * FROM projects LIMIT 5');
    const [sampleRuns, setSampleRuns] = useState(5);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<PerformanceAnalysisResponse | null>(null);

    const handleAnalyze = async () => {
        setLoading(true);
        try {
            const response = await api.analyzePerformance({
                url: url || undefined,
                api_url: apiUrl || undefined,
                api_method: apiMethod,
                db_connection_string: dbConnection || undefined,
                db_query: dbQuery || undefined,
                sample_api_runs: sampleRuns,
            });
            setResult(response);
        } catch (error: any) {
            setResult(null);
            alert(error.response?.data?.detail || error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                    <Activity className="h-8 w-8 text-emerald-400" />
                    Performans Analiz Modulu
                </h1>
                <p className="mt-2 text-slate-400">
                    Web, API ve DB metriklerini yorumlayan performans auditoru.
                </p>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr] items-start">
                <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6 space-y-5">
                    <div className="grid gap-4 md:grid-cols-2">
                        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Web URL" className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none" />
                        <div className="grid grid-cols-[110px_1fr] gap-3">
                            <select value={apiMethod} onChange={(e) => setApiMethod(e.target.value)} className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-3 text-sm text-white outline-none">
                                <option>GET</option>
                                <option>POST</option>
                                <option>PUT</option>
                                <option>DELETE</option>
                            </select>
                            <input value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} placeholder="API URL" className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none" />
                        </div>
                    </div>
                    <div className="grid gap-4 md:grid-cols-[1fr_160px]">
                        <input value={dbConnection} onChange={(e) => setDbConnection(e.target.value)} placeholder="DB connection string" className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none" />
                        <input type="number" value={sampleRuns} onChange={(e) => setSampleRuns(Number(e.target.value))} className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none" />
                    </div>
                    <textarea value={dbQuery} onChange={(e) => setDbQuery(e.target.value)} rows={5} className="w-full rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 font-mono text-sm text-cyan-300 outline-none" />
                    <button onClick={handleAnalyze} disabled={loading} className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50">
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Gauge className="h-4 w-4" />}
                        Performans Analizini Baslat
                    </button>
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
                                <p className="mt-3 text-3xl font-semibold text-white">{result.performance_grade}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Confidence</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.bottleneck_confidence}</p>
                            </div>
                        </div>

                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Technical</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.technical_score}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Perceived</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.perceived_score}</p>
                            </div>
                        </div>

                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">AI Interpretation</p>
                            <p className="mt-3 text-sm text-slate-300">{result.root_cause_summary}</p>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Overview</p>
                                <p className="mt-2 text-sm text-slate-300">{result.overview}</p>
                            </div>
                            <div className="mt-4 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">Interpretation Note</p>
                                <p className="mt-2 text-sm text-cyan-100">
                                    Bu alandaki root cause, grade, confidence ve oneriler olculen metriklerin ustune kuralli yorum katmani eklenerek uretilir.
                                </p>
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
                                <Timer className="h-4 w-4 text-emerald-400" />
                                Measured Metrics · Web
                            </div>
                            <pre className="mt-4 rounded-2xl bg-slate-950 p-4 text-xs text-cyan-300 overflow-auto">
                                {JSON.stringify(result.web_metrics, null, 2)}
                            </pre>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <div className="flex items-center gap-2 text-white font-semibold">
                                <Timer className="h-4 w-4 text-fuchsia-400" />
                                Measured Metrics · API
                            </div>
                            <pre className="mt-4 rounded-2xl bg-slate-950 p-4 text-xs text-cyan-300 overflow-auto">
                                {JSON.stringify(result.api_metrics, null, 2)}
                            </pre>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <div className="flex items-center gap-2 text-white font-semibold">
                                <Timer className="h-4 w-4 text-amber-400" />
                                Measured Metrics · DB
                            </div>
                            <pre className="mt-4 rounded-2xl bg-slate-950 p-4 text-xs text-cyan-300 overflow-auto">
                                {JSON.stringify(result.db_metrics, null, 2)}
                            </pre>
                        </div>
                    </div>

                    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Performance Findings</p>
                            <div className="mt-4 space-y-3">
                                {result.findings.length === 0 ? (
                                    <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                        Bu kosumda belirgin performans bulgusu cikmadi.
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
                                <div className="flex items-center gap-2 text-white font-semibold">
                                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                                    Optimization Suggestions
                                </div>
                                <div className="mt-4 space-y-3">
                                    {result.optimization_suggestions.map((item) => (
                                        <div key={item} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Cross-Module Correlation</p>
                                <div className="mt-4 space-y-3">
                                    {result.correlations.length === 0 ? (
                                        <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
                                            Belirgin korelasyon sinyali cikmadi.
                                        </div>
                                    ) : result.correlations.map((item) => (
                                        <div key={`${item.source}-${item.summary}`} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                            <p className="text-sm font-semibold text-white">{item.source}</p>
                                            <p className="mt-2 text-sm text-slate-300">{item.summary}</p>
                                            <p className="mt-2 text-xs text-slate-500">{item.reason}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Timeline Summary</p>
                                <div className="mt-4 space-y-3">
                                    {result.timeline_summary.map((item) => (
                                        <div key={item} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Measured vs Interpreted</p>
                                <div className="mt-4 grid gap-3">
                                    <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                                        Measured: Web/API/DB metric kartlarindaki sureler, percentile'lar, timeout ve query duration degerleri gercek kosum sirasinda toplanir.
                                    </div>
                                    <div className="rounded-2xl border border-fuchsia-500/20 bg-fuchsia-500/10 p-4 text-sm text-fuchsia-100">
                                        Interpreted: Grade, confidence, root cause, correlation ve optimization onerileri bu metriklerin ustune kuralli analiz katmani eklenerek uretilir.
                                    </div>
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Score Breakdown</p>
                                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                                    {Object.entries(result.score_breakdown).map(([key, value]) => (
                                        <div key={key} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                            <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{key}</p>
                                            <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Module Recommendations</p>
                                <div className="mt-4 space-y-4">
                                    {Object.entries(result.module_recommendations).map(([module, items]) => (
                                        <div key={module} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                            <p className="text-sm font-semibold text-white uppercase tracking-[0.2em]">{module}</p>
                                            <div className="mt-3 space-y-2">
                                                {items.map((item) => (
                                                    <p key={item} className="text-sm text-slate-300">{item}</p>
                                                ))}
                                            </div>
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

export default PerformancePage;
