
import { useEffect, useState, useMemo } from 'react';
import { Activity, CheckCircle2, XCircle, Clock, AlertTriangle, ChevronRight, Search, Filter, Trash2, Calendar, Globe, Sparkles, Zap } from "lucide-react";
import { formatDistanceToNow } from 'date-fns';
import { tr } from 'date-fns/locale';
import axios from 'axios';
import { api, Project } from '../services/api';


interface StepLog {
    order: number;
    action: string;
    action_label?: string;
    target: string;
    value?: string;
    status: 'passed' | 'failed';
    reason?: string;
    error?: string;
}

interface TestRun {
    id: number;
    project_id: number;
    project_name: string;
    platform: string;
    status: string;
    started_at: string | null;
    completed_at: string | null;
    target: string;
    logs?: string;
}

// ─── Logs Detail Modal ───────────────────────────────────────────────
function LogsModal({ run, onClose }: { run: TestRun; onClose: () => void }) {
    let steps: StepLog[] = [];
    let summary: string | null = null;

    try {
        const parsed = JSON.parse(run.logs || '[]');
        if (Array.isArray(parsed)) {
            steps = parsed;
        } else if (typeof parsed === 'object' && parsed !== null) {
            steps = parsed.steps || [];
            summary = parsed.summary || null;
        }
    } catch (e) {
        console.error("Logs parse error", e);
    }

    const passed = steps.filter(s => s.status === 'passed').length;

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-in fade-in duration-300">
            <div className="bg-slate-900 border border-slate-700/50 rounded-3xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-300">
                {/* Header */}
                <div className="flex items-center justify-between px-8 py-6 border-b border-slate-800 bg-slate-900/50">
                    <div className="flex items-center gap-5">
                        <div className={`h-14 w-14 rounded-2xl flex items-center justify-center border shadow-lg ${run.status === 'completed' ? 'bg-green-500/10 border-green-500/30 text-green-500' : 'bg-red-500/10 border-red-500/30 text-red-500'}`}>
                            {run.status === 'completed' ? <CheckCircle2 className="h-8 w-8" /> : <XCircle className="h-8 w-8" />}
                        </div>
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-[10px] font-black text-blue-400 uppercase tracking-[0.2em]">Deployment Report</span>
                                <span className="h-1 w-1 rounded-full bg-slate-700" />
                                <span className="text-[10px] font-mono text-slate-500">RUN_ID: #{run.id}</span>
                            </div>
                            <h2 className="text-2xl font-black text-white tracking-tight">{run.project_name}</h2>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => axios.post(`/api/reports/${run.id}/send-to-jira`).then(() => alert("Jira Ticket Created!"))}
                            className="bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest border border-blue-500/20 transition-all"
                        >
                            Jira
                        </button>
                        <button
                            onClick={() => axios.post(`/api/reports/${run.id}/notify-slack`).then(() => alert("Slack Notified!"))}
                            className="bg-purple-600/20 hover:bg-purple-600/40 text-purple-400 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest border border-purple-500/20 transition-all"
                        >
                            Slack
                        </button>
                        <button
                            onClick={() => window.open(`/api/reports/${run.id}/json`)}
                            className="bg-slate-800 hover:bg-slate-700 text-blue-400 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-2 transition-all"
                        >
                            Export JSON
                        </button>

                        <button
                            onClick={onClose}
                            className="h-12 w-12 flex items-center justify-center rounded-2xl bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition-all active:scale-90"
                        >
                            <XCircle className="h-6 w-6" />
                        </button>
                    </div>


                </div>

                {/* Content */}
                <div className="overflow-y-auto flex-1 p-8 space-y-6 bg-slate-950/20">
                    {/* AI Intelligence Summary */}
                    {summary && (
                        <div className="bg-gradient-to-br from-indigo-600/10 to-blue-600/10 border border-indigo-500/20 rounded-2xl p-6 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                                <Sparkles className="h-20 w-20 text-indigo-400" />
                            </div>
                            <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-3 flex items-center gap-2">
                                <Zap className="h-3 w-3 fill-current" /> AI Intelligence Summary
                            </h3>
                            <p className="text-slate-200 text-sm leading-relaxed font-medium italic">
                                "{summary}"
                            </p>
                        </div>
                    )}

                    {/* Step Logs */}
                    <div>
                        <h3 className="text-[10px] font-black text-slate-600 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <Activity className="h-3 w-3" /> Protocol Execution Logs
                        </h3>

                        {steps.length === 0 ? (
                            <div className="py-20 text-center text-slate-700 border-2 border-dashed border-slate-800 rounded-3xl">
                                <Activity className="h-12 w-12 mx-auto mb-4 opacity-10" />
                                <p className="font-bold text-sm">No protocol data available for this run.</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {steps.map((step, i) => (
                                    <div key={i} className={`p-5 rounded-2xl border transition-all ${step.status === 'passed'
                                        ? 'bg-slate-900/50 border-slate-800 hover:border-green-500/30'
                                        : 'bg-red-500/5 border-red-500/20 hover:border-red-500/40'
                                        }`}>
                                        <div className="flex gap-5">
                                            <div className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 border ${step.status === 'passed' ? 'bg-green-500/10 border-green-500/20 text-green-500' : 'bg-red-500/10 border-red-500/20 text-red-500'
                                                }`}>
                                                <span className="text-xs font-black">{step.order}</span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="font-black text-white text-xs uppercase tracking-tight">
                                                        {step.action_label || step.action}
                                                    </span>
                                                    <span className={`text-[9px] px-2 py-0.5 rounded-md font-black uppercase tracking-widest ${step.status === 'passed' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
                                                        }`}>
                                                        {step.status}
                                                    </span>
                                                </div>
                                                <code className="text-[10px] text-slate-500 block p-2 bg-black/40 rounded-lg border border-white/5 break-all mb-3 font-mono">
                                                    {step.target}
                                                </code>
                                                {step.reason && (
                                                    <div className="flex items-start gap-2 bg-slate-950/50 p-3 rounded-xl border border-white/5">
                                                        <Sparkles className="h-3 w-3 mt-0.5 text-indigo-500 shrink-0" />
                                                        <p className="text-xs leading-relaxed text-slate-400 font-medium italic">
                                                            {step.reason}
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer summary */}
                <div className="px-8 py-5 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between">
                    <div className="flex gap-8">
                        <div className="flex flex-col">
                            <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Successful</span>
                            <span className="text-green-400 font-black text-2xl">{passed}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest">Compromised</span>
                            <span className="text-red-400 font-black text-2xl">{steps.length - passed}</span>
                        </div>
                    </div>
                    <div className="text-right">
                        <span className="text-[10px] text-slate-500 uppercase font-black tracking-widest block mb-1">Pass Ratio</span>
                        <div className="h-2 w-48 bg-slate-800 rounded-full overflow-hidden mb-1">
                            <div
                                className={`h-full transition-all duration-1000 ${passed === steps.length ? 'bg-green-500' : 'bg-blue-600'}`}
                                style={{ width: `${steps.length > 0 ? (passed / steps.length) * 100 : 0}%` }}
                            />
                        </div>
                        <span className="text-white font-black text-lg">{steps.length > 0 ? Math.round((passed / steps.length) * 100) : 0}%</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ─── Ana Sayfa ───────────────────────────────────────────────────────
export function TestRunsPage() {
    const [runs, setRuns] = useState<TestRun[]>([]);
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedRun, setSelectedRun] = useState<TestRun | null>(null);

    // Filters state
    const [searchTerm, setSearchTerm] = useState('');
    const [filterPlatform, setFilterPlatform] = useState('all');
    const [filterStatus, setFilterStatus] = useState('all');
    const [filterProject, setFilterProject] = useState('all');

    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const [runsData, projectsData] = await Promise.all([
                    fetch('/api/execution/runs').then(res => res.json()),
                    api.getProjects()
                ]);
                setRuns(runsData);
                setProjects(projectsData);
            } catch (error) {
                console.error("Data yüklenirken hata:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchInitialData();

        // Polling — 5 sn'de bir sadece run'ları güncelle
        const interval = setInterval(async () => {
            try {
                const response = await fetch('/api/execution/runs');
                if (response.ok) {
                    const data = await response.json();
                    setRuns(data);
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 5000);

        return () => clearInterval(interval);
    }, []);

    // Memoized filtered runs
    const filteredRuns = useMemo(() => {
        return runs.filter(run => {
            const matchesSearch = run.project_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                run.target.toLowerCase().includes(searchTerm.toLowerCase());
            const matchesPlatform = filterPlatform === 'all' || run.platform === filterPlatform;
            const matchesStatus = filterStatus === 'all' || run.status === filterStatus;
            const matchesProject = filterProject === 'all' || run.project_id === Number(filterProject);

            return matchesSearch && matchesPlatform && matchesStatus && matchesProject;
        });
    }, [runs, searchTerm, filterPlatform, filterStatus, filterProject]);

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed': return <CheckCircle2 className="h-4 w-4 text-green-500" />;
            case 'failed': return <XCircle className="h-4 w-4 text-red-500" />;
            case 'running': return <Activity className="h-4 w-4 text-blue-500 animate-spin" />;
            case 'crashed': return <AlertTriangle className="h-4 w-4 text-orange-500" />;
            default: return <Clock className="h-4 w-4 text-slate-500" />;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return "bg-green-500/10 text-green-400 border-green-500/20";
            case 'failed': return "bg-red-500/10 text-red-400 border-red-500/20";
            case 'running': return "bg-blue-500/10 text-blue-400 border-blue-500/20";
            case 'crashed': return "bg-orange-500/10 text-orange-400 border-orange-500/20";
            default: return "bg-slate-800 text-slate-400 border-slate-700";
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Detail Modal */}
            {selectedRun && <LogsModal run={selectedRun} onClose={() => setSelectedRun(null)} />}

            {/* Header Area */}
            <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                        <span className="text-xs font-bold text-blue-500 uppercase tracking-widest">Real-time Intelligence</span>
                    </div>
                    <h1 className="text-4xl font-black text-white tracking-tight">
                        Test <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400">Execution</span> History
                    </h1>
                    <p className="text-slate-400 mt-2 max-w-xl">
                        Monitor and analyze every test cycle. Filter by project, platform or outcome to drill down into specific results.
                    </p>
                </div>

                {/* Stats Grid */}
                <div className="flex gap-4">
                    <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl p-4 px-8 transition-transform hover:scale-105">
                        <div className="text-3xl font-black text-white">{runs.length}</div>
                        <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mt-1">Total Runs</div>
                    </div>
                    <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl p-4 px-8 transition-transform hover:scale-105">
                        <div className="text-3xl font-black text-green-400">
                            {runs.length > 0 ? Math.round((runs.filter(r => r.status === 'completed').length / runs.length) * 100) : 0}%
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mt-1">Efficiency</div>
                    </div>
                </div>
            </div>

            {/* Filters Bar */}
            <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center gap-4">
                <div className="flex-1 min-w-[300px] relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search projects or endpoints..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl py-2.5 pl-11 pr-4 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                    />
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5">
                        <Filter className="h-3.5 w-3.5 text-slate-500" />
                        <select
                            value={filterProject}
                            onChange={(e) => setFilterProject(e.target.value)}
                            className="bg-transparent border-none text-xs text-slate-300 focus:ring-0 cursor-pointer outline-none"
                        >
                            <option value="all">All Projects</option>
                            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                        </select>
                    </div>

                    <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5">
                        <Globe className="h-3.5 w-3.5 text-slate-500" />
                        <select
                            value={filterPlatform}
                            onChange={(e) => setFilterPlatform(e.target.value)}
                            className="bg-transparent border-none text-xs text-slate-300 focus:ring-0 cursor-pointer outline-none"
                        >
                            <option value="all">All Platforms</option>
                            <option value="web">Web</option>
                            <option value="mobile_android">Android</option>
                            <option value="api">API</option>
                        </select>
                    </div>

                    <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5">
                        <Activity className="h-3.5 w-3.5 text-slate-500" />
                        <select
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value)}
                            className="bg-transparent border-none text-xs text-slate-300 focus:ring-0 cursor-pointer outline-none"
                        >
                            <option value="all">Any Status</option>
                            <option value="completed">Completed</option>
                            <option value="failed">Failed</option>
                            <option value="running">Running</option>
                        </select>
                    </div>

                    {(searchTerm || filterPlatform !== 'all' || filterStatus !== 'all' || filterProject !== 'all') && (
                        <button
                            onClick={() => { setSearchTerm(''); setFilterPlatform('all'); setFilterStatus('all'); setFilterProject('all'); }}
                            className="text-xs text-slate-500 hover:text-white transition-colors flex items-center gap-1 px-2"
                        >
                            <Trash2 className="h-3.5 w-3.5" /> Clear
                        </button>
                    )}
                </div>
            </div>

            {/* Main Table */}
            <div className="bg-slate-900/30 backdrop-blur-sm border border-slate-800/50 rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-slate-900/80 text-slate-400 uppercase text-[10px] font-bold tracking-widest border-b border-slate-800">
                            <tr>
                                <th className="px-6 py-4">Status & Run ID</th>
                                <th className="px-6 py-4">Project</th>
                                <th className="px-6 py-4">Target Endpoint</th>
                                <th className="px-6 py-4">Platform</th>
                                <th className="px-6 py-4">Executed</th>
                                <th className="px-6 py-4">Duration</th>
                                <th className="px-6 py-4 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                            {loading ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-20 text-center text-slate-500">
                                        <div className="flex flex-col items-center">
                                            <Activity className="h-10 w-10 animate-spin text-blue-500 mb-4" />
                                            <p className="font-medium animate-pulse">Syncing with server...</p>
                                        </div>
                                    </td>
                                </tr>
                            ) : filteredRuns.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-32 text-center">
                                        <div className="flex flex-col items-center max-w-sm mx-auto">
                                            <div className="h-20 w-20 bg-slate-900 rounded-3xl flex items-center justify-center mb-6 border border-slate-800">
                                                <Search className="h-10 w-10 text-slate-700" />
                                            </div>
                                            <h3 className="text-xl font-bold text-white mb-2">No matching runs</h3>
                                            <p className="text-slate-500 text-sm">
                                                We couldn't find any test runs matching your current filter criteria. Try adjusting your filters.
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                filteredRuns.map((run) => (
                                    <tr key={run.id} className="group hover:bg-slate-800/30 transition-all duration-300">
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-3">
                                                <div className={`h-8 px-2.5 rounded-lg flex items-center gap-2 border ${getStatusColor(run.status)}`}>
                                                    {getStatusIcon(run.status)}
                                                    <span className="text-[10px] font-bold uppercase tracking-wider">{run.status}</span>
                                                </div>
                                                <span className="text-[10px] font-mono text-slate-600 group-hover:text-slate-400 transition-colors">#{run.id}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-2">
                                                <div className="h-6 w-6 rounded bg-slate-800 flex items-center justify-center text-[10px] font-bold text-blue-400">
                                                    {run.project_name.charAt(0)}
                                                </div>
                                                <span className="font-bold text-slate-200 group-hover:text-white transition-colors">{run.project_name}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <code className="text-[11px] text-slate-400 max-w-[200px] truncate block group-hover:text-blue-400 transition-colors" title={run.target}>
                                                {run.target}
                                            </code>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-2 text-slate-400">
                                                <Globe className="h-3.5 w-3.5" />
                                                <span className="text-xs capitalize">{run.platform.replace('_', ' ')}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-2 text-slate-400">
                                                <Calendar className="h-3.5 w-3.5" />
                                                <span className="text-xs">
                                                    {run.started_at
                                                        ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true, locale: tr })
                                                        : '-'}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-2 text-slate-400">
                                                <Clock className="h-3.5 w-3.5" />
                                                <span className="text-xs font-mono">
                                                    {run.completed_at && run.started_at
                                                        ? `${((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000).toFixed(1)}s`
                                                        : (run.status === 'running' ? 'Active' : '-')}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5 text-right">
                                            <button
                                                onClick={() => setSelectedRun(run)}
                                                disabled={!run.logs}
                                                className="h-9 px-4 rounded-xl bg-slate-800 hover:bg-blue-600 text-white font-bold text-xs transition-all flex items-center gap-2 ml-auto group/btn disabled:opacity-20 disabled:cursor-not-allowed"
                                            >
                                                Details
                                                <ChevronRight className="h-3 w-3 group-hover/btn:translate-x-1 transition-transform" />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default TestRunsPage;
