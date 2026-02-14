
import { Bug, AlertTriangle, Video, FileText } from 'lucide-react';

export function FindingsPage() {
    // MOCK DATA (Gerçek veri gelene kadar heyecan yaratır)
    const findings = [
        {
            id: 'BUG-101',
            title: 'Login Button Unresponsive on iOS',
            severity: 'critical',
            platform: 'Mobile (iOS)',
            status: 'Open',
            found_at: '2 hours ago'
        },
        {
            id: 'BUG-102',
            title: 'Product Image 404 Error',
            severity: 'medium',
            platform: 'Web',
            status: 'Investigating',
            found_at: '5 hours ago'
        },
        {
            id: 'BUG-103',
            title: 'Checkout API Timed Out',
            severity: 'high',
            platform: 'API',
            status: 'Resolved',
            found_at: '1 day ago'
        }
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Bug className="h-8 w-8 text-red-500" />
                        Findings & Bugs
                    </h1>
                    <p className="text-slate-400 mt-2">
                        Otomatik testlerin bulduğu hatalar ve analiz raporları.
                    </p>
                </div>
                <button className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
                    <FileText className="h-4 w-4" />
                    Export Report
                </button>
            </div>

            {/* İstatistikler */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
                    <div className="flex items-center justify-between">
                        <h3 className="text-red-400 font-semibold">Critical Issues</h3>
                        <AlertTriangle className="h-6 w-6 text-red-500" />
                    </div>
                    <p className="text-3xl font-bold text-white mt-4">1</p>
                    <p className="text-sm text-red-300/60 mt-1">Requires immediate attention</p>
                </div>

                <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-6">
                    <div className="flex items-center justify-between">
                        <h3 className="text-orange-400 font-semibold">High Priority</h3>
                        <AlertTriangle className="h-6 w-6 text-orange-500" />
                    </div>
                    <p className="text-3xl font-bold text-white mt-4">5</p>
                    <p className="text-sm text-orange-300/60 mt-1">Fix within 24h</p>
                </div>

                <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-6">
                    <div className="flex items-center justify-between">
                        <h3 className="text-blue-400 font-semibold">Total Findings</h3>
                        <Bug className="h-6 w-6 text-blue-500" />
                    </div>
                    <p className="text-3xl font-bold text-white mt-4">12</p>
                    <p className="text-sm text-blue-300/60 mt-1">Last 7 days</p>
                </div>
            </div>

            {/* Liste */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden mt-8">
                <div className="p-6 border-b border-slate-800">
                    <h2 className="text-lg font-semibold text-white">Recent Findings</h2>
                </div>
                <table className="w-full text-left text-sm text-slate-400">
                    <thead className="bg-slate-900 text-slate-200 uppercase text-xs font-semibold">
                        <tr>
                            <th className="px-6 py-4">ID</th>
                            <th className="px-6 py-4">Issue</th>
                            <th className="px-6 py-4">Severity</th>
                            <th className="px-6 py-4">Platform</th>
                            <th className="px-6 py-4">Status</th>
                            <th className="px-6 py-4">Found</th>
                            <th className="px-6 py-4 md:text-right">Action</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {findings.map((f) => (
                            <tr key={f.id} className="hover:bg-slate-900/50 transition-colors">
                                <td className="px-6 py-4 font-mono text-xs text-slate-500">{f.id}</td>
                                <td className="px-6 py-4 text-white font-medium">{f.title}</td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded-full text-xs font-medium border
                                        ${f.severity === 'critical' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                                            f.severity === 'high' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
                                                'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                        }`}>
                                        {f.severity.toUpperCase()}
                                    </span>
                                </td>
                                <td className="px-6 py-4">{f.platform}</td>
                                <td className="px-6 py-4">
                                    <span className="text-slate-300">{f.status}</span>
                                </td>
                                <td className="px-6 py-4 text-slate-500">{f.found_at}</td>
                                <td className="px-6 py-4 text-right">
                                    <button className="text-blue-400 hover:text-blue-300 flex items-center justify-end gap-1 w-full">
                                        Analyze <Video className="h-4 w-4 ml-1" />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default FindingsPage; // Default export önemli
