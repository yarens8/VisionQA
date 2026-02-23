
import { useState } from 'react';
import { Database, Terminal, Play, Loader2, Clock, AlertCircle, ShieldCheck, List as ListIcon } from 'lucide-react';
import axios from 'axios';

export function DatabasePage() {
    const [connString, setConnString] = useState('postgresql://visionqa:visionqa_dev_password@localhost:5432/visionqa_db');
    const [query, setQuery] = useState('SELECT * FROM projects LIMIT 5');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [tables, setTables] = useState<string[]>([]);
    const [selectedTable, setSelectedTable] = useState('');

    const fetchTables = async () => {
        try {
            const response = await axios.get(`/api/db-test/tables?connection_string=${encodeURIComponent(connString)}`);
            setTables(response.data);
        } catch (e) {
            console.error("Tablo listesi alınamadı");
        }
    };

    const handleRunQuery = async () => {
        setLoading(true);
        setResult(null);
        try {
            const response = await axios.post('/api/db-test/query', {
                connection_string: connString,
                query: query
            });
            setResult(response.data);
            if (response.data.success) fetchTables();
        } catch (error: any) {
            setResult({
                success: false,
                error: error.response?.data?.detail || error.message
            });
        } finally {
            setLoading(false);
        }
    };

    const handleValidateSchema = async () => {
        if (!selectedTable) return;
        setLoading(true);
        try {
            const response = await axios.post('/api/db-test/validate-schema', {
                connection_string: connString,
                table_name: selectedTable,
                expected_columns: []
            });
            setResult({ ...response.data, isSchemaValidation: true });
        } catch (error: any) {
            setResult({ success: false, error: error.message });
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
                        Database Playground (Pro)
                    </h1>
                    <p className="text-slate-400 mt-2">
                        SQL Sorgu Analizi, Şema Doğrulama ve Performans Takibi.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Sol Panel: Editor */}
                <div className="lg:col-span-3 space-y-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                        <div className="mb-4">
                            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 block">Connection String (SQLAlchemy)</label>
                            <input
                                type="text"
                                value={connString}
                                onChange={(e) => setConnString(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 text-sm font-mono outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>

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
                    </div>

                    {/* Result Table */}
                    {result && (
                        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
                            <div className="px-6 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
                                <div className="flex items-center gap-4">
                                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${result.success ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'}`}>
                                        {result.success ? <ShieldCheck className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                                        {result.success ? (result.isSchemaValidation ? 'Schema Valid' : 'Success') : 'Error'}
                                    </div>
                                    <div className="flex items-center gap-2 text-slate-500 text-xs">
                                        <Clock className="h-3 w-3" />
                                        <span className={result.duration_ms > 100 ? 'text-orange-400 font-bold' : ''}>{result.duration_ms} ms</span>
                                        {result.duration_ms > 100 && <span className="text-[10px] text-orange-500/50">(Slow Query)</span>}
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

                {/* Sağ Panel: Tables & Schema */}
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
                            {tables.map(table => (
                                <div key={table} className="flex flex-col gap-1">
                                    <button
                                        onClick={() => setSelectedTable(table)}
                                        className={`w-full text-left p-2 rounded border transition-all text-xs font-mono ${selectedTable === table ? 'bg-blue-600/20 border-blue-500 text-blue-400' : 'bg-slate-800/50 border-slate-700/50 text-slate-400 hover:bg-slate-800'}`}
                                    >
                                        {table}
                                    </button>
                                    {selectedTable === table && (
                                        <button
                                            onClick={handleValidateSchema}
                                            className="text-[9px] bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-1 px-2 rounded ml-2 transition-all flex items-center justify-center gap-1"
                                        >
                                            <ShieldCheck className="h-3 w-3" /> Validate Schema
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default DatabasePage;
