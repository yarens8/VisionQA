import { Layers, Plus, ExternalLink, Calendar, Loader2 } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { api, Project } from "@/services/api"
import { Link } from "react-router-dom"

export function ProjectsPage() {
    // 🔄 Veri Çekme (React Query Gücü!)
    const { data: projects, isLoading, isError } = useQuery({
        queryKey: ['projects'],
        queryFn: api.getProjects
    })

    // 🌀 Loading State
    if (isLoading) {
        return (
            <div className="flex h-[400px] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                <span className="ml-3 text-slate-400">Loading projects...</span>
            </div>
        )
    }

    // ❌ Error State
    if (isError) {
        return (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg">
                Failed to load projects. Is the backend running?
            </div>
        )
    }

    return (
        <div className="space-y-6">

            {/* 🟢 Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-white mb-1">Projects</h1>
                    <p className="text-sm text-slate-400">
                        Manage your test suites and application targets.
                    </p>
                </div>
                <Link to="/projects/new" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center shadow-lg shadow-blue-900/20 font-medium transition-all">
                    <Plus className="mr-2 h-4 w-4" /> New Project
                </Link>
            </div>

            {/* 🔵 Project Grid */}
            {projects && projects.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project) => (
                        <ProjectCard key={project.id} project={project} />
                    ))}
                </div>
            ) : (
                // Empty State
                <div className="flex flex-col items-center justify-center min-h-[400px] border-2 border-dashed border-slate-800 rounded-lg bg-slate-900/50">
                    <div className="bg-slate-800 p-4 rounded-full mb-4">
                        <Layers className="h-8 w-8 text-slate-400" />
                    </div>
                    <h3 className="text-lg font-medium text-white mb-1">No projects found</h3>
                    <p className="text-slate-400 text-center max-w-sm mb-6">
                        Get started by creating a new project to run automated tests.
                    </p>
                    <Link to="/projects/new" className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-md transition-colors border border-slate-700">
                        Create Project
                    </Link>
                </div>
            )}
        </div>
    )
}

// 📦 Küçük bir Kart Bileşeni (Aynı dosyada tutabiliriz şimdilik)
function ProjectCard({ project }: { project: Project }) {
    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors group">
            <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                    <Layers className="h-6 w-6 text-blue-500" />
                </div>
                <span className="text-xs text-slate-500 flex items-center bg-slate-800 px-2 py-1 rounded">
                    ID: #{project.id}
                </span>
            </div>

            <h3 className="text-lg font-semibold text-white mb-1 group-hover:text-blue-400 transition-colors">
                {project.name}
            </h3>

            <p className="text-sm text-slate-500 mb-4 line-clamp-2 h-10">
                {project.description || "No description provided."}
            </p>

            {/* Platform Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
                {project.platforms?.map(p => (
                    <span key={p} className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {p}
                    </span>
                ))}
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 border-t border-slate-800 pt-4 mt-auto">
                <span className="flex items-center">
                    <Calendar className="h-3 w-3 mr-1" />
                    {new Date(project.created_at).toLocaleDateString()}
                </span>
                <button className="text-blue-400 hover:text-blue-300 flex items-center font-medium">
                    View Details <ExternalLink className="ml-1 h-3 w-3" />
                </button>
            </div>
        </div>
    )
}
