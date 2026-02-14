
import { Accessibility, Eye, FileSearch, Star } from 'lucide-react';

export function AccessibilityPage() {
    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <Accessibility className="h-8 w-8 text-indigo-500" />
                Accessibility (A11y)
            </h1>
            <p className="text-slate-400 mt-2">
                WCAG 2.1 standartlarına uygunluk denetimleri ve renk kontrastı analizleri.
            </p>

            {/* Score Card */}
            <div className="flex flex-col md:flex-row gap-6">
                <div className="bg-gradient-to-br from-indigo-500/20 to-purple-500/10 border border-indigo-500/30 rounded-2xl p-8 w-full md:w-1/3 flex flex-col items-center justify-center text-center">
                    <div className="relative h-32 w-32 mb-4 flex items-center justify-center">
                        <div className="absolute inset-0 rounded-full border-4 border-slate-800"></div>
                        <div className="absolute inset-0 rounded-full border-4 border-indigo-500 border-r-transparent rotate-45"></div>
                        <span className="text-4xl font-bold text-white">85</span>
                    </div>
                    <div className="text-lg font-bold text-indigo-400">WCAG Score</div>
                    <div className="text-sm text-slate-500 mt-1">AA Compliant (Mostly)</div>
                </div>

                <div className="w-full md:w-2/3 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl hover:border-slate-700 transition-colors cursor-pointer group">
                        <div className="flex items-center gap-3 mb-2">
                            <Eye className="h-6 w-6 text-blue-400 group-hover:text-blue-300" />
                            <h3 className="font-semibold text-white">Color Contrast</h3>
                        </div>
                        <p className="text-sm text-slate-400">Analiz edilen 45 elementten 3 tanesi yetersiz kontrast içeriyor.</p>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl hover:border-slate-700 transition-colors cursor-pointer group">
                        <div className="flex items-center gap-3 mb-2">
                            <FileSearch className="h-6 w-6 text-purple-400 group-hover:text-purple-300" />
                            <h3 className="font-semibold text-white">Alt Text Check</h3>
                        </div>
                        <p className="text-sm text-slate-400">Tüm görsellerde alt text mevcut. (12/12 Passed)</p>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl hover:border-slate-700 transition-colors cursor-pointer group">
                        <div className="flex items-center gap-3 mb-2">
                            <Star className="h-6 w-6 text-yellow-500 group-hover:text-yellow-400" />
                            <h3 className="font-semibold text-white">ARIA Labels</h3>
                        </div>
                        <p className="text-sm text-slate-400">Navigation menüsünde eksik ARIA etiketleri tespit edildi.</p>
                    </div>

                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl flex items-center justify-center text-center hover:bg-slate-800 transition-colors cursor-pointer">
                        <span className="text-indigo-400 font-medium">Generate Report &rarr;</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default AccessibilityPage;
