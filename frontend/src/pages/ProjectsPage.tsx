
import { Layers, Plus } from "lucide-react"

export function ProjectsPage() {
    return (
        <div className="space-y-6">

            {/* 🟢 Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight text-white mb-1">Projects</h1>
                    <p className="text-muted-foreground text-slate-400">
                        Manage your test suites and application targets.
                    </p>
                </div>
                <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center shadow-lg shadow-blue-900/20 font-medium transition-all">
                    <Plus className="mr-2 h-4 w-4" /> New Project
                </button>
            </div>

            {/* 🔵 Empty State (Şimdilik) */}
            <div className="flex flex-col items-center justify-center min-h-[400px] border-2 border-dashed border-slate-800 rounded-lg bg-slate-900/50">
                <div className="bg-slate-800 p-4 rounded-full mb-4">
                    <Layers className="h-8 w-8 text-slate-400" />
                </div>
                <h3 className="text-lg font-medium text-white mb-1">No projects found</h3>
                <p className="text-slate-400 text-center max-w-sm mb-6">
                    Get started by creating a new project to run automated tests.
                </p>
                <button className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-md transition-colors border border-slate-700">
                    Create Project
                </button>
            </div>
        </div>
    )
}
