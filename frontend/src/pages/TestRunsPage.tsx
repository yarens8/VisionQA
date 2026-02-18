
import { useEffect, useState } from 'react';
import { Activity, Play, CheckCircle2, XCircle, Clock, AlertTriangle } from "lucide-react";
import { formatDistanceToNow } from 'date-fns';
import { tr } from 'date-fns/locale';

interface TestRun {
    id: number;
    project_id: number;
    platform: string;
    status: string;
    started_at: string | null;
    completed_at: string | null;
    target: string;
}

export function TestRunsPage() {
    const [runs, setRuns] = useState<TestRun[]>([]);
    const [loading, setLoading] = useState(true);

    // Backend'den Test Koşularını Çek
    useEffect(() => {
        const fetchRuns = async () => {
            try {
                // Not: API URL'sini env'den almak daha doğru olur ama şimdilik hardcoded
                const response = await fetch('http://localhost:8000/execution/runs');
                if (response.ok) {
                    const data = await response.json();
                    setRuns(data);
                }
            } catch (error) {
                console.error("Test runs yüklenirken hata:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchRuns();

        // Polling (Her 5 saniyede bir güncelle - Canlı takip için)
        const interval = setInterval(fetchRuns, 5000);
        return () => clearInterval(interval);
    }, []);

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed': return <CheckCircle2 className="h-5 w-5 text-green-500" />;
            case 'failed': return <XCircle className="h-5 w-5 text-red-500" />;
            case 'running': return <Activity className="h-5 w-5 text-blue-500 animate-spin" />;
            case 'crashed': return <AlertTriangle className="h-5 w-5 text-orange-500" />;
            default: return <Clock className="h-5 w-5 text-slate-500" />;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return "bg-green-500/10 text-green-400 border-green-500/20";
            case 'failed': return "bg-red-500/10 text-red-400 border-red-500/20";
            case 'running': return "bg-blue-500/10 text-blue-400 border-blue-500/20";
            case 'crashed': return "bg-orange-500/10 text-orange-400 border-orange-500/20";
            default: return "bg-slate-800 text-slate-400 border-slate-700";
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Activity className="h-8 w-8 text-blue-500" />
                        Test Koşuları
                    </h1>
                    <p className="text-slate-400 mt-2">
                        Tüm projelerde yürütülen testlerin tarihçesi ve canlı durumları.
                    </p>
                </div>

                {/* İstatistik Kartları (Mock) */}
                <div className="flex gap-4">
                    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 px-6 text-center">
                        <div className="text-2xl font-bold text-white">{runs.length}</div>
                        <div className="text-xs text-slate-500 uppercase">Toplam</div>
                    </div>
                    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 px-6 text-center">
                        <div className="text-2xl font-bold text-green-400">
                            {runs.filter(r => r.status === 'completed').length}
                        </div>
                        <div className="text-xs text-slate-500 uppercase">Başarılı</div>
                    </div>
                    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 px-6 text-center">
                        <div className="text-2xl font-bold text-red-400">
                            {runs.filter(r => r.status === 'failed' || r.status === 'crashed').length}
                        </div>
                        <div className="text-xs text-slate-500 uppercase">Hatalı</div>
                    </div>
                </div>
            </div>

            {/* Liste */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-slate-400">
                        <thead className="bg-slate-900 text-slate-200 uppercase text-xs font-semibold">
                            <tr>
                                <th className="px-6 py-4">Durum</th>
                                <th className="px-6 py-4">Hedef (URL/App)</th>
                                <th className="px-6 py-4">Platform</th>
                                <th className="px-6 py-4">Başlangıç</th>
                                <th className="px-6 py-4">Süre</th>
                                <th className="px-6 py-4 text-right">Aksiyon</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {loading ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                                        <Activity className="h-8 w-8 mx-auto mb-2 animate-spin text-blue-500" />
                                        Yükleniyor...
                                    </td>
                                </tr>
                            ) : runs.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center">
                                        <div className="flex flex-col items-center">
                                            <div className="h-16 w-16 bg-slate-900 rounded-full flex items-center justify-center mb-4">
                                                <Play className="h-8 w-8 text-slate-600" />
                                            </div>
                                            <h3 className="text-lg font-medium text-white">Henüz test koşulmadı</h3>
                                            <p className="text-slate-500 max-w-sm mt-2">
                                                İlk testinizi çalıştırmak için "Projeler" sayfasına gidin ve "Run Test" butonuna basın.
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                runs.map((run) => (
                                    <tr key={run.id} className="hover:bg-slate-900/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(run.status)}`}>
                                                {getStatusIcon(run.status)}
                                                <span className="ml-2 capitalize">{run.status}</span>
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 font-medium text-white truncate max-w-xs" title={run.target}>
                                            {run.target}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                {/* Platform İkonu */}
                                                <span className="capitalize">{run.platform}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            {run.started_at ? formatDistanceToNow(new Date(run.started_at), { addSuffix: true, locale: tr }) : '-'}
                                        </td>
                                        <td className="px-6 py-4">
                                            {run.completed_at && run.started_at
                                                ? `${((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000).toFixed(1)}s`
                                                : (run.status === 'running' ? 'Devam ediyor...' : '-')}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button className="text-blue-400 hover:text-blue-300 font-medium text-xs">
                                                Detaylar &rarr;
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

// Varsayılan export
export default TestRunsPage;
