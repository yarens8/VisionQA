
import { useState } from 'react';
import { FlaskConical, Send, Loader2, Clock, Zap, Download, List as ListIcon } from 'lucide-react';
import axios from 'axios';

export function TestLabPage() {
    const [method, setMethod] = useState('GET');
    const [url, setUrl] = useState('https://jsonplaceholder.typicode.com/todos/1');
    const [body, setBody] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [loadTestCount, setLoadTestCount] = useState(10);
    const [isLoadTest, setIsLoadTest] = useState(false);
    const [swaggerUrl, setSwaggerUrl] = useState('https://petstore.swagger.io/v2/swagger.json');
    const [endpoints, setEndpoints] = useState<any[]>([]);

    const handleRunTest = async () => {
        setLoading(true);
        setResult(null);
        setIsLoadTest(false);
        try {
            const endpoint = isLoadTest ? 'load-test' : 'run';
            const params = isLoadTest ? `?count=${loadTestCount}` : '';
            const response = await axios.post(`/api/api-test/${endpoint}${params}`, {
                method,
                url,
                body: body ? JSON.parse(body) : null
            });
            setResult(response.data);
        } catch (error: any) {
            setResult({
                success: false,
                error: error.response?.data?.detail || error.message
            });
        } finally {
            setLoading(false);
        }
    };

    const handleImportSwagger = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`/api/api-test/import-swagger?url=${swaggerUrl}`);
            setEndpoints(response.data);
        } catch (error: any) {

            alert("Swagger import hatası!");
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
                        API Test Lab (Pro)
                    </h1>
                    <p className="text-slate-400 mt-2">
                        Swagger Import, Load Test ve Manuel API kontrolleri.
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Sol Panel: Config */}
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
                            </select>
                            <input
                                type="text"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                                placeholder="API URL"
                                className="flex-1 bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 focus:ring-2 focus:ring-purple-500 outline-none"
                            />
                        </div>

                        {method !== 'GET' && (
                            <textarea
                                value={body}
                                onChange={(e) => setBody(e.target.value)}
                                rows={4}
                                placeholder='{"key": "value"}'
                                className="w-full bg-slate-800 border border-slate-700 text-white rounded-lg px-4 py-2 font-mono text-sm mb-4 outline-none"
                            />
                        )}

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
                                {isLoadTest ? 'Run Load Test' : 'Send Request'}
                            </button>
                        </div>
                    </div>

                    {/* Results */}
                    {result && (
                        <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                            <div className="bg-slate-900 px-6 py-3 border-b border-slate-800 flex justify-between">
                                <div className="flex gap-4 items-center">
                                    <span className={`text-sm font-bold ${result.success !== false ? 'text-green-500' : 'text-red-500'}`}>
                                        {result.success !== false ? (result.status_code || 'SUCCESS') : 'FAILED'}
                                    </span>
                                    <span className="text-slate-500 text-xs flex items-center gap-1">
                                        <Clock className="h-3 w-3" /> {result.duration_ms || result.avg_duration_ms} ms
                                    </span>
                                </div>
                                {result.p95_duration_ms && (
                                    <span className="text-orange-400 text-xs font-bold">P95: {result.p95_duration_ms}ms</span>
                                )}
                            </div>
                            <pre className="p-6 text-cyan-400 font-mono text-xs overflow-auto max-h-[400px]">
                                {JSON.stringify(result, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>

                {/* Sağ Panel: Swagger & History */}
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
                                    className="w-full text-left p-2 bg-slate-800/50 hover:bg-slate-800 rounded border border-slate-700/50 group transition-all"
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
                </div>
            </div>
        </div>
    );
}

export default TestLabPage;
