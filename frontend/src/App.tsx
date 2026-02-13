
import { useEffect, useState } from 'react'
import { CheckCircle2, Server, Database, Activity } from 'lucide-react'
import axios from 'axios'

interface HealthStatus {
    status: string
    service: string
    database: string
    version?: string
}

function App() {
    const [health, setHealth] = useState<HealthStatus | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // Backend health check
        axios.get('/api/health')
            .then(res => {
                setHealth(res.data)
                setLoading(false)
            })
            .catch(err => {
                console.error("Backend bağlantı hatası:", err)
                setLoading(false)
            })
    }, [])

    return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
            <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden p-8 space-y-6">

                {/* Header */}
                <div className="text-center space-y-2">
                    <div className="bg-blue-600/20 text-blue-400 p-3 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4 animate-pulse">
                        <Activity size={32} />
                    </div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                        VisionQA
                    </h1>
                    <p className="text-slate-400 text-sm font-medium">
                        Universal AI-Powered Test Platform
                    </p>
                </div>

                {/* Status Indicators */}
                <div className="space-y-4 pt-4 border-t border-slate-800/50">

                    {/* Frontend Status */}
                    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                        <div className="flex items-center gap-3">
                            <div className="bg-green-500/20 p-2 rounded-md">
                                <CheckCircle2 size={18} className="text-green-400" />
                            </div>
                            <span className="text-slate-200 font-medium">Frontend (React)</span>
                        </div>
                        <span className="text-green-500 text-xs font-bold px-2 py-1 bg-green-500/10 rounded-full">
                            ONLINE
                        </span>
                    </div>

                    {/* Backend Status */}
                    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                        <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-md ${health ? 'bg-blue-500/20' : 'bg-red-500/20'}`}>
                                <Server size={18} className={health ? 'text-blue-400' : 'text-red-400'} />
                            </div>
                            <span className="text-slate-200 font-medium">Backend API</span>
                        </div>
                        {loading ? (
                            <span className="text-slate-500 text-xs animate-pulse">Connecting...</span>
                        ) : health ? (
                            <span className="text-blue-400 text-xs font-bold px-2 py-1 bg-blue-500/10 rounded-full">
                                CONNECTED
                            </span>
                        ) : (
                            <span className="text-red-500 text-xs font-bold px-2 py-1 bg-red-500/10 rounded-full">
                                OFFLINE
                            </span>
                        )}
                    </div>

                    {/* Database Status */}
                    <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                        <div className="flex items-center gap-3">
                            <div className={`p-2 rounded-md ${health?.database === 'connected' ? 'bg-purple-500/20' : 'bg-slate-700/50'}`}>
                                <Database size={18} className={health?.database === 'connected' ? 'text-purple-400' : 'text-slate-500'} />
                            </div>
                            <span className="text-slate-200 font-medium">PostgreSQL</span>
                        </div>
                        {health?.database === 'connected' ? (
                            <span className="text-purple-400 text-xs font-bold px-2 py-1 bg-purple-500/10 rounded-full">
                                READY
                            </span>
                        ) : (
                            <span className="text-slate-600 text-xs">Waiting...</span>
                        )}
                    </div>

                </div>

                <div className="text-center pt-4">
                    <button
                        onClick={() => window.location.reload()}
                        className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                    >
                        Refresh Status
                    </button>
                </div>

            </div>

            <div className="mt-8 text-slate-600 text-xs text-center">
                Powered by <span className="text-slate-400 font-semibold">Gemini 2.0 & Cortex</span>
            </div>
        </div>
    )
}

export default App
