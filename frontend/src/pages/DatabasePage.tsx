import { useEffect, useState } from 'react';
import { Clock, Database, List as ListIcon, Loader2, RefreshCw } from 'lucide-react';

import { api, DbHistoryItem, DbQualityResponse } from '../services/api';

const severityClasses: Record<string, string> = {
    high: 'border-red-500/40 bg-red-500/10 text-red-200',
    medium: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
    low: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
};

export function DatabasePage() {
    const [connString, setConnString] = useState('postgresql://visionqa:visionqa_dev_password@localhost:5432/visionqa_db');
    const [query, setQuery] = useState('SELECT * FROM projects LIMIT 5');
    const [loading, setLoading] = useState(false);
    const [qualityResult, setQualityResult] = useState<DbQualityResponse | null>(null);
    const [tables, setTables] = useState<string[]>([]);
    const [selectedTable, setSelectedTable] = useState('');
    const [expectedColumns, setExpectedColumns] = useState('');
    const [apiExpectedFields, setApiExpectedFields] = useState('');
    const [historyItems, setHistoryItems] = useState<DbHistoryItem[]>([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const [historyError, setHistoryError] = useState('');

    const loadHistory = async () => {
        setHistoryLoading(true);
        setHistoryError('');
        try {
            const items = await api.getDbHistory(12);
            setHistoryItems(items);
        } catch (error: any) {
            console.warn('DB history could not be loaded', error);
            setHistoryError(error.response?.status === 404
                ? 'DB History endpoint bulunamadi. Backend yeniden baslatilmali.'
                : 'DB history yuklenemedi. Backend loglarini kontrol et.');
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        loadHistory();
    }, []);

    const fetchTables = async () => {
        try {
            const response = await fetch(`/api/db-test/tables?connection_string=${encodeURIComponent(connString)}`);
            const data = await response.json();
            setTables(data);
        } catch {
            console.error('Tablo listesi alinamadi');
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
            loadHistory();
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

    const openHistoryItem = async (recordId: number) => {
        try {
            const detail = await api.getDbHistoryDetail(recordId);
            if (detail.analysis_payload) {
                setQualityResult(detail.analysis_payload);
                if (detail.analysis_payload.table_name) {
                    setSelectedTable(detail.analysis_payload.table_name);
                }
            }
        } catch {
            alert('Database history kaydi acilamadi.');
        }
    };

    return (
        <div className="mx-auto max-w-[1320px] space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-5">
                <div className="flex items-center gap-4">
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-blue-400/20 bg-blue-500/10 text-blue-300">
                        <Database className="h-7 w-7" />
                    </div>
                    <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-300">Database Quality</p>
                        <h1 className="mt-1 text-3xl font-bold text-white">
                            Veritabani Kalite Modulu
                        </h1>
                        <p className="mt-2 text-sm text-slate-400">
                            SQL sorgu analizi, sema kontrolu ve veri tutarlilik sinyalleri.
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_380px] xl:items-start">
                <div className="space-y-6">
                    <div className="rounded-lg border border-slate-800 bg-slate-900/90 p-5 shadow-xl shadow-black/10">
                        <div className="mb-5 flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
                            <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">Audit Workspace</p>
                                <p className="mt-2 text-sm text-slate-300">Query, schema ve API alan beklentileri tek kalite raporuna donusur.</p>
                            </div>
                            <button
                                onClick={handleQualityAudit}
                                disabled={loading}
                                className="hidden min-w-[180px] items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50 md:flex"
                            >
                                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                                Run Quality Audit
                            </button>
                        </div>

                        <div className="mb-5">
                            <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">Connection String</label>
                            <input
                                type="text"
                                value={connString}
                                onChange={(e) => setConnString(e.target.value)}
                                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 font-mono text-sm text-white outline-none transition focus:border-blue-400"
                            />
                        </div>

                        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
                            <div>
                                <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">SQL Editor</label>
                                <textarea
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    rows={8}
                                    className="min-h-[246px] w-full resize-y rounded-lg border border-slate-800 bg-slate-950 px-4 py-4 font-mono text-sm leading-6 text-cyan-300 shadow-inner outline-none transition focus:border-blue-400"
                                />
                            </div>

                            <div className="space-y-4 rounded-lg border border-slate-800 bg-slate-950/70 p-4">
                                <div>
                                    <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">Selected Table</label>
                                    <div className="min-h-[42px] truncate rounded-lg border border-slate-800 bg-slate-900 px-3 py-2.5 text-sm text-white">
                                        {selectedTable || 'No table selected'}
                                    </div>
                                </div>
                                <div>
                                    <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">Expected Columns</label>
                                    <input
                                        type="text"
                                        value={expectedColumns}
                                        onChange={(e) => setExpectedColumns(e.target.value)}
                                        placeholder="id,name,created_at"
                                        className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none transition focus:border-blue-400"
                                    />
                                </div>
                                <div>
                                    <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">API Expected Fields</label>
                                    <input
                                        type="text"
                                        value={apiExpectedFields}
                                        onChange={(e) => setApiExpectedFields(e.target.value)}
                                        placeholder="email,status,role"
                                        className="w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2.5 text-sm text-white outline-none transition focus:border-blue-400"
                                    />
                                </div>
                                <button
                                    onClick={handleQualityAudit}
                                    disabled={loading}
                                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:opacity-50 md:hidden"
                                >
                                    {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                                    Run Quality Audit
                                </button>
                            </div>
                        </div>
                    </div>

                    {qualityResult && (
                        <>
                            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Overall</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{qualityResult.overall_score}</p>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Table Quality</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{qualityResult.table_quality_score}</p>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Duration</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{Math.round(qualityResult.duration_ms)}</p>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Findings</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{qualityResult.findings.length}</p>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                                    <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Columns</p>
                                    <p className="mt-3 text-3xl font-semibold text-white">{qualityResult.detected_columns.length}</p>
                                </div>
                            </div>

                            <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
                                <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
                                    <p className="text-white font-semibold">AI Interpretation</p>
                                    <p className="mt-3 text-sm text-slate-300">{qualityResult.ai_interpretation}</p>
                                    <div className="mt-4 rounded-lg border border-slate-800 bg-slate-950 p-4">
                                        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Root Cause Summary</p>
                                        <p className="mt-2 text-sm text-slate-300">{qualityResult.root_cause_summary}</p>
                                    </div>
                                </div>

                                <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
                                    <p className="text-white font-semibold">Score Breakdown</p>
                                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                                        {Object.entries(qualityResult.score_breakdown).map(([label, value]) => (
                                            <div key={label} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{label}</p>
                                                <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
                                <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
                                    <p className="text-white font-semibold">Quality Findings</p>
                                    <p className="mt-1 text-sm text-slate-400">{qualityResult.summary}</p>
                                    <div className="mt-4 space-y-3">
                                        {qualityResult.findings.length === 0 ? (
                                            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                                Bu kosumda belirgin DB kalite bulgusu cikmadi.
                                            </div>
                                        ) : qualityResult.findings.map((finding) => (
                                            <div key={finding.id} className={`rounded-lg border p-4 ${severityClasses[finding.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
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
                                    <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
                                        <p className="text-white font-semibold">Schema Snapshot</p>
                                    <div className="mt-4 flex flex-wrap gap-2">
                                        {qualityResult.detected_columns.map((column) => (
                                            <span key={column} className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-200">
                                                {column}
                                            </span>
                                        ))}
                                    </div>
                                        {qualityResult.constraint_summary && (
                                            <div className="mt-4 space-y-3 rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                                <p><span className="text-slate-500">Primary Keys:</span> {qualityResult.constraint_summary.primary_keys.join(', ') || 'None'}</p>
                                                <p><span className="text-slate-500">Foreign Keys:</span> {qualityResult.constraint_summary.foreign_keys.join(', ') || 'None'}</p>
                                                <p><span className="text-slate-500">Unique:</span> {qualityResult.constraint_summary.unique_columns.join(', ') || 'None'}</p>
                                                <p><span className="text-slate-500">Nullable:</span> {qualityResult.constraint_summary.nullable_columns.join(', ') || 'None'}</p>
                                            </div>
                                        )}
                                    </div>
                                    <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
                                        <p className="text-white font-semibold">Schema Smells</p>
                                        <div className="mt-4 space-y-3">
                                            {qualityResult.schema_smells.length === 0 ? (
                                                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                                    Belirgin schema smell sinyali cikmadi.
                                                </div>
                                            ) : qualityResult.schema_smells.map((smell) => (
                                                <div key={smell.id} className={`rounded-lg border p-4 ${severityClasses[smell.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
                                                    <p className="font-semibold">{smell.title}</p>
                                                    <p className="mt-2 text-sm">{smell.summary}</p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="rounded-lg border border-slate-800 bg-slate-900 p-5">
                                        <p className="text-white font-semibold">Sample Rows</p>
                                        <pre className="mt-4 max-h-[340px] overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-cyan-300">
                                            {JSON.stringify(qualityResult.sample_rows, null, 2)}
                                        </pre>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                </div>

                <div className="space-y-5 xl:sticky xl:top-6">
                    <div className="rounded-lg border border-slate-800 bg-slate-900/90 p-5">
                        <div className="mb-4 flex items-center justify-between gap-3">
                            <h3 className="flex items-center gap-2 text-sm font-bold text-white">
                                <ListIcon className="h-4 w-4 text-blue-400" />
                                Tables & Schema
                            </h3>
                            <span className="rounded-full border border-slate-700 px-2.5 py-1 text-[11px] font-semibold text-slate-400">
                                {tables.length}
                            </span>
                        </div>
                        <button
                            onClick={fetchTables}
                            className="mb-4 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-xs font-semibold text-slate-200 transition hover:border-blue-500/40 hover:bg-slate-800/80"
                        >
                            Refresh Tables
                        </button>
                        <div className="max-h-[300px] space-y-2 overflow-y-auto pr-2">
                            {tables.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-slate-700 bg-slate-950/60 p-4 text-sm text-slate-400">
                                    Tablo listesini almak icin Refresh Tables calistir.
                                </div>
                            ) : tables.map((table) => (
                                <button
                                    key={table}
                                    onClick={() => setSelectedTable(table)}
                                    className={`w-full rounded-lg border px-3 py-2.5 text-left font-mono text-xs transition ${selectedTable === table ? 'border-blue-500 bg-blue-600/15 text-blue-200' : 'border-slate-800 bg-slate-950/70 text-slate-400 hover:border-slate-700 hover:bg-slate-900'}`}
                                >
                                    {table}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="rounded-lg border border-slate-800 bg-slate-900/90 p-5">
                        <div className="flex items-center justify-between gap-3">
                            <h3 className="text-sm font-bold text-white flex items-center gap-2">
                                <Clock className="h-4 w-4 text-cyan-400" />
                                DB History
                            </h3>
                            <button
                                type="button"
                                onClick={loadHistory}
                                disabled={historyLoading}
                                className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-cyan-500/40 hover:bg-slate-800 disabled:opacity-60"
                            >
                                <RefreshCw className={`inline h-3.5 w-3.5 ${historyLoading ? 'animate-spin' : ''}`} />
                            </button>
                        </div>
                        <div className="mt-4 max-h-[520px] space-y-3 overflow-y-auto pr-2">
                            {historyError ? (
                                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
                                    {historyError}
                                </div>
                            ) : historyItems.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-slate-700 bg-slate-950/60 p-4 text-sm text-slate-400">
                                    Kayitli DB kalite analizi yok. Run Quality Audit calistirinca burada gorunecek.
                                </div>
                            ) : historyItems.map((item) => (
                                <button
                                    key={item.id}
                                    type="button"
                                    onClick={() => openHistoryItem(item.id)}
                                    className="w-full rounded-lg border border-slate-800 bg-slate-950/70 p-4 text-left transition hover:border-blue-500/40 hover:bg-slate-950"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <p className="truncate text-sm font-semibold text-white" title={item.source_label || item.table_name || 'DB quality audit'}>
                                                {item.source_label || item.table_name || 'DB quality audit'}
                                            </p>
                                            <p className="mt-1 truncate text-xs text-slate-500">
                                                {item.created_at ? new Date(item.created_at).toLocaleString('tr-TR') : 'unknown time'}
                                            </p>
                                        </div>
                                        <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${item.success === false ? 'border-red-500/40 bg-red-500/10 text-red-200' : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'}`}>
                                            {item.overall_score}
                                        </span>
                                    </div>
                                    <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-slate-300">
                                        <span className="truncate rounded-full border border-slate-700 px-2 py-1 text-center">{item.source_type}</span>
                                        <span className="rounded-full border border-slate-700 px-2 py-1 text-center">{item.findings_count} finding</span>
                                        <span className="rounded-full border border-slate-700 px-2 py-1 text-center">{item.detected_columns_count} cols</span>
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

export default DatabasePage;
