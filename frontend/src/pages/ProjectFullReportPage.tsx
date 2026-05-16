import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
    Activity,
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    Download,
    FileText,
    GitMerge,
    Loader2,
    ShieldAlert,
    XCircle,
} from 'lucide-react';
import { api, ProjectSummaryReport } from '@/services/api';

const severityStyles: Record<string, string> = {
    critical: 'border-red-400/30 bg-red-500/10 text-red-100',
    high: 'border-red-400/30 bg-red-500/10 text-red-100',
    medium: 'border-amber-400/30 bg-amber-500/10 text-amber-100',
    low: 'border-blue-400/30 bg-blue-500/10 text-blue-100',
    info: 'border-slate-600 bg-slate-800 text-slate-200',
};

function severityClass(severity?: string) {
    return severityStyles[String(severity || 'info').toLowerCase()] || severityStyles.info;
}

function moduleStatusClass(status?: string) {
    switch (String(status || '').toLowerCase()) {
        case 'healthy':
            return 'border-emerald-400/25 bg-emerald-500/10 text-emerald-100';
        case 'attention':
            return 'border-amber-400/25 bg-amber-500/10 text-amber-100';
        case 'observed':
            return 'border-blue-400/25 bg-blue-500/10 text-blue-100';
        default:
            return 'border-slate-700 bg-slate-900 text-slate-400';
    }
}

