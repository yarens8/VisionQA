
import React from 'react';
import { FlaskConical, Smartphone, Monitor, Database, Server, Plus } from 'lucide-react';

export function TestLabPage() {
    const [selectedEnv, setSelectedEnv] = React.useState('desktop_web');

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <FlaskConical className="h-8 w-8 text-purple-500" />
                        Test Lab
                    </h1>
                    <p className="text-slate-400 mt-2">
                        Deneysel testlerinizi yapılandırın ve çalıştırın.
                    </p>
                </div>
                <button className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
                    <Plus className="h-4 w-4" />
                    New Experiment
                </button>
            </div>

            {/* Platform Seçimi */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Select Environment</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { id: 'desktop_web', name: 'Desktop Web', icon: Monitor },
                        { id: 'mobile_app', name: 'Mobile App', icon: Smartphone },
                        { id: 'api_gateway', name: 'API Gateway', icon: Server },
                        { id: 'database_engine', name: 'Database Engine', icon: Database },
                    ].map((env) => (
                        <button
                            key={env.id}
                            onClick={() => setSelectedEnv(env.id)}
                            className={`flex flex-col items-center justify-center gap-3 p-4 border rounded-lg transition-all group
                                ${selectedEnv === env.id
                                    ? 'bg-purple-500/10 border-purple-500 text-purple-400'
                                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-600 hover:bg-slate-800'
                                }`}
                        >
                            <env.icon className={`h-8 w-8 ${selectedEnv === env.id ? 'text-purple-400' : 'text-slate-500 group-hover:text-slate-300'}`} />
                            <span className="text-sm font-medium">{env.name}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Yakındaki Deneyler */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-8 text-center mt-6">
                <FlaskConical className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">No Active Experiments</h3>
                <p className="text-slate-400 max-w-md mx-auto">
                    Test Lab modülü, özel konfigürasyonlarla (örneğin: Network Throttling, GPS Mocking) test yapmanızı sağlar. Yakında aktif olacak.
                </p>
            </div>
        </div>
    );
}

export default TestLabPage;
