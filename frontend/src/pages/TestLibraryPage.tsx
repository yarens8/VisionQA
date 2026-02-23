
import React, { useEffect, useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, TestCase } from '../services/api';
import {
    Trash2, Play, Sparkles, X, Shield,
    AlertCircle, CheckCircle, Zap, ChevronDown,
    ChevronUp, Loader2, ArrowLeft,
    Layers, Command
} from 'lucide-react';

// ─── TYPES ──────────────────────────────────────────────────────────
interface StepResult {
    order: number;
    action: string;
    action_label: string;
    target: string;
    value?: string;
    status: 'passed' | 'failed' | 'pending';
    reason: string;
    error?: string;
    screenshot?: string;
}

interface ExecutionResult {
    status: 'completed' | 'failed' | 'crashed';
    steps: StepResult[];
    summary?: string;
    error?: string;
}

const CATEGORY_CONFIG: Record<string, { label: string; bg: string; text: string; icon: any }> = {
    happy_path: { label: 'Happy Path', bg: 'bg-emerald-500/10', text: 'text-emerald-400', icon: CheckCircle },
    negative_path: { label: 'Negative', bg: 'bg-rose-500/10', text: 'text-rose-400', icon: AlertCircle },
    edge_case: { label: 'Edge Case', bg: 'bg-amber-500/10', text: 'text-amber-400', icon: Zap },
    security: { label: 'Security', bg: 'bg-violet-500/10', text: 'text-violet-400', icon: Shield },
};

// ─── COMPONENTS ─────────────────────────────────────────────────────

