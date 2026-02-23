import { useQuery } from '@tanstack/react-query';
import { Server, Database, Activity, Clock, Plus, Zap, TrendingUp, CheckCircle2, XCircle, AlertTriangle, Globe, Smartphone, Monitor, Code2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api, AlertsResponse, DashboardStats, Alert } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { formatDistanceToNow } from 'date-fns';

export function DashboardPage() {
    // Fetch dashboard stats
    const { data: stats, isLoading } = useQuery<DashboardStats>({
        queryKey: ['dashboardStats'],
        queryFn: api.getDashboardStats,
        refetchInterval: 30000 // Her 30 saniyede bir yenile
    });

    // Fetch alerts
    const { data: alerts } = useQuery<AlertsResponse>({
        queryKey: ['alerts'],
        queryFn: api.getAlerts,
        refetchInterval: 60000 // Her 1 dakikada bir kontrol et
    });

    return (
        <div className="space-y-8">
            {/* Hero Section */}
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

            {/* Intelligent Alerts Panel */}
            {alerts && alerts.total_alerts > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                            <AlertTriangle className="h-5 w-5 text-yellow-500" />
                            Intelligent Alerts
                            <span className="ml-2 bg-red-500/10 text-red-400 text-xs px-2 py-1 rounded-full border border-red-500/20 font-bold">
                                {alerts.critical_count} Critical
                            </span>
                            <span className="bg-yellow-500/10 text-yellow-400 text-xs px-2 py-1 rounded-full border border-yellow-500/20 font-bold">
                                {alerts.warning_count} Warning
                            </span>
                        </h3>
                    </div>

                    <div className="space-y-3">
                        {alerts.alerts.map((alert: Alert, index: number) => (
                            <div
                                key={index}
                                className={`p-4 rounded-lg border ${alert.severity === 'high'
                                    ? 'bg-red-500/5 border-red-500/30'
                                    : alert.severity === 'medium'
                                        ? 'bg-yellow-500/5 border-yellow-500/30'
                                        : 'bg-blue-500/5 border-blue-500/30'
                                    }`}
                            >
                                <div className="flex items-start gap-3">
                                    <AlertTriangle className={`h-5 w-5 mt-0.5 ${alert.severity === 'high' ? 'text-red-500'
                                        : alert.severity === 'medium' ? 'text-yellow-500'
                                            : 'text-blue-500'
                                        }`} />
                                    <div className="flex-1">
                                        <h4 className="text-white font-semibold">{alert.title}</h4>
                                        <p className="text-slate-400 text-sm mt-1">{alert.message}</p>
                                        <p className="text-slate-500 text-xs mt-2 italic">
                                            💡 <strong>Action:</strong> {alert.action}
                                        </p>
                                    </div>
                                    <span className={`px-2 py-1 rounded-full text-xs font-bold ${alert.severity === 'high'
                                        ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                                        : alert.severity === 'medium'
                                            ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20'
                                            : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                                        }`}>
                                        {alert.severity.toUpperCase()}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                {/* Total Projects */}
                <Link to="/projects" className="block">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden group hover:border-blue-500/50 transition-colors cursor-pointer">
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                            <Database className="h-24 w-24 text-blue-500" />
                        </div>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Projects</h3>
                            <span className="text-blue-400 text-xs">View →</span>
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">
                            {isLoading ? '...' : stats?.total_projects || 0}
                        </div>
                        <p className="text-sm text-slate-500">Total active projects</p>
                    </div>
                </Link>

                {/* Total Test Cases */}
                <Link to="/projects" className="block">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden group hover:border-purple-500/50 transition-colors cursor-pointer">
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                            <Zap className="h-24 w-24 text-purple-500" />
                        </div>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Test Cases</h3>
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">
                            {isLoading ? '...' : stats?.total_cases || 0}
                        </div>
                        <p className="text-sm text-slate-500">AI + Manual tests</p>
                    </div>
                </Link>

                {/* Recent Runs (Last 7 days) */}
                <Link to="/test-runs" className="block">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden group hover:border-orange-500/50 transition-colors cursor-pointer">
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                            <TrendingUp className="h-24 w-24 text-orange-500" />
                        </div>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Recent Runs</h3>
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">
                            {isLoading ? '...' : stats?.recent_runs || 0}
                        </div>
                        <p className="text-sm text-slate-500">Last 7 days</p>
                    </div>
                </Link>

                {/* Success Rate */}
                <Link to="/findings" className="block">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden group hover:border-green-500/50 transition-colors cursor-pointer">
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                            <Server className="h-24 w-24 text-green-500" />
                        </div>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">Success Rate</h3>
                            <span className={`text-xs px-2 py-1 rounded-full border font-bold ${(stats?.success_rate || 0) >= 80
                                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                                }`}>
                                {isLoading ? '...' : `${stats?.success_rate || 0}%`}
                            </span>
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">
                            {isLoading ? '...' : `${stats?.success_rate || 0}%`}
                        </div>
                        <p className="text-sm text-slate-500">Pass rate (all time)</p>
                    </div>
                </Link>
            </div>

            {/* Weekly Trend Chart */}
            {stats && stats.weekly_trend && stats.weekly_trend.length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-blue-400" />
                        Weekly Test Activity
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={stats.weekly_trend}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis
                                dataKey="date"
                                stroke="#94a3b8"
                                tick={{ fill: '#94a3b8', fontSize: 12 }}
                                tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            />
                            <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                                labelStyle={{ color: '#e2e8f0' }}
                            />
                            <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6', r: 4 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Platform Breakdown */}
            {stats && stats.platform_breakdown && stats.platform_breakdown.length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                        <Globe className="h-5 w-5 text-purple-400" />
                        Platform Breakdown
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {stats.platform_breakdown.map((p) => {
                            const platformIcons: Record<string, React.ReactNode> = {
                                web: <Globe className="h-5 w-5" />,
                                mobile_android: <Smartphone className="h-5 w-5" />,
                                desktop_windows: <Monitor className="h-5 w-5" />,
                                api: <Code2 className="h-5 w-5" />,
                                database: <Database className="h-5 w-5" />,
                            };
                            const platformColors: Record<string, string> = {
                                web: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
                                mobile_android: 'text-green-400 bg-green-500/10 border-green-500/20',
                                desktop_windows: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
                                api: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
                                database: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
                            };
                            const colorClass = platformColors[p.platform] || 'text-slate-400 bg-slate-500/10 border-slate-500/20';
                            return (
                                <div key={p.platform} className={`rounded-xl border p-4 ${colorClass}`}>
                                    <div className="flex items-center gap-2 mb-3">
                                        {platformIcons[p.platform] || <Server className="h-5 w-5" />}
                                        <span className="font-semibold text-sm capitalize">{p.platform.replace('_', ' ')}</span>
                                    </div>
                                    <div className="text-2xl font-bold mb-1">{p.total_runs}</div>
                                    <div className="text-xs opacity-70">runs • {p.success_rate}% success</div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* Recent Test Runs */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <Clock className="h-5 w-5 text-slate-400" /> Recent Test Runs
                    </h3>
                    <Link to="/test-runs" className="text-blue-400 text-sm hover:underline">View All →</Link>
                </div>

                {isLoading ? (
                    <div className="text-center py-12 text-slate-500">
                        <Activity className="h-12 w-12 mx-auto mb-3 opacity-20 animate-pulse" />
                        <p>Loading...</p>
                    </div>
                ) : stats && stats.recent_test_runs && stats.recent_test_runs.length > 0 ? (
                    <div className="space-y-3">
                        {stats.recent_test_runs.slice(0, 5).map((run) => (
                            <div key={run.id} className="flex items-center justify-between p-4 bg-slate-950 rounded-lg border border-slate-800 hover:border-slate-700 transition-colors">
                                <div className="flex items-center gap-4">
                                    {run.status === 'completed' ? (
                                        <CheckCircle2 className="h-5 w-5 text-green-500 shrink-0" />
                                    ) : (
                                        <XCircle className="h-5 w-5 text-red-500 shrink-0" />
                                    )}
                                    <div>
                                        <p className="text-white font-medium">{run.case_title}</p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className="text-xs text-slate-500 capitalize">{run.platform?.replace('_', ' ')}</span>
                                            <span className="text-slate-700">•</span>
                                            <span className="text-xs text-slate-500">{run.module}</span>
                                            <span className="text-slate-700">•</span>
                                            <span className="text-xs text-slate-500">
                                                {run.created_at ? formatDistanceToNow(new Date(run.created_at), { addSuffix: true }) : 'Unknown time'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className="text-sm text-slate-400">{run.duration}</span>
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${run.status === 'completed'
                                        ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                                        : 'bg-red-500/10 text-red-400 border border-red-500/20'
                                        }`}>
                                        {run.status}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12 text-slate-500 border-2 border-dashed border-slate-800 rounded-lg bg-slate-950/50">
                        <Activity className="h-12 w-12 mx-auto mb-3 opacity-20" />
                        <p>No recent activity found.</p>
                        <Link to="/projects" className="text-blue-400 text-sm mt-2 hover:underline inline-block">
                            Start your first test run
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}
