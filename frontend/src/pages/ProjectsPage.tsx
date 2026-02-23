import React from 'react';
import { Layers, Plus, ExternalLink, Calendar, Loader2, Trash2, AlertTriangle } from "lucide-react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api, Project } from "@/services/api"
import { Link } from "react-router-dom"

// ─── Confirm Delete Modal ────────────────────────────────────────────
interface ConfirmDeleteProps {
    project: Project;
    onConfirm: () => void;
    onCancel: () => void;
    isLoading: boolean;
}

function ConfirmDeleteModal({ project, onConfirm, onCancel, isLoading }: ConfirmDeleteProps) {
    return (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-md p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-red-500/15 rounded-lg">
                        <AlertTriangle className="h-5 w-5 text-red-400" />
                    </div>
                    <h2 className="text-lg font-bold text-white">Projeyi Sil</h2>
                </div>
                <p className="text-slate-400 text-sm mb-2">
                    Bu işlem geri alınamaz. Aşağıdaki proje ve bağlı tüm test case'ler silinecektir:
                </p>
                <div className="bg-slate-800 rounded-lg px-4 py-3 mb-6 border border-slate-700">
                    <p className="text-white font-semibold">{project.name}</p>
                    {project.description && (
                        <p className="text-slate-400 text-xs mt-1">{project.description}</p>
                    )}
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={onCancel}
                        disabled={isLoading}
                        className="flex-1 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium transition-colors text-sm border border-slate-700"
                    >
                        İptal
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={isLoading}
                        className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-60"
                    >
                        {isLoading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Trash2 className="h-4 w-4" />
                        )}
                        Evet, Sil
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── Project Card ────────────────────────────────────────────────────
interface ProjectCardProps {
    project: Project;
    onDeleteClick: (project: Project) => void;
}

function ProjectCard({ project, onDeleteClick }: ProjectCardProps) {
    return (
        <Link
            to={`/projects/${project.id}/pages`}
            className="bg-slate-900 border border-slate-800 rounded-3xl p-6 hover:border-blue-500/50 hover:bg-slate-800/40 transition-all duration-300 group flex flex-col relative overflow-hidden shadow-xl"
        >
            {/* Background Glow Effect */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600/5 rounded-full blur-[50px] -mr-16 -mt-16 group-hover:bg-blue-600/10 transition-all duration-500" />

            <div className="flex justify-between items-start mb-5 relative z-10">
                <div className="h-12 w-12 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-center group-hover:border-blue-500/30 group-hover:bg-blue-500/5 transition-all duration-300 shadow-inner">
                    <Layers className="h-6 w-6 text-slate-500 group-hover:text-blue-400 transition-colors" />
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[9px] font-black text-slate-600 uppercase tracking-widest bg-black/40 px-2 py-1 rounded-lg border border-white/5">
                        #{project.id}
                    </span>
                    <button
                        onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onDeleteClick(project);
                        }}
                        className="h-8 w-8 flex items-center justify-center rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-400/10 border border-transparent hover:border-red-400/20 transition-all opacity-0 group-hover:opacity-100"
                        title="Projeyi Sil"
                    >
                        <Trash2 className="h-4 w-4" />
                    </button>
                </div>
            </div>

            <div className="relative z-10 flex-1">
                <h3 className="text-xl font-bold text-white mb-2 group-hover:text-blue-300 transition-colors tracking-tight">
                    {project.name}
                </h3>

                <p className="text-slate-500 mb-6 line-clamp-2 leading-relaxed font-medium text-xs">
                    {project.description || "Otonom VisionAI tarafından yönetilen test mimarisi."}
                </p>

                {/* Platform Badges */}
                <div className="flex flex-wrap gap-2 mb-6">
                    {project.platforms?.map(p => (
                        <span key={p} className="text-[8px] font-black uppercase tracking-wider px-2 py-1 rounded-md bg-blue-500/5 text-blue-400 border border-blue-500/10 shadow-sm">
                            {p}
                        </span>
                    ))}
                </div>
            </div>

            <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-slate-600 border-t border-white/5 pt-5 mt-auto relative z-10">
                <span className="flex items-center">
                    <Calendar className="h-3 w-3 mr-2 text-slate-700" />
                    {new Date(project.created_at).toLocaleDateString('tr-TR')}
                </span>
                <span className="flex items-center text-blue-500 group-hover:translate-x-1 transition-transform duration-300">
                    OPEN MODULES <ExternalLink className="ml-2 h-3 w-3" />
                </span>
            </div>
        </Link>
    );
}

// ─── Ana Sayfa ────────────────────────────────────────────────────────
export function ProjectsPage() {
    const queryClient = useQueryClient();
    const [confirmProject, setConfirmProject] = React.useState<Project | null>(null);

    const { data: projects, isLoading, isError } = useQuery({
        queryKey: ['projects'],
        queryFn: api.getProjects
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => api.deleteProject(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['projects'] });
            // localStorage'daki summary'yi de temizle
            if (confirmProject) {
                try { localStorage.removeItem(`visionqa_summary_project_${confirmProject.id}`); } catch { }
            }
            setConfirmProject(null);
        },
        onError: (error: any) => {
            alert('Silme hatası: ' + (error?.response?.data?.detail || error.message));
            setConfirmProject(null);
        }
    });

    if (isLoading) {
        return (
            <div className="flex h-[400px] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                <span className="ml-3 text-slate-400">Loading projects...</span>
            </div>
        );
    }

    if (isError) {
        return (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg">
                Failed to load projects. Is the backend running?
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Confirm Delete Modal */}
            {confirmProject && (
                <ConfirmDeleteModal
                    project={confirmProject}
                    onConfirm={() => deleteMutation.mutate(confirmProject.id)}
                    onCancel={() => setConfirmProject(null)}
                    isLoading={deleteMutation.isPending}
                />
            )}

            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <div className="h-14 w-14 bg-blue-600 rounded-2xl flex items-center justify-center shadow-xl shadow-blue-900/20">
                        <Layers className="h-7 w-7 text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight text-white mb-0.5">Projects</h1>
                        <p className="text-slate-400 text-sm">
                            Manage your test suites and application targets.
                        </p>
                    </div>
                </div>
                <Link
                    to="/projects/new"
                    className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl flex items-center shadow-lg shadow-blue-900/10 font-bold transition-all active:scale-95 group text-sm"
                >
                    <Plus className="mr-2 h-4 w-4 group-hover:rotate-90 transition-transform duration-300" /> New Project
                </Link>
            </div>

            {/* Project Grid */}
            {projects && projects.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project) => (
                        <ProjectCard
                            key={project.id}
                            project={project}
                            onDeleteClick={setConfirmProject}
                        />
                    ))}
                </div>
            ) : (
                <div className="flex flex-col items-center justify-center min-h-[400px] border-2 border-dashed border-slate-800 rounded-3xl bg-slate-900/10 group">
                    <div className="bg-slate-900/50 p-6 rounded-full mb-6 border border-white/5">
                        <Layers className="h-10 w-10 text-slate-700" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">No projects found</h3>
                    <p className="text-slate-500 text-center max-w-sm mb-8 text-sm leading-relaxed">
                        Deploy your first automated test environment to start analyzing your application stack.
                    </p>
                    <Link
                        to="/projects/new"
                        className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-bold transition-all shadow-xl shadow-blue-900/20 active:scale-95 text-sm"
                    >
                        Initiate Project
                    </Link>
                </div>
            )}
        </div>
    );
}
