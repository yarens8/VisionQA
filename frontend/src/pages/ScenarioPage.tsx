
import { useState } from 'react';
import { Layers, Plus, Play, Trash2, ChevronDown, ChevronUp, Save, Loader2, CheckCircle2, XCircle, Clock, Zap, Globe, Database, FlaskConical } from 'lucide-react';
import axios from 'axios';

interface Step {
    id: string;
    platform: 'web' | 'api' | 'db';
    action: string;
    params: any;
    variable_output?: string;
}

export function ScenarioPage() {
    const [name, setName] = useState('New Integration Scenario');
    const [steps, setSteps] = useState<Step[]>([]);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<any>(null);

    const addStep = (platform: 'web' | 'api' | 'db') => {
        const newStep: Step = {
            id: Math.random().toString(36).substr(2, 9),
            platform,
            action: platform === 'api' ? 'GET' : (platform === 'db' ? 'query' : 'navigate'),
            params: platform === 'api' ? { url: '', method: 'GET' } : (platform === 'db' ? { connection_string: '', query: '' } : { url: '' }),
        };
        setSteps([...steps, newStep]);
    };

    const updateStep = (id: string, updates: Partial<Step>) => {
        setSteps(steps.map(s => s.id === id ? { ...s, ...updates } : s));
    };

    const removeStep = (id: string) => {
        setSteps(steps.filter(s => s.id !== id));
    };

    const moveStep = (index: number, direction: 'up' | 'down') => {
        const newSteps = [...steps];
        const newIndex = direction === 'up' ? index - 1 : index + 1;
        if (newIndex >= 0 && newIndex < steps.length) {
            [newSteps[index], newSteps[newIndex]] = [newSteps[newIndex], newSteps[index]];
            setSteps(newSteps);
        }
    };

    const handleRunScenario = async () => {
        setLoading(true);
        setResults(null);
        try {
            const response = await axios.post('/api/scenarios/run', {
                name,
                steps: steps.map(({ platform, action, params, variable_output }) => ({
                    platform,
                    action,
                    params,
                    variable_output
                }))
            });
            setResults(response.data);
        } catch (error: any) {

            alert("Scenario execution failed: " + error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-3">
                        <Layers className="h-8 w-8 text-indigo-500" />
                        Scenario <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">Orchestrator</span>
                    </h1>
                    <p className="text-slate-400 mt-1">Chain multiple platforms into a single end-to-end test story.</p>
                </div>
                <div className="flex gap-3">
                    <button className="h-11 px-6 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold transition-all flex items-center gap-2">
                        <Save className="h-4 w-4" /> Save
                    </button>
                    <button
                        onClick={handleRunScenario}
                        disabled={loading || steps.length === 0}
                        className="h-11 px-6 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-black transition-all flex items-center gap-2 shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                    >
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-current" />}
                        Run Story
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Steps Builder */}
                <div className="lg:col-span-2 space-y-4">
                    <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
                        <input
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            className="bg-transparent border-none text-xl font-bold text-white w-full focus:ring-0 mb-6 placeholder:text-slate-700"
                            placeholder="Enter Scenario Name..."
                        />

                        <div className="space-y-4">
                            {steps.length === 0 && (
                                <div className="py-20 text-center border-2 border-dashed border-slate-800 rounded-3xl">
                                    <Plus className="h-12 w-12 mx-auto mb-4 opacity-10 text-slate-500" />
                                    <p className="text-slate-500 font-bold">No steps added yet. Start by adding a step below.</p>
                                </div>
                            )}

                            {steps.map((step, index) => (
                                <div key={step.id} className="bg-slate-950 border border-slate-800 rounded-2xl p-5 group hover:border-indigo-500/30 transition-all relative overflow-hidden">
                                    <div className={`absolute top-0 left-0 bottom-0 w-1 ${step.platform === 'web' ? 'bg-blue-500' : (step.platform === 'api' ? 'bg-purple-500' : 'bg-emerald-500')}`} />

                                    <div className="flex items-center justify-between mb-4">
                                        <div className="flex items-center gap-3">
                                            <div className="h-8 w-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-xs font-black text-slate-500">
                                                {index + 1}
                                            </div>
                                            <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded ${step.platform === 'web' ? 'bg-blue-500/10 text-blue-400' : (step.platform === 'api' ? 'bg-purple-500/10 text-purple-400' : 'bg-emerald-500/10 text-emerald-400')}`}>
                                                {step.platform}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button onClick={() => moveStep(index, 'up')} className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-500"><ChevronUp className="h-4 w-4" /></button>
                                            <button onClick={() => moveStep(index, 'down')} className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-500"><ChevronDown className="h-4 w-4" /></button>
                                            <button onClick={() => removeStep(step.id)} className="p-1.5 hover:bg-red-500/20 hover:text-red-500 rounded-lg text-slate-500"><Trash2 className="h-4 w-4" /></button>
                                        </div>
                                    </div>

                                    {/* Step Parameters */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-bold text-slate-600 uppercase">Action</label>
                                            <select
                                                value={step.action}
                                                onChange={(e) => updateStep(step.id, { action: e.target.value })}
                                                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white outline-none focus:border-indigo-500"
                                            >
                                                {step.platform === 'api' ? ['GET', 'POST', 'PUT', 'DELETE'].map(a => <option key={a}>{a}</option>) :
                                                    step.platform === 'db' ? ['query', 'validate-schema'].map(a => <option key={a}>{a}</option>) :
                                                        ['navigate', 'click', 'type', 'verify'].map(a => <option key={a}>{a}</option>)}
                                            </select>
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-bold text-slate-600 uppercase">Store Output As (Variable)</label>
                                            <input
                                                value={step.variable_output || ''}
                                                onChange={(e) => updateStep(step.id, { variable_output: e.target.value })}
                                                placeholder="e.g. user_id"
                                                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-sm text-white outline-none focus:border-indigo-500"
                                            />
                                        </div>
                                        <div className="col-span-2 space-y-2">
                                            <label className="text-[10px] font-bold text-slate-600 uppercase">Parameters (JSON or Text)</label>
                                            <textarea
                                                value={typeof step.params === 'object' ? JSON.stringify(step.params, null, 2) : step.params}
                                                onChange={(e) => {
                                                    try {
                                                        const p = JSON.parse(e.target.value);
                                                        updateStep(step.id, { params: p });
                                                    } catch {
                                                        // Hata olsa da allow string edit
                                                    }
                                                }}
                                                rows={3}
                                                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-xs font-mono text-cyan-400 outline-none focus:border-indigo-500"
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Add Step Buttons */}
                        <div className="mt-8 flex items-center gap-3">
                            <button onClick={() => addStep('web')} className="flex-1 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/20 text-blue-400 py-3 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all">
                                <Globe className="h-4 w-4" /> Add Web Step
                            </button>
                            <button onClick={() => addStep('api')} className="flex-1 bg-purple-600/10 hover:bg-purple-600/20 border border-purple-500/20 text-purple-400 py-3 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all">
                                <FlaskConical className="h-4 w-4" /> Add API Step
                            </button>
                            <button onClick={() => addStep('db')} className="flex-1 bg-emerald-600/10 hover:bg-emerald-600/20 border border-emerald-500/20 text-emerald-400 py-3 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all">
                                <Database className="h-4 w-4" /> Add DB Step
                            </button>
                        </div>
                    </div>
                </div>

                {/* Live Execution Results */}
                <div className="space-y-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sticky top-6">
                        <h2 className="text-xl font-black text-white mb-6 flex items-center gap-2">
                            <Zap className="h-5 w-5 text-yellow-400 fill-yellow-400" />
                            Live Timeline
                        </h2>

                        {!results && !loading && (
                            <div className="text-center py-10 opacity-20 italic text-sm text-slate-500">
                                Run the story to see execution timeline...
                            </div>
                        )}

                        {loading && (
                            <div className="flex flex-col items-center py-10">
                                <Loader2 className="h-10 w-10 animate-spin text-indigo-500 mb-4" />
                                <p className="text-sm font-bold text-slate-400 animate-pulse">Executing Story Steps...</p>
                            </div>
                        )}

                        {results && (
                            <div className="space-y-4">
                                {results.results.map((res: any, i: number) => (
                                    <div key={i} className={`p-4 rounded-xl border flex gap-4 ${res.success ? 'bg-green-500/5 border-green-500/10' : 'bg-red-500/5 border-red-500/10'}`}>
                                        <div className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${res.success ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                                            {res.success ? <CheckCircle2 className="h-5 w-5" /> : <XCircle className="h-5 w-5" />}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-[10px] font-black uppercase text-slate-500">{res.platform} Step</span>
                                                <span className="text-[10px] text-slate-600 font-mono flex items-center gap-1"><Clock className="h-2 w-2" />{res.duration_ms}ms</span>
                                            </div>
                                            <p className="text-xs font-bold text-white truncate">{res.action} executed</p>
                                            {res.error && <p className="text-[10px] text-red-400 mt-1 italic">{res.error}</p>}
                                        </div>
                                    </div>
                                ))}

                                <div className="pt-6 border-t border-slate-800">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-xs font-bold text-slate-500 uppercase">Context Snapshot</span>
                                        <span className={`text-[10px] px-2 py-0.5 rounded font-black ${results.success ? 'bg-green-500 text-black' : 'bg-red-500 text-white'}`}>
                                            {results.success ? 'PASSED' : 'FAILED'}
                                        </span>
                                    </div>
                                    <pre className="p-4 bg-slate-950 rounded-xl text-[10px] text-indigo-300 font-mono overflow-auto max-h-[300px] border border-white/5">
                                        {JSON.stringify(results.final_context, null, 2)}
                                    </pre>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
export default ScenarioPage;
