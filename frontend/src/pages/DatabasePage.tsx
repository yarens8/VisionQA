
import { Database, Zap, AlertTriangle, CheckCircle2 } from 'lucide-react';

export function DatabasePage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <Database className="h-8 w-8 text-cyan-500" />
                Database Analysis
            </h1>
            <p className="text-slate-400 mt-2">
                SQL performans analizleri, şema değişiklikleri ve bütünlük kontrolleri.
            </p>

            {/* Metrik Kartları */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-400 text-sm font-medium">Avg Query Time</span>
                        <Zap className="h-5 w-5 text-yellow-500" />
                    </div>
                    <div className="text-3xl font-bold text-white">45ms</div>
                    <div className="text-green-500 text-xs mt-1">Faster than last week</div>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-400 text-sm font-medium">Schema Health</span>
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                    </div>
                    <div className="text-3xl font-bold text-white">98%</div>
                    <div className="text-slate-500 text-xs mt-1">Pass rate</div>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-slate-400 text-sm font-medium">Slow Queries</span>
                        <AlertTriangle className="h-5 w-5 text-red-500" />
                    </div>
                    <div className="text-3xl font-bold text-white">3</div>
                    <div className="text-red-400 text-xs mt-1">Requires optimization</div>
                </div>
            </div>

            {/* Grafik Placeholder */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-8 text-center mt-6 h-64 flex flex-col items-center justify-center">
                <Database className="h-12 w-12 text-slate-700 mb-4" />
                <h3 className="text-lg font-medium text-slate-300">Live Metrics Coming Soon</h3>
                <p className="text-slate-500 max-w-sm mt-2">
                    Veritabanı bağlantılarını konfigüre ettikten sonra burada canlı sorgu analizlerini göreceksiniz.
                </p>
            </div>
        </div>
    );
}

export default DatabasePage;
