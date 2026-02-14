
import { ShieldAlert, Unlock, Lock, AlertTriangle, CheckCircle } from 'lucide-react';

export function SecurityPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <ShieldAlert className="h-8 w-8 text-blue-500" />
                Security Scan
            </h1>
            <p className="text-slate-400 mt-2">
                Otomatik güvenlik taramaları (OWASP Top 10, Port Scan, Encryption Check).
            </p>

            {/* Durum Özet */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-green-500/10 border border-green-500/20 p-4 rounded-lg flex items-center justify-between">
                    <div>
                        <div className="text-green-400 font-bold text-xl">Passed</div>
                        <div className="text-xs text-green-300/60">HTTPS Check</div>
                    </div>
                    <Lock className="h-6 w-6 text-green-500" />
                </div>
                <div className="bg-green-500/10 border border-green-500/20 p-4 rounded-lg flex items-center justify-between">
                    <div>
                        <div className="text-green-400 font-bold text-xl">Passed</div>
                        <div className="text-xs text-green-300/60">Port Security</div>
                    </div>
                    <CheckCircle className="h-6 w-6 text-green-500" />
                </div>
                <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-lg flex items-center justify-between">
                    <div>
                        <div className="text-red-400 font-bold text-xl">Fail</div>
                        <div className="text-xs text-red-300/60">XSS Check</div>
                    </div>
                    <Unlock className="h-6 w-6 text-red-500" />
                </div>
                <div className="bg-orange-500/10 border border-orange-500/20 p-4 rounded-lg flex items-center justify-between">
                    <div>
                        <div className="text-orange-400 font-bold text-xl">Warning</div>
                        <div className="text-xs text-orange-300/60">Headers</div>
                    </div>
                    <AlertTriangle className="h-6 w-6 text-orange-500" />
                </div>
            </div>

            {/* Detay Tablosu (Mock) */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden mt-6">
                <div className="p-4 bg-slate-900 border-b border-slate-800 font-medium text-slate-300">
                    Latest Vulnerability Scan Results
                </div>
                <div className="p-8 text-center text-slate-500">
                    Scanning in progress... (Mock)
                </div>
            </div>
        </div>
    );
}

export default SecurityPage;
