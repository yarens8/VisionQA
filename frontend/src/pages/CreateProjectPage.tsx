import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api, ProjectCreate } from "@/services/api"
import { ArrowLeft, Save, Loader2, Monitor, Smartphone, Globe, Database, Terminal } from "lucide-react"
import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"

const PLATFORMS = [
    { id: "WEB", name: "Web Application", icon: Globe },
    { id: "MOBILE_ANDROID", name: "Android App", icon: Smartphone },
    { id: "MOBILE_IOS", name: "iOS App", icon: Smartphone },
    { id: "API", name: "REST API", icon: Terminal },
    { id: "DATABASE", name: "Database", icon: Database },
    { id: "DESKTOP", name: "Desktop App", icon: Monitor },
]

export function CreateProjectPage() {
    const navigate = useNavigate()
    const queryClient = useQueryClient()

    const [formData, setFormData] = useState<ProjectCreate>({
        name: "",
        description: "",
        platforms: []
    })

    // 🔄 Mutation (Veri Değiştirme - Create Project)
    const mutation = useMutation({
        mutationFn: api.createProject,
        onSuccess: () => {
            // Projeler listesini (cache) geçersiz kıl ve güncelle
            queryClient.invalidateQueries({ queryKey: ['projects'] })
            navigate("/projects") // İşlem bitince listeye dön
        },
        onError: (error) => {
            alert("Failed to create project: " + error)
        }
    })

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!formData.name) return
        if (formData.platforms.length === 0) {
            alert("Please select at least one target platform.")
            return
        }
        mutation.mutate(formData)
    }

    const togglePlatform = (platformId: string) => {
        setFormData(prev => {
            const exists = prev.platforms.includes(platformId)
            if (exists) {
                return { ...prev, platforms: prev.platforms.filter(p => p !== platformId) }
            } else {
                return { ...prev, platforms: [...prev.platforms, platformId] }
            }
        })
    }

    return (
        <div className="max-w-2xl mx-auto space-y-8">

            {/* 🟢 Header */}
            <div className="flex items-center gap-4">
                <Link to="/projects" className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white">
                    <ArrowLeft className="h-5 w-5" />
                </Link>
                <div>
                    <h1 className="text-2xl font-bold text-white">New Project</h1>
                    <p className="text-sm text-slate-400">Define your testing target and scope.</p>
                </div>
            </div>

            {/* 🔵 Form */}
            <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">

                {/* Project Name */}
                <div className="space-y-2">
                    <label htmlFor="name" className="text-sm font-medium text-slate-300">Project Name <span className="text-red-500">*</span></label>
                    <input
                        type="text"
                        id="name"
                        placeholder="e.g. E-Commerce Website v2"
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all placeholder:text-slate-600"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        required
                    />
                </div>

                {/* Description */}
                <div className="space-y-2">
                    <label htmlFor="description" className="text-sm font-medium text-slate-300">Description</label>
                    <textarea
                        id="description"
                        placeholder="Briefly describe the application under test..."
                        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all h-24 resize-none placeholder:text-slate-600"
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                </div>

                {/* Platform Selection */}
                <div className="space-y-3">
                    <label className="text-sm font-medium text-slate-300">Target Platforms <span className="text-red-500">*</span></label>
                    <div className="grid grid-cols-2 gap-3">
                        {PLATFORMS.map((platform) => {
                            const isSelected = formData.platforms.includes(platform.id)
                            return (
                                <div
                                    key={platform.id}
                                    onClick={() => togglePlatform(platform.id)}
                                    className={cn(
                                        "flex items-center p-3 rounded-lg border cursor-pointer transition-all select-none",
                                        isSelected
                                            ? "bg-blue-500/10 border-blue-500/50 ring-1 ring-blue-500/50"
                                            : "bg-slate-950 border-slate-800 hover:border-slate-700 hover:bg-slate-900"
                                    )}
                                >
                                    <div className={cn(
                                        "p-2 rounded-md mr-3",
                                        isSelected ? "bg-blue-500 text-white" : "bg-slate-800 text-slate-400"
                                    )}>
                                        <platform.icon className="h-4 w-4" />
                                    </div>
                                    <span className={cn(
                                        "text-sm font-medium",
                                        isSelected ? "text-blue-100" : "text-slate-400"
                                    )}>{platform.name}</span>
                                </div>
                            )
                        })}
                    </div>
                </div>

                {/* Submit Button */}
                <div className="pt-4 flex justify-end">
                    <button
                        type="submit"
                        disabled={mutation.isPending}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg font-medium flex items-center shadow-lg shadow-blue-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                        {mutation.isPending ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating...
                            </>
                        ) : (
                            <>
                                <Save className="mr-2 h-4 w-4" /> Create Project
                            </>
                        )}
                    </button>
                </div>

            </form>
        </div>
    )
}
