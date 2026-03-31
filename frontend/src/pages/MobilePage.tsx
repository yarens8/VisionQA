import { useState } from 'react';
import { Loader2, Smartphone, Sparkles, Wand2 } from 'lucide-react';

import { api, MobileAnalysisResponse } from '../services/api';

const severityClasses: Record<string, string> = {
    high: 'border-red-500/40 bg-red-500/10 text-red-200',
    medium: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
    low: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200',
};

const sampleMetadata = JSON.stringify(
    [
        { element_type: 'input', x: 20, y: 84, width: 280, height: 42, text_content: 'Email address' },
        { element_type: 'input', x: 20, y: 138, width: 280, height: 42, text_content: 'Password' },
        { element_type: 'button', x: 20, y: 196, width: 40, height: 38, text_content: 'Continue' },
        { element_type: 'button', x: 72, y: 196, width: 40, height: 38, text_content: 'Help' },
        { element_type: 'button', x: 124, y: 196, width: 40, height: 38, text_content: 'Google' },
        { element_type: 'button', x: 176, y: 196, width: 40, height: 38, text_content: 'Apple' },
        { element_type: 'link', x: 20, y: 258, width: 110, height: 24, text_content: 'Forgot password?' },
    ],
    null,
    2,
);

export function MobilePage() {
    const [platform, setPlatform] = useState('android');
    const [screenName, setScreenName] = useState('Login Screen');
    const [metadata, setMetadata] = useState(sampleMetadata);
    const [imageBase64, setImageBase64] = useState<string | undefined>(undefined);
    const [preview, setPreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<MobileAnalysisResponse | null>(null);

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) {
            setImageBase64(undefined);
            setPreview(null);
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            const output = String(reader.result || '');
            const [, base64] = output.split(',');
            setPreview(output);
            setImageBase64(base64);
        };
        reader.readAsDataURL(file);
    };

    const handleAnalyze = async () => {
        setLoading(true);
        try {
            const parsedMetadata = metadata.trim() ? JSON.parse(metadata) : [];
            const response = await api.analyzeMobile({
                platform,
                screen_name: screenName,
                image_base64: imageBase64,
                element_metadata: parsedMetadata,
            });
            setResult(response);
        } catch (error: any) {
            setResult(null);
            alert(error.response?.data?.detail || error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                    <Smartphone className="h-8 w-8 text-sky-400" />
                    Mobil Test Modulu
                </h1>
                <p className="mt-2 text-slate-400">
                    Screenshot + metadata tabanli mobil UX, responsive risk ve capability analizi.
                </p>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr] items-start">
                <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6 space-y-5">
                    <div className="grid gap-4 md:grid-cols-2">
                        <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none">
                            <option value="android">Android</option>
                            <option value="ios">iOS</option>
                        </select>
                        <input value={screenName} onChange={(e) => setScreenName(e.target.value)} placeholder="Screen name" className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none" />
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                        <p className="text-sm font-semibold text-white">Mobil Screenshot</p>
                        <div className="mt-3 flex flex-wrap items-center gap-3">
                            <label className="inline-flex cursor-pointer items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:border-sky-400/50 hover:text-sky-300">
                                <Wand2 className="h-4 w-4" />
                                Screenshot Sec
                                <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
                            </label>
                            {preview && <span className="text-xs text-slate-400">Screenshot yüklendi</span>}
                        </div>
                        {preview && (
                            <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
                                <img src={preview} alt="Mobile preview" className="max-h-[360px] w-full object-contain" />
                            </div>
                        )}
                    </div>

                    <div>
                        <p className="mb-3 text-sm font-semibold text-white">Element Metadata</p>
                        <textarea
                            value={metadata}
                            onChange={(e) => setMetadata(e.target.value)}
                            rows={14}
                            className="w-full rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 font-mono text-sm text-cyan-300 outline-none"
                        />
                    </div>

                    <button onClick={handleAnalyze} disabled={loading} className="inline-flex items-center gap-2 rounded-xl bg-sky-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:opacity-50">
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                        Mobil Analizini Baslat
                    </button>
                </div>

                {result && (
                    <div className="space-y-6">
                        <div className="grid gap-4 sm:grid-cols-3">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Overall</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.overall_score}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Screen Type</p>
                                <p className="mt-3 text-3xl font-semibold text-white capitalize">{result.context_profile.screen_type}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Patterns</p>
                                <p className="mt-3 text-sm font-semibold text-cyan-300">{result.context_profile.detected_patterns.join(' • ')}</p>
                            </div>
                        </div>

                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Task Friction</p>
                                <p className="mt-3 text-3xl font-semibold text-white">{result.task_completion_friction}</p>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
                                <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Parity</p>
                                <p className="mt-3 text-sm font-semibold text-cyan-300">{result.cross_platform_parity_summary}</p>
                            </div>
                        </div>

                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">AI Mobile Interpretation</p>
                            <p className="mt-3 text-sm text-slate-300">{result.ai_interpretation}</p>
                            <div className="mt-4 rounded-2xl border border-sky-500/20 bg-sky-500/10 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-sky-300">AI Mobile Critic</p>
                                <p className="mt-2 text-sm text-sky-100">{result.ai_mobile_critic}</p>
                            </div>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Root Cause Summary</p>
                                <p className="mt-2 text-sm text-slate-300">{result.root_cause_summary}</p>
                            </div>
                            <div className="mt-4 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4">
                                <p className="text-xs uppercase tracking-[0.24em] text-cyan-300">Cross-Platform Signal</p>
                                <p className="mt-2 text-sm text-cyan-100">{result.context_profile.cross_platform_consistency_signal}</p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {result && (
                <>
                    <div className="grid gap-6 xl:grid-cols-3">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Score Breakdown</p>
                            <div className="mt-4 grid gap-3">
                                {Object.entries(result.score_breakdown).map(([key, value]) => (
                                    <div key={key} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                                        <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{key}</p>
                                        <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Supported Now</p>
                            <div className="mt-4 space-y-3">
                                {result.supported_now.map((item) => (
                                    <div key={item.title} className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4">
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="text-sm font-semibold text-emerald-100">{item.title}</p>
                                            <span className="rounded-full border border-emerald-300/20 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em] text-emerald-200">{item.status}</span>
                                        </div>
                                        <p className="mt-2 text-sm text-emerald-50/90">{item.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Next Phase</p>
                            <div className="mt-4 space-y-3">
                                {result.next_phase.map((item) => (
                                    <div key={item.title} className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4">
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="text-sm font-semibold text-amber-100">{item.title}</p>
                                            <span className="rounded-full border border-amber-300/20 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em] text-amber-200">{item.status}</span>
                                        </div>
                                        <p className="mt-2 text-sm text-amber-50/90">{item.description}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="grid gap-6 xl:grid-cols-3">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Thumb Zone</p>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                {result.thumb_zone_summary}
                            </div>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Keyboard Overlap</p>
                            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                {result.keyboard_overlap_signal}
                            </div>
                        </div>
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Safe Area & Gesture</p>
                            <div className="mt-4 space-y-3">
                                <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                    {result.safe_area_signal}
                                </div>
                                <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                    {result.gesture_friction_summary}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
                        <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-white font-semibold">Mobile Findings</p>
                            <div className="mt-4 space-y-3">
                                {result.findings.length === 0 ? (
                                    <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                                        Bu kosumda belirgin mobil UX bulgusu cikmadi.
                                    </div>
                                ) : result.findings.map((finding) => (
                                    <div key={finding.id} className={`rounded-2xl border p-4 ${severityClasses[finding.severity] ?? 'border-slate-700 bg-slate-950 text-slate-200'}`}>
                                        <div className="flex items-center justify-between gap-3">
                                            <p className="font-semibold">{finding.title}</p>
                                            <span className="rounded-full border border-current/30 px-2.5 py-1 text-[11px] uppercase tracking-[0.24em]">{finding.severity}</span>
                                        </div>
                                        <p className="mt-3 text-sm">{finding.description}</p>
                                        <p className="mt-2 text-xs text-slate-300/90">Kanit: {finding.evidence}</p>
                                        <p className="mt-2 text-xs text-slate-300/90">Oneri: {finding.recommendation}</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Context Playbook</p>
                                <div className="mt-4 space-y-3">
                                    {result.context_playbook.map((item) => (
                                        <div key={item} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-3xl border border-slate-800 bg-slate-900 p-5">
                                <p className="text-white font-semibold">Recommendations</p>
                                <div className="mt-4 space-y-3">
                                    {result.recommendations.map((item) => (
                                        <div key={item} className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

export default MobilePage;