const TestResultModal: React.FC<{ result: ExecutionResult; onClose: () => void }> = ({ result, onClose }) => {
    const [activeStep, setActiveStep] = useState(0);
    const passed = result.steps.filter(s => s.status === 'passed').length;
    const total = result.steps.length;

    return (
        <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-md z-[100] flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl w-full max-w-5xl max-h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="flex items-center justify-between px-8 py-6 border-b border-slate-800">
                    <div>
                        <h2 className="text-lg font-bold text-white tracking-tight">Intelligence Report</h2>
                        <p className="text-xs font-black text-indigo-400 uppercase tracking-widest mt-0.5">{passed}/{total} Steps Secured</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-800 text-slate-400 rounded-xl transition-all active:scale-95"><X className="h-5 w-5" /></button>
                </div>

                <div className="flex flex-1 overflow-hidden">
                    <div className="w-72 border-r border-slate-800 bg-slate-900/50 overflow-y-auto p-4 space-y-2">
                        {result.steps.map((step, i) => (
                            <button key={i} onClick={() => setActiveStep(i)} className={`w-full text-left p-3 rounded-xl transition-all flex items-center gap-3 ${activeStep === i ? 'bg-indigo-600 text-white shadow-lg' : 'hover:bg-slate-800 text-slate-500'}`}>
                                <span className={`h-6 w-6 rounded-lg flex items-center justify-center text-[9px] font-black border ${activeStep === i ? 'border-white/20' : 'border-slate-800'}`}>{step.order}</span>
                                <span className="text-xs font-bold truncate flex-1">{step.action.toUpperCase()}</span>
                                {step.status === 'passed' ? <CheckCircle className="h-3.5 w-3.5 text-emerald-500" /> : <AlertCircle className="h-3.5 w-3.5 text-rose-500" />}
                            </button>
                        ))}
                    </div>
                    <div className="flex-1 overflow-y-auto bg-slate-950 p-8 space-y-8">
                        {/* Final AI Summary Analysis */}
                        {result.summary && (
                            <div className="max-w-3xl mx-auto bg-indigo-600/5 border border-indigo-500/20 p-6 rounded-2xl relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                                    <Sparkles className="h-16 w-16 text-indigo-400" />
                                </div>
                                <div className="flex items-center gap-2 mb-3">
                                    <Zap className="h-4 w-4 text-indigo-500 fill-current" />
                                    <h3 className="text-xs font-black text-indigo-400 uppercase tracking-widest">Executive AI Summary</h3>
                                </div>
                                <p className="text-slate-200 text-sm leading-relaxed font-medium italic relative z-10">
                                    "{result.summary}"
                                </p>
                            </div>
                        )}

                        {result.steps[activeStep] && (
                            <div className="max-w-3xl mx-auto space-y-6">
                                <div className="flex items-center justify-between border-b border-white/5 pb-4">
                                    <div>
                                        <h3 className="text-xl font-black text-white">{result.steps[activeStep].action.toUpperCase()}</h3>
                                        <p className="text-slate-500 text-xs font-mono mt-1">{result.steps[activeStep].target}</p>
                                    </div>
                                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase ${result.steps[activeStep].status === 'passed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>{result.steps[activeStep].status}</span>
                                </div>
                                <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
                                    <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-2">AI Vision Analysis</p>
                                    <p className="text-white text-sm font-medium leading-relaxed">"{result.steps[activeStep].reason}"</p>
                                </div>
                                {result.steps[activeStep].screenshot && (
                                    <div className="rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
                                        <img src={result.steps[activeStep].screenshot} className="w-full h-auto" />
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

const TestCaseCard: React.FC<{
    testCase: TestCase;
    onRun: (id: number) => void;
    onDelete: (id: number) => void;
    running: boolean
}> = ({ testCase, onRun, onDelete, running }) => {
    const [expanded, setExpanded] = useState(false);
    const cat = CATEGORY_CONFIG[testCase.category || 'happy_path'] || CATEGORY_CONFIG.happy_path;
    const Icon = cat.icon;

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 mb-3 hover:border-indigo-500/30 transition-all group relative overflow-hidden">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                        <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full ${cat.bg} ${cat.text} text-[9px] font-black uppercase border border-current opacity-60`}>
                            <Icon className="h-2.5 w-2.5" />
                            {cat.label}
                        </span>
                        <span className="text-[9px] font-bold text-slate-600 uppercase tracking-tight">#{testCase.id}</span>
                    </div>
                    <h3 className="text-base font-bold text-white group-hover:text-indigo-400 transition-colors tracking-tight">{testCase.title}</h3>
                    <p className="text-xs text-slate-500 mt-0.5 line-clamp-1 truncate">{testCase.description}</p>
                    <button onClick={() => setExpanded(!expanded)} className="mt-3 flex items-center gap-2 text-[10px] font-black text-slate-600 hover:text-indigo-500 transition-colors uppercase tracking-widest">
                        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        {testCase.steps.length} Protocol Steps
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={() => onRun(testCase.id)} disabled={running} className={`h-10 px-6 rounded-xl flex items-center gap-2 font-black text-[11px] uppercase tracking-widest transition-all active:scale-95 ${running ? 'bg-slate-800 text-amber-500 cursor-wait' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-950/20'}`}>
                        {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-3.5 w-3.5 fill-current" />}
                        {running ? 'Loading' : 'Deploy'}
                    </button>
                    <button onClick={() => onDelete(testCase.id)} className="h-10 w-10 bg-slate-950 hover:bg-rose-500/10 text-slate-800 hover:text-rose-500 rounded-xl border border-slate-800 hover:border-rose-500/30 transition-all flex items-center justify-center">
                        <Trash2 className="h-4 w-4" />
                    </button>
                </div>
            </div>
            {expanded && (
                <div className="mt-4 pt-4 border-t border-slate-800/50 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                    {testCase.steps.map((s, i) => (
                        <div key={i} className="flex items-center gap-3 p-3 bg-slate-950/50 rounded-xl border border-slate-800/50 text-xs">
                            <span className="h-5 w-5 bg-slate-900 text-indigo-500 rounded flex items-center justify-center text-[9px] font-black border border-slate-800">{s.order}</span>
                            <div className="min-w-0">
                                <p className="text-[8px] font-black text-slate-600 uppercase mb-0.5">{s.action}</p>
                                <p className="text-slate-400 font-medium truncate">{s.target}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

// ─── MAIN PAGE ───────────────────────────────────────────────────────

export function TestLibraryPage() {
    const { projectId, pageId } = useParams();
    const [searchParams] = useSearchParams();
    const queryClient = useQueryClient();
    const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
    const [runningCaseId, setRunningCaseId] = useState<number | null>(null);
    const [isGenerating, setIsGenerating] = useState(false);

    const { data: cases, isLoading: isLoadingCases } = useQuery({
        queryKey: ['cases', projectId, pageId],
        queryFn: () => api.getCases(Number(projectId), Number(pageId)),
        enabled: !!pageId
    });

    const { data: projects } = useQuery({
        queryKey: ['projects'],
        queryFn: () => api.getProjects()
    });

    const currentProject = projects?.find(p => p.id === Number(projectId));
    const currentPage = currentProject?.pages?.find(p => p.id === Number(pageId));

    const generateMutation = useMutation({
        mutationFn: () => api.generateCasesForPage(Number(pageId)),
        onMutate: () => setIsGenerating(true),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['cases', projectId, pageId] });
            setIsGenerating(false);
        },
        onError: () => setIsGenerating(false)
    });

    useEffect(() => {
        if (searchParams.get('generate') === 'true' && !isGenerating && Array.isArray(cases) && cases.length === 0) {
            generateMutation.mutate();
        }
    }, [searchParams, cases, isGenerating, generateMutation]);

    const runMutation = useMutation({
        mutationFn: (id: number) => api.runTestCase(id),
        onMutate: (id) => setRunningCaseId(id),
        onSuccess: (res) => {
            setRunningCaseId(null);
            setExecutionResult(res as ExecutionResult);
        }
    });

    return (
        <div className="min-h-screen bg-slate-950 text-slate-300 p-8 pt-6 space-y-8">
            {executionResult && <TestResultModal result={executionResult} onClose={() => setExecutionResult(null)} />}

            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-end gap-6">
                <div className="space-y-4">
                    <Link to={`/projects/${projectId}/pages`} className="group inline-flex items-center text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 hover:text-white transition-all">
                        <ArrowLeft className="h-3.5 w-3.5 mr-2 group-hover:-translate-x-1 transition-transform" /> Back
                    </Link>
                    <div className="flex items-center gap-5">
                        <div className="h-14 w-14 bg-slate-900 rounded-2xl border border-slate-800 flex items-center justify-center shadow-xl">
                            <Sparkles className="h-7 w-7 text-indigo-500" />
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-indigo-500/60 uppercase tracking-widest mb-1">{currentPage?.url}</p>
                            <h1 className="text-3xl font-black text-white tracking-tight leading-none">{currentPage?.name || 'Protocol'}</h1>
                        </div>
                    </div>
                </div>

                <button
                    onClick={() => generateMutation.mutate()}
                    disabled={isGenerating}
                    className={`h-12 px-8 rounded-xl flex items-center gap-3 transition-all active:scale-95 disabled:opacity-30 bg-indigo-600 text-white shadow-xl shadow-indigo-900/20 font-black text-xs uppercase tracking-widest hover:bg-indigo-500`}
                >
                    {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Command className="h-4 w-4" />}
                    {isGenerating ? 'AI Syncing...' : 'Generate Protocols'}
                </button>
            </div>

            {/* List */}
            <div className="relative">
                {isLoadingCases ? (
                    <div className="flex flex-col items-center justify-center h-64 bg-slate-900/30 rounded-3xl border border-slate-800">
                        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
                    </div>
                ) : cases && cases.length > 0 ? (
                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                        {cases.map(c => (
                            <TestCaseCard
                                key={c.id}
                                testCase={c}
                                onRun={(id) => runMutation.mutate(id)}
                                onDelete={(id) => api.deleteTestCase(id).then(() => queryClient.invalidateQueries({ queryKey: ['cases'] }))}
                                running={runningCaseId === c.id}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center p-20 bg-slate-900/10 rounded-[2.5rem] border-2 border-dashed border-slate-800/50 text-center">
                        <div className="p-5 bg-slate-900 rounded-full mb-6 border border-slate-800">
                            <Layers className="h-8 w-8 text-slate-700" />
                        </div>
                        <h2 className="text-xl font-bold text-slate-400 uppercase tracking-tighter">Station Offline</h2>
                        <p className="text-xs text-slate-600 mt-2 max-w-xs mx-auto font-medium">Click Generate Protocols to initialize the AI analysis for this target.</p>
                        <button onClick={() => generateMutation.mutate()} className="mt-8 text-[10px] font-black text-indigo-500 hover:text-indigo-400 uppercase tracking-widest">Initialize Startup</button>
                    </div>
                )}
            </div>
        </div>
    );
}

export default TestLibraryPage;
