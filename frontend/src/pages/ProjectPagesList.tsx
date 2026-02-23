import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import {
    Layout,
    Link as LinkIcon,
    Plus,
    ArrowLeft,
    ChevronRight,
    Zap,
    Trash2,
    Globe,
    Loader2,
    CheckCircle2,
    Activity,
    Target
} from 'lucide-react';

export function ProjectPagesList() {
    const { projectId } = useParams();
    const queryClient = useQueryClient();
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [newPage, setNewPage] = useState({ name: '', url: '', description: '' });

    // ─── Veri Çekme ───────────────────────────────────────────
    const { data: pages, isLoading: isPagesLoading } = useQuery({
        queryKey: ['pages', projectId],
        queryFn: () => api.getPages(Number(projectId))
    });

    const { data: stats, isLoading: isStatsLoading } = useQuery({
        queryKey: ['projectStats', projectId],
        queryFn: () => api.getProjectStats(Number(projectId)),
        refetchInterval: 10000 // 10 saniyede bir güncelle
    });

    // ─── Yeni Sayfa Ekleme ──────────────────────────────────────
    const addMutation = useMutation({
        mutationFn: (data: any) => api.addPage(Number(projectId), data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['pages', projectId] });
            queryClient.invalidateQueries({ queryKey: ['projectStats', projectId] }); // Invalidate stats as well
            setIsAddModalOpen(false);
            setNewPage({ name: '', url: '', description: '' });
        }
    });

    // ─── Sayfa Silme ───────────────────────────────────────────
    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.deletePage(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['pages', projectId] });
            queryClient.invalidateQueries({ queryKey: ['projectStats', projectId] }); // Invalidate stats as well
        }
    });

    const isLoading = isPagesLoading || isStatsLoading;

    if (isLoading) return (
        <div className="flex flex-col items-center justify-center min-h-[400px]">
            <Loader2 className="h-12 w-12 animate-spin text-blue-500 mb-4" />
            <p className="text-slate-500 font-medium animate-pulse text-lg">Analyzing Project Architecture...</p>
        </div>
    );

    return (
        <div className="space-y-8 animate-in fade-in duration-700">
            {/* Context Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-4 flex-1">
                    <Link to="/projects" className="text-slate-500 hover:text-white flex items-center text-xs font-bold uppercase tracking-widest transition-colors group">
                        <ArrowLeft className="h-3.5 w-3.5 mr-2 group-hover:-translate-x-1 transition-transform" /> Back to Workspace
                    </Link>

                    <div className="flex items-center gap-4">
                        <div className="h-16 w-16 bg-blue-600 rounded-3xl flex items-center justify-center shadow-lg shadow-blue-900/40">
                            <Globe className="h-8 w-8 text-white" />
                        </div>
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <span className="bg-blue-500/10 text-blue-400 text-[10px] font-black uppercase px-2 py-0.5 rounded-full border border-blue-500/20 tracking-tighter">
                                    Active Project
                                </span>
                            </div>
                            <h1 className="text-4xl font-black text-white tracking-tight">
                                {stats?.project_name} <span className="text-slate-700 font-light mx-2">|</span> <span className="text-slate-500 underline decoration-blue-500/30">Modules</span>
                            </h1>
                        </div>
                    </div>
                </div>

                <button
                    onClick={() => setIsAddModalOpen(true)}
                    className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-4 rounded-2xl flex items-center shadow-[0_10px_30px_rgba(37,99,235,0.4)] font-black transition-all active:scale-95 group"
                >
                    <Plus className="mr-2 h-5 w-5 group-hover:rotate-90 transition-transform" /> Add New Module
                </button>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute right-0 top-0 p-4 opacity-5 bg-gradient-to-br from-blue-500 to-transparent rounded-full h-24 w-24 -mr-12 -mt-12 transition-all group-hover:scale-150" />
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                        <Target className="h-3 w-3" /> Total Test Cases
                    </p>
                    <p className="text-3xl font-black text-white">{stats?.total_cases || 0}</p>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute right-0 top-0 p-4 opacity-5 bg-gradient-to-br from-green-500 to-transparent rounded-full h-24 w-24 -mr-12 -mt-12 transition-all group-hover:scale-150" />
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                        <CheckCircle2 className="h-3 w-3" /> Success Rate
                    </p>
                    <p className="text-3xl font-black text-green-400">{stats?.success_rate || 0}%</p>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 relative overflow-hidden group">
                    <div className="absolute right-0 top-0 p-4 opacity-5 bg-gradient-to-br from-purple-500 to-transparent rounded-full h-24 w-24 -mr-12 -mt-12 transition-all group-hover:scale-150" />
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1 flex items-center gap-1.5">
                        <Activity className="h-3 w-3" /> Execution Count
                    </p>
                    <p className="text-3xl font-black text-white">{stats?.total_runs || 0}</p>
                </div>

                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 flex flex-col justify-center">
                    <div className="flex -space-x-2">
                        {[1, 2, 3].map(i => (
                            <div key={i} className={`h-8 w-8 rounded-full border-2 border-slate-900 bg-slate-800 flex items-center justify-center text-[8px] font-bold transition-transform hover:-translate-y-1 cursor-help ${i === 1 ? 'text-green-400' : 'text-blue-400'}`}>
                                {i === 1 ? 'AI' : i === 2 ? 'WEB' : 'UX'}
                            </div>
                        ))}
                    </div>
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mt-2">Active Frameworks</p>
                </div>
            </div>

            {/* Modules Section */}
            <div>
                <div className="flex items-center gap-3 mb-6">
                    <h2 className="text-xl font-black text-white px-4 py-1.5 bg-slate-900 rounded-lg border border-slate-800">Available Modules</h2>
                    <div className="h-px bg-slate-800 flex-1" />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {pages && pages.length > 0 ? (
                        pages.map((page) => (
                            <div
                                key={page.id}
                                className="bg-slate-900/40 backdrop-blur-md border border-slate-800 p-8 rounded-[2rem] group hover:border-blue-500/50 hover:bg-slate-900/60 transition-all duration-500 relative overflow-hidden"
                            >
                                <div className="absolute top-0 right-0 p-6 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button
                                        onClick={() => deleteMutation.mutate(page.id)}
                                        className="h-10 w-10 flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-400/10 rounded-full transition-all"
                                    >
                                        <Trash2 className="h-5 w-5" />
                                    </button>
                                </div>

                                <div className="flex items-start gap-6">
                                    <div className="h-16 w-16 bg-slate-950 rounded-2xl border border-slate-800 flex items-center justify-center group-hover:border-blue-500/30 group-hover:bg-blue-500/5 transition-all">
                                        <Layout className="h-8 w-8 text-slate-500 group-hover:text-blue-400 transition-colors" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-2xl font-black text-white mb-2 group-hover:text-blue-300 transition-colors truncate">{page.name}</h3>
                                        <div className="flex items-center bg-black/40 px-3 py-1.5 rounded-lg border border-white/5 w-fit">
                                            <LinkIcon className="h-3 w-3 mr-2 text-blue-500" />
                                            <span className="text-[11px] font-mono text-slate-400 truncate max-w-[200px]" title={page.url}>
                                                {page.url}
                                            </span>
                                        </div>
                                        <p className="text-slate-500 text-sm mt-4 leading-relaxed line-clamp-2">
                                            {page.description || "Otonom AI tarafından analiz edilecek ve test senaryoları türetilecek hedef modül."}
                                        </p>
                                    </div>
                                </div>

                                <div className="mt-8 pt-8 border-t border-white/5 flex gap-4">
                                    <Link
                                        to={`/projects/${projectId}/pages/${page.id}/tests`}
                                        className="flex-1 bg-slate-800/80 hover:bg-slate-700 text-white px-5 py-4 rounded-2xl flex items-center justify-center font-black text-xs transition-all border border-slate-700 hover:border-slate-500"
                                    >
                                        Inspect Suite <ChevronRight className="ml-2 h-4 w-4" />
                                    </Link>
                                    <Link
                                        to={`/projects/${projectId}/pages/${page.id}/tests?generate=true`}
                                        className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:scale-[1.02] text-white px-5 py-4 rounded-2xl flex items-center justify-center font-black text-xs shadow-lg shadow-blue-900/40 transition-all active:scale-95"
                                    >
                                        <Zap className="mr-2 h-4 w-4 fill-current text-yellow-300" /> AI Generation
                                    </Link>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="lg:col-span-2 py-32 flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-[3rem] bg-slate-900/20">
                            <div className="h-24 w-24 bg-slate-900/50 rounded-full flex items-center justify-center mb-8 border border-white/5">
                                <Plus className="h-10 w-10 text-slate-600" />
                            </div>
                            <h2 className="text-3xl font-black text-white mb-3">Your project is empty</h2>
                            <p className="text-slate-500 text-center max-w-sm mb-10 leading-relaxed font-medium">
                                Start by adding specific URLs (e.g. /login, /shop) to analyze and generate automated test scenarios.
                            </p>
                            <button
                                onClick={() => setIsAddModalOpen(true)}
                                className="bg-white text-black px-8 py-4 rounded-2xl font-black hover:bg-blue-400 hover:text-white transition-all shadow-2xl"
                            >
                                Get Started Now
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Add Page Modal */}
            {isAddModalOpen && (
                <div className="fixed inset-0 bg-slate-950/90 backdrop-blur-xl z-50 flex items-center justify-center p-4">
                    <div className="bg-slate-900 border border-slate-800 rounded-[3rem] shadow-2xl w-full max-w-lg p-10 animate-in zoom-in-90 duration-300">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="h-2 w-2 rounded-full bg-blue-500 animate-ping" />
                            <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest">Architectural Input</span>
                        </div>
                        <h2 className="text-4xl font-black text-white mb-2">New Module</h2>
                        <p className="text-slate-500 mb-10 font-medium">Add a path to your web application for AI scanning.</p>

                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-xs font-black uppercase tracking-widest text-slate-600 ml-1">Friendly Name</label>
                                <input
                                    type="text"
                                    placeholder="e.g. User Authentication"
                                    value={newPage.name}
                                    onChange={(e) => setNewPage({ ...newPage, name: e.target.value })}
                                    className="w-full bg-slate-950 border border-slate-800/50 rounded-2xl px-6 py-5 text-white focus:border-blue-500 outline-none transition-all placeholder:text-slate-700 font-bold"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-black uppercase tracking-widest text-slate-600 ml-1">Path / URL</label>
                                <input
                                    type="text"
                                    placeholder="https://app.example.com/login"
                                    value={newPage.url}
                                    onChange={(e) => setNewPage({ ...newPage, url: e.target.value })}
                                    className="w-full bg-slate-950 border border-slate-800/50 rounded-2xl px-6 py-5 text-white focus:border-blue-500 outline-none transition-all placeholder:text-slate-700 font-bold"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-black uppercase tracking-widest text-slate-600 ml-1">Objective</label>
                                <textarea
                                    placeholder="What should AI focus on testing?"
                                    value={newPage.description}
                                    onChange={(e) => setNewPage({ ...newPage, description: e.target.value })}
                                    className="w-full bg-slate-950 border border-slate-800/50 rounded-2xl px-6 py-5 text-white focus:border-blue-500 outline-none transition-all h-32 placeholder:text-slate-700 font-bold resize-none"
                                ></textarea>
                            </div>

                            <div className="flex gap-4 pt-6">
                                <button
                                    onClick={() => setIsAddModalOpen(false)}
                                    className="flex-1 px-4 py-5 bg-slate-800/50 hover:bg-slate-800 text-slate-400 font-black rounded-2xl transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={() => addMutation.mutate(newPage)}
                                    disabled={!newPage.name || !newPage.url || addMutation.isPending}
                                    className="flex-1 px-4 py-5 bg-blue-600 hover:bg-blue-500 text-white font-black rounded-2xl shadow-xl shadow-blue-900/30 disabled:opacity-50 transition-all flex items-center justify-center active:scale-95"
                                >
                                    {addMutation.isPending ? <Loader2 className="h-6 w-6 animate-spin" /> : "Initiate Module"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default ProjectPagesList;
