import { useState } from 'react';
import { AlertCircle, Clock, Database, List as ListIcon, Loader2, Play, ShieldCheck, Terminal } from 'lucide-react';

import { api, DbQualityResponse } from '../services/api';

const severityClasses: Record<string, string> = {
    high: 'border-red-500/40 bg-red-500/10 text-red-200',
    medium: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
    low: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
};

export function DatabasePage() {
    const [connString, setConnString] = useState('postgresql://visionqa:visionqa_dev_password@localhost:5432/visionqa_db');
    const [query, setQuery] = useState('SELECT * FROM projects LIMIT 5');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [qualityResult, setQualityResult] = useState<DbQualityResponse | null>(null);
    const [tables, setTables] = useState<string[]>([]);
    const [selectedTable, setSelectedTable] = useState('');
    const [expectedColumns, setExpectedColumns] = useState('');
    const [apiExpectedFields, setApiExpectedFields] = useState('');

    const fetchTables = async () => {
        try {
            const response = await fetch(`/api/db-test/tables?connection_string=${encodeURIComponent(connString)}`);
            const data = await response.json();
            setTables(data);
        } catch {
            console.error('Tablo listesi alinamadi');
        }
    };

    const handleRunQuery = async () => {
        setLoading(true);
        setResult(null);
        try {
            const response = await fetch('/api/db-test/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    connection_string: connString,
                    query,
                }),
            });
            const data = await response.json();
            setResult(data);
            if (data.success) {
                fetchTables();
            }
        } catch (error: any) {
            setResult({
                success: false,
                error: error.message,
            });
        } finally {
            setLoading(false);
        }
    };

    const handleQualityAudit = async () => {
        setLoading(true);
        try {
            const audit = await api.analyzeDbQuality({
                connection_string: connString,
                query,
                table_name: selectedTable || undefined,
                expected_columns: expectedColumns
                    .split(',')
                    .map((column) => column.trim())
                    .filter(Boolean),
                api_expected_fields: apiExpectedFields
                    .split(',')
                    .map((column) => column.trim())
                    .filter(Boolean),
            });
            setQualityResult(audit);
        } catch (error: any) {
            setQualityResult({
                success: false,
                overall_score: 0,
                table_quality_score: 0,
                summary: error.response?.data?.detail || error.message,
                ai_interpretation: 'Kalite analizi calistirilamadi.',
                root_cause_summary: '',
                duration_ms: 0,
                score_breakdown: { integrity: 0, completeness: 0, consistency: 0, performance: 0, security: 0 },
                findings: [],
                schema_smells: [],
                constraint_summary: null,
                detected_columns: [],
                sample_rows: [],
            });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Database className="h-8 w-8 text-blue-500" />
                        Veritabani Kalite Modulu
                    </h1>
                    <p className="text-slate-400 mt-2">
                        SQL sorgu analizi, sema kontrolu ve veri tutarlilik sinyalleri.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
                <div className="lg:col-span-3 space-y-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                        <div className="mb-4">
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 block">Connection String</label>
                            <input
                                type="text"
                                value={connString}
                                onChange={(e) => setConnString(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 text-sm font-mono outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>

                        <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
                            <div className="relative">
                                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 block">SQL Editor</label>
                                <textarea
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    rows={8}
                                    className="w-full bg-slate-950 border border-slate-800 text-cyan-400 rounded-xl px-4 py-3 font-mono text-sm outline-none focus:border-blue-500 transition-all shadow-inner"
                                />
                                <button
                                    onClick={handleRunQuery}
                                    disabled={loading}
                                    className="absolute bottom-4 right-4 bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-bold flex items-center gap-2 shadow-lg transition-all active:scale-95 disabled:opacity-50"
                                >
                                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
                                    Execute Query
                                </button>
                            </div>

                            <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 space-y-4">
                                <div>
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 block">Selected Table</label>
                                    <div className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white">
                                        {selectedTable || 'No table selected'}
                                    </div>
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 block">Expected Columns</label>
                                    <input
                                        type="text"
                                        value={expectedColumns}
                                        onChange={(e) => setExpectedColumns(e.target.value)}
                                        placeholder="id,name,created_at"
                                        className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 block">API Expected Fields</label>
                                    <input
                                        type="text"
                                        value={apiExpectedFields}
                                        onChange={(e) => setApiExpectedFields(e.target.value)}
                                        placeholder="email,status,role"
                                        className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white outline-none"
                                    />
                                </div>
                                <button
                                    onClick={handleQualityAudit}
                                    disabled={loading}
                                    className="w-full rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50"
                                >
                                    Run Quality Audit
                                </button>
                            </div>
                        </div>
                    </div>

                    {qualityResult && (
                        <>
                            <div className="grid gap-4 sm:grid-cols-4">
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Overall</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{qualityResult.overall_score}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Table Quality</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{qualityResult.table_quality_score}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Duration</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{Math.round(qualityResult.duration_ms)}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Findings</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{qualityResult.findings.length}</p>
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Columns</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{qualityResult.detected_columns.length}</p>
                                </div>
                            </div>

                            <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                                    <p className="text-white font-semibold">AI Interpretation</p>
                                    <p className="mt-3 text-sm text-slate-300">{qualityResult.ai_interpretation}</p>
                                    <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Root Cause Summary</p>
                                        <p className="mt-2 text-sm text-slate-300">{qualityResult.root_cause_summary}</p>
                                    </div>
                                </div>

                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                                    <p className="text-white font-semibold">Score Breakdown</p>
                                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                                        {Object.entries(qualityResult.score_breakdown).map(([label, value]) => (
                                            <div key={label} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{label}</p>
                                                <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
                                <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                                    <p className="text-white font-semibold">Quality Findings</p>
                                    <p className="mt-1 text-sm text-slate-400">{qualityResult.summary}</p>
                                    <div className="mt-4 space-y-3">
                                        {qualityResult.findings.length === 0 ? (
                                            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                                Bu kosumda belirgin DB kalite bulgusu cikmadi.
                                            </div>
                                        ) : qualityResult.findings.map((finding) => (
                                            <div key={finding.id} className={`rounded-2xl border p-4 ${severityClasses[finding.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
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

                                <div className="space-y-6">
                                    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                                        <p className="text-white font-semibold">Schema Snapshot</p>
                                    <div className="mt-4 flex flex-wrap gap-2">
                                        {qualityResult.detected_columns.map((column) => (
                                            <span key={column} className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-200">
                                                {column}
                                            </span>
                                        ))}
                                    </div>
                                        {qualityResult.constraint_summary && (
                                            <div className="mt-4 space-y-3 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                                <p><span className="text-slate-500">Primary Keys:</span> {qualityResult.constraint_summary.primary_keys.join(', ') || 'None'}</p>
                                                <p><span className="text-slate-500">Foreign Keys:</span> {qualityResult.constraint_summary.foreign_keys.join(', ') || 'None'}</p>
                                                <p><span className="text-slate-500">Unique:</span> {qualityResult.constraint_summary.unique_columns.join(', ') || 'None'}</p>
                                                <p><span className="text-slate-500">Nullable:</span> {qualityResult.constraint_summary.nullable_columns.join(', ') || 'None'}</p>
                                            </div>
                                        )}
                                    </div>
                                    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                                        <p className="text-white font-semibold">Schema Smells</p>
                                        <div className="mt-4 space-y-3">
                                            {qualityResult.schema_smells.length === 0 ? (
                                                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                                    Belirgin schema smell sinyali cikmadi.
                                                </div>
                                            ) : qualityResult.schema_smells.map((smell) => (
                                                <div key={smell.id} className={`rounded-2xl border p-4 ${severityClasses[smell.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
                                                    <p className="font-semibold">{smell.title}</p>
                                                    <p className="mt-2 text-sm">{smell.summary}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                                        <p className="text-white font-semibold">Sample Rows</p>
                                        <pre className="mt-4 max-h-[340px] overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-cyan-300">
                                            {JSON.stringify(qualityResult.sample_rows, null, 2)}
                                        </pre>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                    {result && (
                        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                            <div className="px-6 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
                                <div className="flex items-center gap-4">
                                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${result.success ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'}`}>
                                        {result.success ? <ShieldCheck className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                                        {result.success ? 'Success' : 'Error'}
                                    </div>
                                    <div className="flex items-center gap-2 text-slate-500 text-xs">
                                        <Clock className="h-3 w-3" />
                                        <span className={result.duration_ms > 100 ? 'text-orange-400 font-bold' : ''}>{result.duration_ms} ms</span>
                                    </div>
                                </div>
                                {result.row_count !== undefined && (
                                    <span className="text-xs text-slate-400 font-bold">{result.row_count} rows affected</span>
                                )}
                            </div>

                            <div className="overflow-x-auto">
                                {result.success && result.data && result.data.length > 0 ? (
                                    <table className="w-full text-left text-xs">
                                        <thead className="bg-slate-950 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-800">
                                            <tr>
                                                {Object.keys(result.data[0]).map((key) => (
                                                    <th key={key} className="px-6 py-3">{key}</th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-800 font-mono">
                                            {result.data.map((row: any, i: number) => (
                                                <tr key={i} className="hover:bg-slate-800/50 transition-colors">
                                                    {Object.values(row).map((val: any, j: number) => (
                                                        <td key={j} className="px-6 py-3 text-slate-300">
                                                            {val === null ? <span className="text-slate-600 italic">null</span> : String(val)}
                                                        </td>
                                                    ))}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                ) : (
                                    <div className="p-12 text-center">
                                        {result.success ? (
                                            <div className="text-slate-500">
                                                <Terminal className="h-12 w-12 mx-auto mb-4 opacity-10" />
                                                <p className="font-bold">Query executed successfully, but returned no data.</p>
                                            </div>
                                        ) : (
                                            <div className="text-red-400 bg-red-950/20 p-4 rounded-lg border border-red-900/50 max-w-2xl mx-auto text-left">
                                                <pre className="whitespace-pre-wrap font-mono text-sm">{result.error}</pre>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <div className="space-y-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                            <ListIcon className="h-4 w-4 text-blue-400" />
                            Tables & Schema
                        </h3>
                        <button
                            onClick={fetchTables}
                            className="w-full bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs py-2 rounded mb-4 transition-all"
                        >
                            Refresh Tables
                        </button>
                        <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2">
                            {tables.map((table) => (
                                <button
                                    key={table}
                                    onClick={() => setSelectedTable(table)}
                                    className={`w-full text-left p-2 rounded border transition-all text-xs font-mono ${selectedTable === table ? 'bg-blue-600/20 border-blue-500 text-blue-400' : 'bg-slate-800/50 border-slate-700/50 text-slate-400 hover:bg-slate-800'}`}
                                >
                                    {table}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default DatabasePage;