function downloadJson(report: ProjectSummaryReport) {
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `visionqa_project_${report.project.id}_report.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
}

export default function ProjectFullReportPage() {
    const { projectId } = useParams();
    const { data: report, isLoading, error } = useQuery({
        queryKey: ['projectFullReport', projectId],
        queryFn: () => api.getProjectSummaryReport(Number(projectId)),
        enabled: Boolean(projectId),
        refetchInterval: 15000,
    });

    const securityActions = report?.security.priority_actions ?? [];
    const testActions = report?.tests.priority_actions ?? [];
    const bugReports = report?.tests.bug_reports ?? [];
    const apiActions = report?.api?.priority_actions ?? [];
    const correlations = report?.correlation?.items ?? [];
    const runs = report?.runs ?? [];
    const failedRuns = runs.filter(run => run.status === 'failed');
    const fallbackModuleItems = report ? [
        {
            module: 'autonomous',
            label: 'Autonomous Testing',
            status: report.summary.failed_runs > 0 ? 'attention' : 'observed',
            score: null,
            records: report.summary.total_runs,
            findings: report.summary.failed_runs,
            summary: `${report.summary.total_runs} run, ${report.summary.failed_runs} failed run ve ${report.summary.test_actions} test action sinyali var.`,
            latest: [],
        },
        {
            module: 'bug_analysis',
            label: 'Bug Analysis',
            status: (report.summary.bug_reports ?? bugReports.length) > 0 ? 'attention' : 'not_connected',
            score: null,
            records: report.summary.bug_reports ?? bugReports.length,
            findings: report.summary.bug_reports ?? bugReports.length,
            summary: `${report.summary.bug_reports ?? bugReports.length} structured bug report kaydi var.`,
            latest: [],
        },
        {
            module: 'security',
            label: 'Security',
            status: report.summary.high_security_risks + report.summary.medium_security_risks > 0 ? 'attention' : 'observed',
            score: null,
            records: report.summary.security_records,
            findings: report.summary.high_security_risks + report.summary.medium_security_risks,
            summary: `${report.summary.security_records} security analizi, ${report.summary.high_security_risks + report.summary.medium_security_risks} risk sinyali var.`,
            latest: [],
        },
        {
            module: 'correlation',
            label: 'Cross-Module',
            status: report.summary.correlations > 0 ? 'attention' : 'observed',
            score: null,
            records: report.summary.correlations,
            findings: report.summary.correlations,
            summary: `${report.summary.correlations} cross-module correlation sinyali var.`,
            latest: [],
        },
    ] : [];
    const moduleItems = report?.module_breakdown?.items?.length
        ? report.module_breakdown.items
        : fallbackModuleItems;
    const generatedAt = report
        ? new Date(report.generated_at).toLocaleString('tr-TR', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
        })
        : '';

    if (isLoading) {
        return (
            <div className="flex min-h-[420px] flex-col items-center justify-center text-slate-500">
                <Loader2 className="mb-4 h-10 w-10 animate-spin text-blue-400" />
                Project report hazırlanıyor...
            </div>
        );
    }

    if (error || !report) {
        return (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-6 text-red-100">
                Project report yüklenemedi.
            </div>
        );
    }

    return (
        <div className="mx-auto max-w-7xl space-y-6 pb-8 animate-in fade-in duration-500">
            <section className="rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-2xl shadow-black/20">
                <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <Link to={`/projects/${report.project.id}/pages`} className="inline-flex items-center text-xs font-bold uppercase tracking-[0.2em] text-slate-500 transition-colors hover:text-white">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Modules
                        </Link>
                        <div className="mt-5 flex items-center gap-4">
                            <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-400/20 bg-blue-500/15 text-blue-200">
                                <FileText className="h-8 w-8" />
                            </div>
                            <div>
                                <div className="flex flex-wrap items-center gap-2">
                                    <span className="text-xs uppercase tracking-[0.24em] text-blue-300">Final Report</span>
                                    <span className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-[11px] text-slate-400">{generatedAt}</span>
                                </div>
                                <h1 className="mt-1 text-4xl font-black text-white">{report.project.name}</h1>
                                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                                    Project quality, security actions, failed test evidence ve correlation sinyalleri tek raporda toplandı.
                                </p>
                            </div>
                        </div>
                    </div>
                    <button
                        type="button"
                        onClick={() => downloadJson(report)}
                        className="inline-flex items-center justify-center rounded-xl border border-blue-400/25 bg-blue-500/15 px-5 py-3 text-sm font-bold text-blue-100 transition hover:bg-blue-500/25"
                    >
                        <Download className="mr-2 h-4 w-4" />
                        Export JSON
                    </button>
                </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
                    {[
                        ['Overall', report.overall_score, 'text-white'],
                        ['Runs', report.summary.total_runs, 'text-blue-100'],
                        ['Failed', report.summary.failed_runs, 'text-red-100'],
                        ['Security', report.summary.high_security_risks + report.summary.medium_security_risks, 'text-amber-100'],
                        ['Correlation', report.summary.correlations, 'text-violet-100'],
                        ['Bugs', report.summary.bug_reports ?? bugReports.length, 'text-sky-100'],
                    ].map(([label, value, color]) => (
                        <div key={label} className="rounded-2xl border border-slate-800 bg-slate-900/80 px-5 py-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{label}</div>
                            <div className={`mt-2 text-3xl font-black ${color}`}>{value}</div>
                        </div>
                    ))}
                </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-cyan-300">
                        <Activity className="h-4 w-4" />
                        Module Breakdown
                    </div>
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-2.5 py-1 text-[11px] text-cyan-100">{moduleItems.length} modules</span>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    {moduleItems.length ? moduleItems.map((item) => (
                        <div key={item.module} className={`rounded-2xl border p-4 ${moduleStatusClass(item.status)}`}>
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <h3 className="text-sm font-black text-white">{item.label}</h3>
                                    <p className="mt-1 text-[10px] uppercase tracking-[0.18em] opacity-70">{item.status}</p>
                                </div>
                                <div className="text-right">
                                    <div className="text-2xl font-black text-white">{item.score ?? '--'}</div>
                                    <div className="text-[10px] uppercase tracking-[0.16em] opacity-60">score</div>
                                </div>
                            </div>
                            <p className="mt-3 min-h-[42px] text-sm leading-6 text-slate-300">{item.summary}</p>
                            <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                                <div className="rounded-xl border border-white/10 bg-slate-950/50 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Records</div>
                                    <div className="mt-1 text-lg font-black text-white">{item.records}</div>
                                </div>
                                <div className="rounded-xl border border-white/10 bg-slate-950/50 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Findings</div>
                                    <div className="mt-1 text-lg font-black text-white">{item.findings}</div>
                                </div>
                            </div>
                        </div>
                    )) : (
                        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                            Modül çıktıları oluşunca burada özetlenir.
                        </div>
                    )}
                </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-cyan-300">
                        <Activity className="h-4 w-4" />
                        API Endpoint Actions
                    </div>
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-2.5 py-1 text-[11px] text-cyan-100">{apiActions.length} action</span>
                </div>
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {apiActions.length ? apiActions.map((action, index) => (
                        <div key={`${action.api_record_id}-${action.category}-${index}`} className="rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-4">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                    <p className="mt-1 truncate text-xs uppercase tracking-[0.16em] text-cyan-200">
                                        {action.method || 'API'} {action.endpoint || 'endpoint'}
                                    </p>
                                    {(action.duplicate_count || 0) > 1 && (
                                        <p className="mt-1 text-xs text-cyan-100/70">
                                            {action.duplicate_count} tekrar eden kayıt birleştirildi.
                                        </p>
                                    )}
                                </div>
                                <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.category}</span>
                            </div>
                            <p className="mt-3 text-sm leading-6 text-slate-300">{action.summary}</p>
                            <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Status</div>
                                    <div className="mt-1 text-white">{action.status_code ?? 'n/a'}</div>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Duration</div>
                                    <div className="mt-1 text-white">{Math.round(Number(action.duration_ms || 0))} ms</div>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Signals</div>
                                    <div className="mt-1 text-white">
                                        {[
                                            action.evidence_summary?.contract_signals || 0,
                                            action.evidence_summary?.security_signals || 0,
                                            action.evidence_summary?.performance_signals || 0,
                                            action.evidence_summary?.availability_signals || 0,
                                        ].reduce((total, value) => total + value, 0)}
                                    </div>
                                </div>
                            </div>
                            <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                                Evidence: {action.evidence || 'API response evidence'}
                            </div>
                            <p className="mt-3 text-sm leading-6 text-cyan-100">{action.recommendation}</p>
                        </div>
                    )) : (
                        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                            API bulgusu oluşunca endpoint aksiyonları burada görünür.
                        </div>
                    )}
                </div>
            </section>

            <section className="grid gap-5 xl:grid-cols-2">
                <div className="flex h-[420px] flex-col rounded-3xl border border-slate-800 bg-slate-950 p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-violet-300">
                            <GitMerge className="h-4 w-4" />
                            Cross-Module Correlation
                        </div>
                        <span className="rounded-full border border-violet-400/20 bg-violet-500/10 px-2.5 py-1 text-[11px] text-violet-100">{correlations.length} item</span>
                    </div>
                    <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-2">
                        {correlations.length ? correlations.map((item, index) => (
                            <div key={`${item.target}-${index}`} className="rounded-xl border border-violet-400/20 bg-violet-500/10 p-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <h3 className="text-sm font-bold text-white">{item.title}</h3>
                                        <p className="mt-1 truncate text-xs uppercase tracking-[0.16em] text-violet-200">{item.target}</p>
                                        {(item.duplicate_count || 0) > 1 && (
                                            <p className="mt-1 text-xs text-violet-100/70">
                                                {item.duplicate_count} tekrar eden correlation birleştirildi.
                                            </p>
                                        )}
                                    </div>
                                    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(item.severity)}`}>{item.severity}</span>
                                </div>
                                <p className="mt-3 text-sm leading-6 text-slate-300">{item.recommendation}</p>
                                {item.evidence?.bug_categories && item.evidence.bug_categories.length > 0 && (
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        {item.evidence.bug_categories.map((category) => (
                                            <span key={category} className="rounded-lg border border-blue-400/20 bg-blue-500/10 px-2.5 py-1 text-[10px] font-bold text-blue-100">
                                                {category}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )) : (
                            <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                                Aynı hedefte birden fazla modül sinyali oluşunca correlation burada listelenir.
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex h-[420px] flex-col rounded-3xl border border-slate-800 bg-slate-950 p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-red-300">
                            <ShieldAlert className="h-4 w-4" />
                            Priority Security Actions
                        </div>
                        <span className="rounded-full border border-red-400/20 bg-red-500/10 px-2.5 py-1 text-[11px] text-red-100">{securityActions.length} action</span>
                    </div>
                    <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-2">
                        {securityActions.length ? securityActions.slice(0, 5).map((action, index) => (
                            <div key={`${action.title}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                                <div className="flex items-start justify-between gap-3">
                                    <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.severity}</span>
                                </div>
                                <p className="mt-2 text-sm leading-6 text-slate-300">{action.recommendation}</p>
                            </div>
                        )) : (
                            <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                                Security analiziyle eşleşen öncelikli aksiyon yok.
                            </div>
                        )}
                    </div>
                </div>
            </section>

            <section className="grid gap-5 xl:grid-cols-2">
                <div className="flex h-[420px] flex-col rounded-3xl border border-slate-800 bg-slate-950 p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-blue-300">
                            <AlertTriangle className="h-4 w-4" />
                            Failed Test Actions
                        </div>
                        <span className="rounded-full border border-blue-400/20 bg-blue-500/10 px-2.5 py-1 text-[11px] text-blue-100">{bugReports.length || testActions.length} report</span>
                    </div>
                    <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-2">
                        {testActions.length ? testActions.map((action, index) => (
                            <div key={`${action.run_id}-${index}`} className="rounded-xl border border-blue-400/20 bg-blue-500/10 p-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                        <p className="mt-1 text-xs uppercase tracking-[0.16em] text-blue-200">{action.module} / run #{action.run_id}</p>
                                    </div>
                                    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.bug_report?.category || 'test'}</span>
                                </div>
                                {action.bug_report ? (
                                    <div className="mt-3 space-y-3">
                                        <div className="grid gap-2 sm:grid-cols-2">
                                            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                                <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Failed Step</div>
                                                <div className="mt-1 text-sm text-white">
                                                    #{action.bug_report.failed_step_order ?? '--'} / {action.bug_report.failed_action || 'step'}
                                                </div>
                                            </div>
                                            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                                <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Target</div>
                                                <div className="mt-1 truncate text-sm text-white">{action.bug_report.target}</div>
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Probable Cause</div>
                                            <p className="mt-1 text-sm leading-6 text-slate-300">{action.bug_report.probable_cause}</p>
                                        </div>
                                        <div>
                                            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Recommended Action</div>
                                            <p className="mt-1 text-sm leading-6 text-blue-100">{action.bug_report.recommendation}</p>
                                        </div>
                                        <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                                            Evidence: {action.bug_report.evidence.reason}
                                        </div>
                                    </div>
                                ) : (
                                    <p className="mt-2 text-sm leading-6 text-slate-300">{action.recommendation}</p>
                                )}
                            </div>
                        )) : (
                            <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                                Failed step oluşursa aksiyonlar burada görünür.
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex h-[420px] flex-col rounded-3xl border border-slate-800 bg-slate-950 p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-400">
                            <Activity className="h-4 w-4" />
                            Run History
                        </div>
                        <span className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-[11px] text-slate-300">{runs.length} runs</span>
                    </div>
                    <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-2">
                        {runs.length ? runs.map(run => (
                            <div key={run.id} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <h3 className="text-sm font-bold text-white">{run.test_case_title || run.module_name}</h3>
                                        <p className="mt-1 text-xs text-slate-500">run #{run.id} / {run.target}</p>
                                    </div>
                                    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] ${
                                        run.status === 'completed'
                                            ? 'border-green-400/30 bg-green-500/10 text-green-100'
                                            : 'border-red-400/30 bg-red-500/10 text-red-100'
                                    }`}>
                                        {run.status === 'completed' ? <CheckCircle2 className="mr-1 h-3 w-3" /> : <XCircle className="mr-1 h-3 w-3" />}
                                        {run.status}
                                    </span>
                                </div>
                                {run.failed_steps_count > 0 && (
                                    <p className="mt-2 text-sm text-red-200">{run.failed_steps_count} failed step</p>
                                )}
                            </div>
                        )) : (
                            <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                                Bu proje için run geçmişi yok.
                            </div>
                        )}
                    </div>
                </div>
            </section>

            {failedRuns.length > 0 && (
                <section className="rounded-2xl border border-red-400/20 bg-red-500/10 p-5">
                    <div className="text-xs uppercase tracking-[0.2em] text-red-200">Execution Notes</div>
                    <p className="mt-2 text-sm leading-6 text-red-100">
                        Bu projede failed run var. Öncelik sırası: failed step kanıtı, aynı hedefteki security riski ve correlation kartları birlikte incelenmeli.
                    </p>
                </section>
            )}
        </div>
    );
}
