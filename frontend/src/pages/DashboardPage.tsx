
import { useEffect, useState } from 'react'
import { Server, Database, Activity, Clock, Plus, Zap } from 'lucide-react'
import axios from 'axios'
import { Link } from 'react-router-dom'
// import { cn } from "@/lib/utils"

interface HealthStatus {
    status: string
    service: string
    database: string
    version?: string
}

export function DashboardPage() {
    const [health, setHealth] = useState<HealthStatus | null>(null)

    useEffect(() => {
        axios.get('/api/health')
            .then(res => {
                setHealth(res.data)
            })
            .catch(err => {
                console.error("Backend bağlantı hatası:", err)
            })
    }, [])

    return (
        <div className="space-y-8">

            {/* 🟢 Hero Section */}
            <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 rounded-xl p-8 shadow-sm">
                <h2 className="text-3xl font-bold text-white mb-2">Welcome Back, Admin 👋</h2>
                <p className="text-slate-400 max-w-2xl">
                    VisionQA platform is ready for your test missions. Analyze your applications across Web, Mobile, and API platforms with AI-powered agents.
                </p>

                <div className="mt-8 flex gap-4">
                    <Link to="/projects/new" className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg flex items-center font-medium transition-colors shadow-lg shadow-blue-900/20">
                        <Plus className="mr-2 h-4 w-4" /> New Project
                    </Link>
                    <Link to="/test-runs" className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-5 py-2.5 rounded-lg flex items-center font-medium transition-colors border border-slate-700">
                        <Activity className="mr-2 h-4 w-4" /> View Test Runs
                    </Link>
                </div>
            </div>

            {/* 🔵 System Status Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* Card 1: Backend API */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden group hover:border-blue-500/50 transition-colors">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <Server className="h-24 w-24 text-blue-500" />
                    </div>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">System Status</h3>
                        {health ? (
                            <span className="bg-green-500/10 text-green-400 text-xs px-2 py-1 rounded-full border border-green-500/20 font-bold">ONLINE</span>
                        ) : (
                            <span className="bg-red-500/10 text-red-400 text-xs px-2 py-1 rounded-full border border-red-500/20 font-bold">OFFLINE</span>
                        )}
                    </div>
                    <div className="text-3xl font-bold text-white mb-1">
                        {health ? "Operational" : "System Error"}
                    </div>
                    <p className="text-sm text-slate-500">API Latency: ~45ms</p>
                </div>

                {/* Card 2: Active Tests */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden group hover:border-purple-500/50 transition-colors">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <Zap className="h-24 w-24 text-purple-500" />
                    </div>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Active Tests</h3>
                        <span className="bg-blue-500/10 text-blue-400 text-xs px-2 py-1 rounded-full border border-blue-500/20 font-bold">RUNNING</span>
                    </div>
                    <div className="text-3xl font-bold text-white mb-1">0</div>
                    <p className="text-sm text-slate-500">Scheduled: 12</p>
                </div>

                {/* Card 3: Total Projects */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden group hover:border-orange-500/50 transition-colors">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                        <Database className="h-24 w-24 text-orange-500" />
                    </div>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Projects</h3>
                        <Link to="/projects" className="text-orange-400 text-xs hover:underline">View All →</Link>
                    </div>
                    <div className="text-3xl font-bold text-white mb-1">--</div>
                    <p className="text-sm text-slate-500">Last updated: Just now</p>
                </div>

            </div>

            {/* 🔴 Recent Activity Limit */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Clock className="h-5 w-5 text-slate-400" /> Recent Activity
                    </h3>
                </div>

                <div className="text-center py-12 text-slate-500 border-2 border-dashed border-slate-800 rounded-lg bg-slate-950/50">
                    <Activity className="h-12 w-12 mx-auto mb-3 opacity-20" />
                    <p>No recent activity found.</p>
                    <button className="text-blue-400 text-sm mt-2 hover:underline">Start your first test run</button>
                </div>
            </div>

        </div>
    )
}
