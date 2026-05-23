import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
    Activity,
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    Download,
    ExternalLink,
    FileText,
    GitMerge,
    Loader2,
    ShieldAlert,
    XCircle,
} from 'lucide-react';
import { api, JiraChecklistItem, JiraDraftRequest, JiraTicketDraft, ProjectSummaryReport } from '@/services/api';

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

function claimStatusClass(status?: string) {
    switch (String(status || '').toLowerCase()) {
        case 'supported':
            return 'border-emerald-400/25 bg-emerald-500/10 text-emerald-100';
        case 'observed':
            return 'border-blue-400/25 bg-blue-500/10 text-blue-100';
        case 'pending':
            return 'border-amber-400/25 bg-amber-500/10 text-amber-100';
        default:
            return 'border-slate-700 bg-slate-900 text-slate-300';
    }
}

function moduleRoute(module: string, projectId?: string) {
    const routes: Record<string, string> = {
        autonomous: projectId ? `/projects/${projectId}/pages` : '/projects',
        bug_analysis: '/test-runs',
        security: '/security',
        accessibility: '/accessibility',
        uiux: '/uiux',
        dataset: '/dataset',
        api: '/lab',
        database: '/database',
        performance: '/performance',
        mobile: '/mobile',
    };
    return routes[module] || '/projects';
}

const reportScrollClass = 'report-scrollbar';

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
    const [draftLoadingKey, setDraftLoadingKey] = useState<string | null>(null);
    const [createdDraft, setCreatedDraft] = useState<JiraTicketDraft | null>(null);
    const [checklistSavingIndex, setChecklistSavingIndex] = useState<number | null>(null);
    const [showAllJiraDrafts, setShowAllJiraDrafts] = useState(false);
    const [jiraDraftStatusFilter, setJiraDraftStatusFilter] = useState<'all' | 'partial' | 'completed'>('all');
    const [jiraDraftModuleFilter, setJiraDraftModuleFilter] = useState('all');
    const { data: report, isLoading, error } = useQuery({
        queryKey: ['projectFullReport', projectId],
        queryFn: () => api.getProjectSummaryReport(Number(projectId)),
        enabled: Boolean(projectId),
        refetchInterval: 15000,
    });
    const { data: jiraDrafts = [], refetch: refetchJiraDrafts } = useQuery({
        queryKey: ['projectJiraDrafts', projectId],
        queryFn: () => api.getProjectJiraDrafts(Number(projectId), 12),
        enabled: Boolean(projectId),
        refetchInterval: 15000,
    });

    const securityActions = report?.security.priority_actions ?? [];
    const testActions = report?.tests.priority_actions ?? [];
    const bugReports = report?.tests.bug_reports ?? [];
    const apiActions = report?.api?.priority_actions ?? [];
    const dbActions = report?.database?.priority_actions ?? [];
    const performanceActions = report?.performance?.priority_actions ?? [];
    const uiuxActions = report?.uiux?.priority_actions ?? [];
    const accessibilityActions = report?.accessibility?.priority_actions ?? [];
    const mobileActions = report?.mobile?.priority_actions ?? [];
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
            interpretation: 'Run geçmişi otonom test çıktılarıyla rapora bağlandı.',
            recommended_action: 'Failed run varsa Bug Analysis kartını incele.',
            evidence_level: report.summary.failed_runs > 0 ? 'actionable' : 'observed',
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
            interpretation: 'Failed step logları bug raporu olarak özetlenir.',
            recommended_action: 'Kategori ve hedef selector üzerinden düzeltme planı çıkar.',
            evidence_level: (report.summary.bug_reports ?? bugReports.length) > 0 ? 'actionable' : 'none',
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
            interpretation: 'Security risk sinyalleri proje raporuna taşındı.',
            recommended_action: 'Priority Security Actions listesini önceliklendir.',
            evidence_level: report.summary.high_security_risks + report.summary.medium_security_risks > 0 ? 'actionable' : 'observed',
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
            interpretation: 'Aynı hedefteki modül sinyalleri birlikte yorumlanır.',
            recommended_action: 'Correlation kartlarını API, DB, security ve failed test kanıtlarıyla kontrol et.',
            evidence_level: report.summary.correlations > 0 ? 'actionable' : 'observed',
            latest: [],
        },
    ] : [];
    const moduleItems = report?.module_breakdown?.items?.length
        ? report.module_breakdown.items
        : fallbackModuleItems;
    const executiveSummary = report?.executive_summary;
    const evidenceMatrix = report?.evidence_matrix;
    const paperAlignment = report?.paper_alignment;
    const generatedAt = report
        ? new Date(report.generated_at).toLocaleString('tr-TR', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
        })
        : '';

    const createJiraDraft = async (key: string, draft: JiraDraftRequest) => {
        if (!projectId) return;
        const existingDraft = jiraDrafts.find((item) => (
            item.source_module === draft.source_module
            && item.source_type === draft.source_type
            && (item.source_ref || '') === (draft.source_ref || '')
            && item.title === draft.title
        ));
        if (existingDraft) {
            setCreatedDraft(existingDraft);
            return;
        }
        setDraftLoadingKey(key);
        try {
            const created = await api.createProjectJiraDraft(Number(projectId), draft);
            setCreatedDraft(created);
            refetchJiraDrafts();
        } finally {
            setDraftLoadingKey(null);
        }
    };

    const jiraButton = (key: string, draft: JiraDraftRequest) => (
        <button
            type="button"
            onClick={() => createJiraDraft(key, draft)}
            disabled={draftLoadingKey === key}
            className="inline-flex items-center gap-2 rounded-lg border border-blue-400/25 bg-blue-500/10 px-3 py-1.5 text-[11px] font-black uppercase tracking-[0.12em] text-blue-100 transition hover:border-blue-300/50 disabled:cursor-wait disabled:opacity-60"
        >
            {draftLoadingKey === key ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
            Jira Draft
        </button>
    );

    const acceptanceCriteria = (createdDraft?.payload?.acceptance_criteria as JiraChecklistItem[] | undefined) ?? [];
    const jiraDraftChecklistStats = jiraDrafts.reduce(
        (stats, draft) => {
            const criteria = (draft.payload?.acceptance_criteria as JiraChecklistItem[] | undefined) ?? [];
            stats.total += criteria.length;
            stats.done += criteria.filter((item) => item.done).length;
            if (criteria.some((item) => item.done) && criteria.some((item) => !item.done)) {
                stats.partial += 1;
            }
            if (criteria.length > 0 && criteria.every((item) => item.done)) {
                stats.completed += 1;
            }
            return stats;
        },
        { total: 0, done: 0, partial: 0, completed: 0 },
    );
    const jiraDraftModules = Array.from(new Set(jiraDrafts.map((draft) => draft.source_module))).sort();
    const filteredJiraDrafts = jiraDrafts.filter((draft) => {
        const criteria = (draft.payload?.acceptance_criteria as JiraChecklistItem[] | undefined) ?? [];
        const doneCount = criteria.filter((item) => item.done).length;
        const isCompleted = criteria.length > 0 && doneCount === criteria.length;
        const isPartial = doneCount > 0 && doneCount < criteria.length;
        const statusMatches = (
            jiraDraftStatusFilter === 'all'
            || (jiraDraftStatusFilter === 'partial' && isPartial)
            || (jiraDraftStatusFilter === 'completed' && isCompleted)
        );
        const moduleMatches = jiraDraftModuleFilter === 'all' || draft.source_module === jiraDraftModuleFilter;
        return statusMatches && moduleMatches;
    });
    const visibleJiraDrafts = showAllJiraDrafts ? filteredJiraDrafts : filteredJiraDrafts.slice(0, 3);

    const toggleAcceptanceCriteria = async (index: number) => {
        if (!createdDraft) return;
        const nextItems = acceptanceCriteria.map((item, itemIndex) => (
            itemIndex === index ? { ...item, done: !item.done } : item
        ));
        setChecklistSavingIndex(index);
        try {
            const updated = await api.updateJiraDraftChecklist(createdDraft.id, nextItems);
            setCreatedDraft(updated);
            refetchJiraDrafts();
        } finally {
            setChecklistSavingIndex(null);
        }
    };

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
            {createdDraft && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
                    <div className="w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-100 text-slate-950 shadow-2xl shadow-black/40">
                        <div className="flex items-start justify-between gap-4 border-b border-slate-300 bg-white px-6 py-5">
                            <div>
                                <div className="text-xs font-bold uppercase tracking-[0.18em] text-blue-700">Jira Issue Draft</div>
                                <h2 className="mt-2 text-2xl font-black text-slate-950">{createdDraft.title}</h2>
                                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-500">
                                    <span className="font-mono font-bold text-blue-700">{createdDraft.ticket_key}</span>
                                    <span>created from Final Report</span>
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={() => setCreatedDraft(null)}
                                className="rounded-xl border border-slate-300 bg-white p-2 text-slate-500 transition hover:border-slate-500 hover:text-slate-900"
                            >
                                <XCircle className="h-5 w-5" />
                            </button>
                        </div>
                        <div className="grid gap-0 lg:grid-cols-[1fr_280px]">
                            <div className="space-y-5 bg-white px-6 py-5">
                                <section>
                                    <div className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Description</div>
                                    <p className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-7 text-slate-700">
                                        {createdDraft.description}
                                    </p>
                                </section>
                                <section className="grid gap-4 md:grid-cols-2">
                                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                        <div className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Evidence</div>
                                        <p className="mt-2 text-sm leading-6 text-slate-800">
                                            {String(createdDraft.payload?.evidence || 'Evidence bu draft icinde kayitli degil.')}
                                        </p>
                                    </div>
                                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                        <div className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Recommended Action</div>
                                        <p className="mt-2 text-sm leading-6 text-slate-800">
                                            {String(createdDraft.payload?.recommendation || 'Aksiyon onerisi bu draft icinde kayitli degil.')}
                                        </p>
                                    </div>
                                </section>
                                <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                                    <div className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Acceptance Criteria</div>
                                    <div className="mt-3 space-y-2 text-sm text-slate-800">
                                        {acceptanceCriteria.map((item, index) => (
                                            <label key={`${item.text}-${index}`} className="flex cursor-pointer items-start gap-3">
                                                <input
                                                    type="checkbox"
                                                    checked={Boolean(item.done)}
                                                    onChange={() => toggleAcceptanceCriteria(index)}
                                                    disabled={checklistSavingIndex === index}
                                                    className="mt-1 h-4 w-4 rounded border-slate-300"
                                                />
                                                <span className={item.done ? 'text-slate-400 line-through' : 'text-slate-800'}>
                                                    {item.text}
                                                    {checklistSavingIndex === index && (
                                                        <Loader2 className="ml-2 inline h-3.5 w-3.5 animate-spin text-blue-600" />
                                                    )}
                                                </span>
                                            </label>
                                        ))}
                                    </div>
                                </section>
                            </div>
                            <aside className="space-y-4 border-l border-slate-300 bg-slate-50 px-5 py-5">
                                <div className="rounded-xl border border-slate-200 bg-white p-4">
                                    <div className="text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">Status</div>
                                    <div className="mt-2 inline-flex rounded-full bg-slate-200 px-3 py-1 text-xs font-black uppercase text-slate-700">
                                        {createdDraft.status}
                                    </div>
                                </div>
                                <div className="rounded-xl border border-slate-200 bg-white p-4">
                                    <div className="text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">Priority</div>
                                    <div className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-black uppercase ${
                                        createdDraft.priority === 'high' || createdDraft.priority === 'critical'
                                            ? 'bg-red-100 text-red-700'
                                            : createdDraft.priority === 'medium'
                                                ? 'bg-amber-100 text-amber-700'
                                                : 'bg-blue-100 text-blue-700'
                                    }`}>
                                        {createdDraft.priority}
                                    </div>
                                </div>
                                <div className="rounded-xl border border-slate-200 bg-white p-4">
                                    <div className="text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">Module</div>
                                    <div className="mt-2 text-sm font-bold text-slate-900">{createdDraft.source_module}</div>
                                </div>
                                <div className="rounded-xl border border-slate-200 bg-white p-4">
                                    <div className="text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">Source</div>
                                    <div className="mt-2 text-sm font-bold text-slate-900">{createdDraft.source_type}</div>
                                    {createdDraft.source_ref && (
                                        <div className="mt-1 break-all font-mono text-xs text-slate-500">{createdDraft.source_ref}</div>
                                    )}
                                </div>
                                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                                    <div className="text-[11px] font-black uppercase tracking-[0.16em] text-blue-700">Stored In VisionQA</div>
                                    <p className="mt-2 text-xs leading-5 text-blue-900">
                                        Bu kayıt DB'de saklanan Jira taslağıdır. Gerçek Jira bağlantısı eklenince aynı içerik dış sisteme gönderilebilir.
                                    </p>
                                </div>
                            </aside>
                        </div>
                    </div>
                </div>
            )}
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

            {executiveSummary && (
                <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
                    <div className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-blue-300">
                                    <FileText className="h-4 w-4" />
                                    Executive Summary
                                </div>
                                <h2 className="mt-3 text-2xl font-black text-white">{executiveSummary.title}</h2>
                            </div>
                            <span className={`rounded-full border px-3 py-1.5 text-xs font-bold uppercase ${severityClass(executiveSummary.risk_level)}`}>
                                {executiveSummary.risk_level} risk
                            </span>
                        </div>
                        <p className="mt-4 text-sm leading-7 text-slate-300">{executiveSummary.narrative}</p>
                        <div className="mt-4 grid gap-3 lg:grid-cols-2">
                            <div className="rounded-2xl border border-red-400/15 bg-red-500/5 p-4">
                                <div className="text-[11px] uppercase tracking-[0.18em] text-red-200">Top Risks</div>
                                <div className="mt-3 space-y-2">
                                    {executiveSummary.top_risks.map((risk) => (
                                        <p key={risk} className="text-sm leading-6 text-slate-300">{risk}</p>
                                    ))}
                                </div>
                            </div>
                            <div className="rounded-2xl border border-cyan-400/15 bg-cyan-500/5 p-4">
                                <div className="text-[11px] uppercase tracking-[0.18em] text-cyan-200">Next Actions</div>
                                <div className="mt-3 space-y-2">
                                    {executiveSummary.next_actions.map((action) => (
                                        <p key={action} className="text-sm leading-6 text-slate-300">{action}</p>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-cyan-300">
                            <Activity className="h-4 w-4" />
                            Evidence Matrix
                        </div>
                        <div className="mt-4 grid grid-cols-2 gap-3">
                            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                                <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Coverage</div>
                                <div className="mt-2 text-2xl font-black text-white">{evidenceMatrix?.coverage.evidence_coverage_percent ?? 0}%</div>
                            </div>
                            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
                                <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Connected</div>
                                <div className="mt-2 text-2xl font-black text-white">
                                    {evidenceMatrix?.coverage.connected_modules ?? 0}/{evidenceMatrix?.coverage.total_modules ?? moduleItems.length}
                                </div>
                            </div>
                        </div>
                        <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Paper Evidence</div>
                            <div className="mt-3 flex flex-wrap gap-2">
                                {(evidenceMatrix?.paper_evidence ?? []).map((item) => (
                                    <span key={item} className="rounded-lg border border-cyan-400/20 bg-cyan-500/10 px-2.5 py-1 text-[11px] font-bold text-cyan-100">
                                        {item}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                </section>
            )}

            {paperAlignment && (
                <section className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-violet-300">
                            <GitMerge className="h-4 w-4" />
                            Paper Alignment
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-2.5 py-1 text-[11px] font-bold uppercase text-cyan-100">
                                {paperAlignment.status.replace(/_/g, ' ')}
                            </span>
                            <span className="rounded-full border border-amber-400/20 bg-amber-500/10 px-2.5 py-1 text-[11px] font-bold uppercase text-amber-100">
                                Benchmark: {paperAlignment.benchmark_status.replace(/_/g, ' ')}
                            </span>
                        </div>
                    </div>
                    <div className="mt-4 grid gap-3 lg:grid-cols-2">
                        {paperAlignment.claims.map((claim) => (
                            <div key={claim.claim} className={`rounded-2xl border p-4 ${claimStatusClass(claim.status)}`}>
                                <div className="flex items-start justify-between gap-3">
                                    <h3 className="text-sm font-black text-white">{claim.claim}</h3>
                                    <span className="shrink-0 rounded-full border border-white/10 bg-slate-950/60 px-2.5 py-1 text-[10px] font-bold uppercase">
                                        {claim.status}
                                    </span>
                                </div>
                                <p className="mt-3 text-sm leading-6 text-slate-300">{claim.evidence}</p>
                            </div>
                        ))}
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-[0.8fr_1.2fr]">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Evidence Counts</div>
                            <div className="mt-3 grid grid-cols-2 gap-2">
                                {Object.entries(paperAlignment.evidence_counts).map(([label, value]) => (
                                    <div key={label} className="rounded-xl border border-white/10 bg-slate-950/60 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.14em] text-slate-500">{label.replace(/_/g, ' ')}</div>
                                        <div className="mt-1 text-lg font-black text-white">{value}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                            <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Next Research Steps</div>
                            <div className="mt-3 space-y-2">
                                {paperAlignment.next_research_steps.map((step) => (
                                    <p key={step} className="text-sm leading-6 text-slate-300">{step}</p>
                                ))}
                            </div>
                        </div>
                    </div>
                </section>
            )}

            <section className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-blue-300">
                            <FileText className="h-4 w-4" />
                            Jira Drafts
                        </div>
                        <p className="mt-2 text-sm text-slate-500">
                            Final Report aksiyonlarından oluşturulan task taslakları burada kısa özet olarak tutulur.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-blue-400/20 bg-blue-500/10 px-3 py-1.5 text-xs font-bold text-blue-100">
                            {jiraDrafts.length} draft
                        </span>
                        <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-3 py-1.5 text-xs font-bold text-emerald-100">
                            {jiraDraftChecklistStats.done}/{jiraDraftChecklistStats.total || 0} checklist
                        </span>
                        {filteredJiraDrafts.length > 3 && (
                            <button
                                type="button"
                                onClick={() => setShowAllJiraDrafts((value) => !value)}
                                className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-bold text-slate-200 transition hover:border-blue-400/40 hover:text-blue-100"
                            >
                                {showAllJiraDrafts ? 'Son 3 taslağı göster' : 'Tümünü göster'}
                            </button>
                        )}
                    </div>
                </div>
                {jiraDrafts.length > 0 && (
                    <div className="mt-4 flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-3 lg:flex-row lg:items-center lg:justify-between">
                        <div className="flex flex-wrap gap-2">
                            {(['all', 'partial', 'completed'] as const).map((filter) => (
                                <button
                                    key={filter}
                                    type="button"
                                    onClick={() => {
                                        setJiraDraftStatusFilter(filter);
                                        setShowAllJiraDrafts(false);
                                    }}
                                    className={`rounded-lg border px-3 py-2 text-xs font-black uppercase tracking-[0.12em] transition ${
                                        jiraDraftStatusFilter === filter
                                            ? 'border-blue-300/50 bg-blue-500/20 text-blue-100'
                                            : 'border-slate-700 bg-slate-950/70 text-slate-400 hover:border-slate-500 hover:text-slate-200'
                                    }`}
                                >
                                    {filter}
                                </button>
                            ))}
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">Module</span>
                            <select
                                value={jiraDraftModuleFilter}
                                onChange={(event) => {
                                    setJiraDraftModuleFilter(event.target.value);
                                    setShowAllJiraDrafts(false);
                                }}
                                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-bold text-slate-200 outline-none transition focus:border-blue-400/60"
                            >
                                <option value="all">All modules</option>
                                {jiraDraftModules.map((module) => (
                                    <option key={module} value={module}>{module}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                )}
                {jiraDrafts.length > 0 && (
                    <div className="mt-4 grid gap-3 border-y border-slate-800 py-4 sm:grid-cols-3">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
                            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Open Drafts</div>
                            <div className="mt-1 text-xl font-black text-white">{jiraDrafts.length}</div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
                            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Partially Checked</div>
                            <div className="mt-1 text-xl font-black text-amber-100">{jiraDraftChecklistStats.partial}</div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
                            <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Completed Checklist</div>
                            <div className="mt-1 text-xl font-black text-emerald-100">{jiraDraftChecklistStats.completed}</div>
                        </div>
                    </div>
                )}
                <div className="mt-4 grid gap-3 lg:grid-cols-3">
                    {filteredJiraDrafts.length ? visibleJiraDrafts.map((draft) => {
                        const criteria = (draft.payload?.acceptance_criteria as JiraChecklistItem[] | undefined) ?? [];
                        const completed = criteria.filter((item) => item.done).length;
                        return (
                            <button
                                key={draft.id}
                                type="button"
                                onClick={() => setCreatedDraft(draft)}
                                className="rounded-2xl border border-blue-400/20 bg-blue-500/10 p-3 text-left transition hover:border-blue-300/50 hover:bg-blue-500/15"
                            >
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="font-mono text-[11px] font-black uppercase tracking-[0.14em] text-blue-200">{draft.ticket_key}</div>
                                        <h3 className="mt-1 line-clamp-1 text-sm font-black text-white">{draft.title}</h3>
                                    </div>
                                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] font-black uppercase ${
                                        draft.priority === 'high' || draft.priority === 'critical'
                                            ? 'bg-red-500/15 text-red-100'
                                            : draft.priority === 'medium'
                                                ? 'bg-amber-500/15 text-amber-100'
                                                : 'bg-blue-500/15 text-blue-100'
                                    }`}>
                                        {draft.priority}
                                    </span>
                                </div>
                                <p className="mt-2 line-clamp-1 text-xs leading-5 text-slate-300">{draft.description}</p>
                                <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-400">
                                    <span>{draft.source_module}</span>
                                    <span>{completed}/{criteria.length || 3} checklist</span>
                                </div>
                            </button>
                        );
                    }) : (
                        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                            {jiraDrafts.length
                                ? 'Bu filtreye uyan Jira Draft bulunmuyor.'
                                : 'Final Report aksiyonlarından Jira Draft oluşturunca kayıtlar burada görünecek.'}
                        </div>
                    )}
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
                        <Link
                            key={item.module}
                            to={moduleRoute(item.module, projectId)}
                            className={`group flex min-h-[295px] flex-col rounded-2xl border p-4 transition hover:-translate-y-0.5 hover:border-cyan-300/40 hover:shadow-lg hover:shadow-cyan-950/20 ${moduleStatusClass(item.status)}`}
                        >
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <h3 className="text-sm font-black text-white">{item.label}</h3>
                                    <p className="mt-1 text-[10px] uppercase tracking-[0.18em] opacity-70">{item.status}</p>
                                </div>
                                <div className="shrink-0 text-right">
                                    <div className="text-2xl font-black text-white">{item.score ?? '--'}</div>
                                    <div className="text-[10px] uppercase tracking-[0.16em] opacity-60">score</div>
                                </div>
                            </div>
                            <p className="mt-3 min-h-[44px] line-clamp-2 text-sm leading-6 text-slate-300">{item.summary}</p>
                            {(item.interpretation || item.recommended_action) && (
                                <div className="mt-3 min-h-[92px] space-y-2 rounded-xl border border-white/10 bg-slate-950/50 p-3">
                                    {item.interpretation && (
                                        <p className="line-clamp-2 text-xs leading-5 text-slate-300">{item.interpretation}</p>
                                    )}
                                    {item.recommended_action && (
                                        <p className="line-clamp-2 text-xs leading-5 text-cyan-100">{item.recommended_action}</p>
                                    )}
                                </div>
                            )}
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
                            <div className="mt-auto flex items-center justify-between gap-3 pt-4">
                                <span className="rounded-full border border-white/10 bg-slate-950/60 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] opacity-75">
                                    Evidence: {item.evidence_level ?? 'none'}
                                </span>
                                <span className="inline-flex items-center text-[10px] font-black uppercase tracking-[0.14em] text-cyan-200 opacity-0 transition group-hover:opacity-100">
                                    Open <ExternalLink className="ml-1.5 h-3 w-3" />
                                </span>
                            </div>
                        </Link>
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
                                    <div className="mt-1 text-white">{action.status_code ?? '--'}</div>
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
                            <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
                                <p className="text-sm leading-6 text-cyan-100">{action.recommendation}</p>
                                {jiraButton(`api-${index}`, {
                                    source_module: 'api',
                                    source_ref: String(action.api_record_id ?? index),
                                    title: action.title,
                                    description: action.summary,
                                    priority: action.severity,
                                    evidence: action.evidence,
                                    recommendation: action.recommendation,
                                    payload: action as unknown as Record<string, unknown>,
                                })}
                            </div>
                        </div>
                    )) : (
                        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                            API bulgusu oluşunca endpoint aksiyonları burada görünür.
                        </div>
                    )}
                </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-sky-300">
                        <Activity className="h-4 w-4" />
                        UI/UX Actions
                    </div>
                    <span className="rounded-full border border-sky-400/20 bg-sky-500/10 px-2.5 py-1 text-[11px] text-sky-100">{uiuxActions.length} action</span>
                </div>
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {uiuxActions.length ? uiuxActions.map((action, index) => (
                        <div key={`${action.uiux_record_id}-${action.category}-${index}`} className="rounded-2xl border border-sky-400/20 bg-sky-500/10 p-4">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                    <p className="mt-1 truncate text-xs uppercase tracking-[0.16em] text-sky-200">
                                        {action.category || 'uiux-signal'}
                                    </p>
                                    {(action.duplicate_count || 0) > 1 && (
                                        <p className="mt-1 text-xs text-sky-100/70">
                                            {action.duplicate_count} tekrar eden UI/UX bulgusu birleştirildi.
                                        </p>
                                    )}
                                </div>
                                <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.severity}</span>
                            </div>
                            <p className="mt-3 text-sm leading-6 text-slate-300">{action.summary}</p>
                            <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Score</div>
                                    <div className="mt-1 text-white">{action.score ?? '--'}</div>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Metric</div>
                                    <div className="mt-1 truncate text-white">{action.metric || action.category}</div>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Value</div>
                                    <div className="mt-1 text-white">{action.metric_value ?? '--'}</div>
                                </div>
                            </div>
                            <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                                Evidence: {action.evidence || 'UI/UX screenshot metric'}
                            </div>
                            <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
                                <p className="text-sm leading-6 text-sky-100">{action.recommendation}</p>
                                {jiraButton(`uiux-${index}`, {
                                    source_module: 'uiux',
                                    source_ref: String(action.uiux_record_id ?? index),
                                    title: action.title,
                                    description: action.summary,
                                    priority: action.severity,
                                    evidence: action.evidence,
                                    recommendation: action.recommendation,
                                    payload: action as unknown as Record<string, unknown>,
                                })}
                            </div>
                            {action.test_suggestion && (
                                <p className="mt-3 rounded-lg border border-violet-400/20 bg-violet-500/10 p-3 text-xs leading-5 text-violet-100">
                                    Test: {action.test_suggestion}
                                </p>
                            )}
                        </div>
                    )) : (
                        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                            UI/UX analizinde high/medium bulgu oluşunca aksiyonlar burada görünür.
                        </div>
                    )}
                </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-cyan-300">
                        <Activity className="h-4 w-4" />
                        Accessibility Actions
                    </div>
                    <span className="rounded-full border border-cyan-400/20 bg-cyan-500/10 px-2.5 py-1 text-[11px] text-cyan-100">{accessibilityActions.length} action</span>
                </div>
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {accessibilityActions.length ? accessibilityActions.map((action, index) => (
                        <div key={`${action.accessibility_record_id}-${action.category}-${index}`} className="rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-4">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                    <p className="mt-1 truncate text-xs uppercase tracking-[0.16em] text-cyan-200">
                                        {action.category || 'accessibility-signal'}
                                    </p>
                                    {(action.duplicate_count || 0) > 1 && (
                                        <p className="mt-1 text-xs text-cyan-100/70">
                                            {action.duplicate_count} tekrar eden accessibility bulgusu birleştirildi.
                                        </p>
                                    )}
                                </div>
                                <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.severity}</span>
                            </div>
                            <p className="mt-3 text-sm leading-6 text-slate-300">{action.summary}</p>
                            <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Impact</div>
                                    <div className="mt-1 text-white">{action.impact_score ?? '--'}</div>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Selector</div>
                                    <div className="mt-1 truncate text-white">{action.selector || '--'}</div>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">WCAG</div>
                                    <div className="mt-1 truncate text-white">{action.wcag_refs?.join(', ') || '--'}</div>
                                </div>
                            </div>
                            <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                                Evidence: {action.evidence || 'Accessibility evidence'}
                            </div>
                            <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
                                <p className="text-sm leading-6 text-cyan-100">{action.recommendation}</p>
                                {jiraButton(`accessibility-${index}`, {
                                    source_module: 'accessibility',
                                    source_ref: String(action.accessibility_record_id ?? index),
                                    title: action.title,
                                    description: action.summary,
                                    priority: action.severity,
                                    evidence: action.evidence,
                                    recommendation: action.recommendation,
                                    payload: action as unknown as Record<string, unknown>,
                                })}
                            </div>
                        </div>
                    )) : (
                        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                            Accessibility analizinde high/medium bulgu oluşunca aksiyonlar burada görünür.
                        </div>
                    )}
                </div>
            </section>

            <section className="rounded-3xl border border-slate-800 bg-slate-950 p-5">
                <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-teal-300">
                        <Activity className="h-4 w-4" />
                        Mobile Actions
                    </div>
                    <span className="rounded-full border border-teal-400/20 bg-teal-500/10 px-2.5 py-1 text-[11px] text-teal-100">{mobileActions.length} action</span>
                </div>
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {mobileActions.length ? mobileActions.map((action, index) => (
                        <div key={`${action.mobile_record_id}-${action.category}-${index}`} className="rounded-2xl border border-teal-400/20 bg-teal-500/10 p-4">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                    <p className="mt-1 truncate text-xs uppercase tracking-[0.16em] text-teal-200">
                                        {action.platform || 'mobile'} / {action.screen_type || action.category}
                                    </p>
                                    {(action.duplicate_count || 0) > 1 && (
                                        <p className="mt-1 text-xs text-teal-100/70">
                                            {action.duplicate_count} tekrar eden mobil bulgu birleştirildi.
                                        </p>
                                    )}
                                </div>
                                <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.severity}</span>
                            </div>
                            <p className="mt-3 text-sm leading-6 text-slate-300">{action.summary}</p>
                            <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Score</div>
                                    <div className="mt-1 text-white">{action.score ?? '--'}</div>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Friction</div>
                                    <div className="mt-1 text-white">{action.task_completion_friction ?? '--'}</div>
                                </div>
                                <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                    <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Category</div>
                                    <div className="mt-1 truncate text-white">{action.category}</div>
                                </div>
                            </div>
                            <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                                Evidence: {action.evidence || 'Mobile evidence'}
                            </div>
                            <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
                                <p className="text-sm leading-6 text-teal-100">{action.recommendation}</p>
                                {jiraButton(`mobile-${index}`, {
                                    source_module: 'mobile',
                                    source_ref: String(action.mobile_record_id ?? index),
                                    title: action.title,
                                    description: action.summary,
                                    priority: action.severity,
                                    evidence: action.evidence,
                                    recommendation: action.recommendation,
                                    payload: action as unknown as Record<string, unknown>,
                                })}
                            </div>
                            {action.cross_platform_parity_summary && (
                                <p className="mt-3 rounded-lg border border-cyan-400/20 bg-cyan-500/10 p-3 text-xs leading-5 text-cyan-100">
                                    {action.cross_platform_parity_summary}
                                </p>
                            )}
                        </div>
                    )) : (
                        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                            Mobil analizde high/medium bulgu oluşunca aksiyonlar burada görünür.
                        </div>
                    )}
                </div>
            </section>

            <section className="grid gap-5 xl:grid-cols-2">
                <div className="flex h-[420px] flex-col rounded-3xl border border-slate-800 bg-slate-950 p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-violet-300">
                            <Activity className="h-4 w-4" />
                            Database Quality Actions
                        </div>
                        <span className="rounded-full border border-violet-400/20 bg-violet-500/10 px-2.5 py-1 text-[11px] text-violet-100">{dbActions.length} action</span>
                    </div>
                    <div className={`mt-4 flex-1 space-y-3 overflow-y-auto pr-2 ${reportScrollClass}`}>
                        {dbActions.length ? dbActions.map((action, index) => (
                            <div key={`${action.db_record_id}-${action.category}-${index}`} className="rounded-xl border border-violet-400/20 bg-violet-500/10 p-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                        <p className="mt-1 truncate text-xs uppercase tracking-[0.16em] text-violet-200">
                                            {action.table_name || action.query || 'database signal'}
                                        </p>
                                        {(action.duplicate_count || 0) > 1 && (
                                            <p className="mt-1 text-xs text-violet-100/70">
                                                {action.duplicate_count} tekrar eden kayıt birleştirildi.
                                            </p>
                                        )}
                                    </div>
                                    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.category}</span>
                                </div>
                                <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-300">{action.summary}</p>
                                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Score</div>
                                        <div className="mt-1 text-white">{action.score ?? '--'}</div>
                                    </div>
                                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Columns</div>
                                        <div className="mt-1 text-white">{action.detected_columns?.length ?? 0}</div>
                                    </div>
                                </div>
                                <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                                    Evidence: {action.evidence || 'DB evidence'}
                                </div>
                                <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
                                    <p className="text-sm leading-6 text-violet-100">{action.recommendation}</p>
                                    {jiraButton(`db-${index}`, {
                                        source_module: 'database',
                                        source_ref: String(action.db_record_id ?? index),
                                        title: action.title,
                                        description: action.summary,
                                        priority: action.severity,
                                        evidence: action.evidence,
                                        recommendation: action.recommendation,
                                        payload: action as unknown as Record<string, unknown>,
                                    })}
                                </div>
                            </div>
                        )) : (
                            <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                                DB kalite bulgusu oluşunca aksiyonlar burada görünür.
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex h-[420px] flex-col rounded-3xl border border-slate-800 bg-slate-950 p-5">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-emerald-300">
                            <Activity className="h-4 w-4" />
                            Performance Actions
                        </div>
                        <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-100">{performanceActions.length} action</span>
                    </div>
                    <div className={`mt-4 flex-1 space-y-3 overflow-y-auto pr-2 ${reportScrollClass}`}>
                        {performanceActions.length ? performanceActions.map((action, index) => (
                            <div key={`${action.performance_record_id}-${action.category}-${index}`} className="rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                        <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                        <p className="mt-1 truncate text-xs uppercase tracking-[0.16em] text-emerald-200">{action.target || 'performance target'}</p>
                                        {(action.duplicate_count || 0) > 1 && (
                                            <p className="mt-1 text-xs text-emerald-100/70">
                                                {action.duplicate_count} tekrar eden kayıt birleştirildi.
                                            </p>
                                        )}
                                    </div>
                                    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.category}</span>
                                </div>
                                <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-300">{action.summary}</p>
                                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Score</div>
                                        <div className="mt-1 text-white">{action.score ?? '--'}</div>
                                    </div>
                                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Grade</div>
                                        <div className="mt-1 text-white">{action.grade ?? '--'}</div>
                                    </div>
                                    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
                                        <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">API ms</div>
                                        <div className="mt-1 text-white">{Math.round(Number(action.api_duration_ms || 0)) || '--'}</div>
                                    </div>
                                </div>
                                <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-400">
                                    Evidence: {action.evidence || 'Performance evidence'}
                                </div>
                                <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
                                    <p className="text-sm leading-6 text-emerald-100">{action.recommendation}</p>
                                    {jiraButton(`performance-${index}`, {
                                        source_module: 'performance',
                                        source_ref: String(action.performance_record_id ?? index),
                                        title: action.title,
                                        description: action.summary,
                                        priority: action.severity,
                                        evidence: action.evidence,
                                        recommendation: action.recommendation,
                                        payload: action as unknown as Record<string, unknown>,
                                    })}
                                </div>
                            </div>
                        )) : (
                            <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
                                Performance bulgusu oluşunca aksiyonlar burada görünür.
                            </div>
                        )}
                    </div>
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
                    <div className={`mt-4 flex-1 space-y-3 overflow-y-auto pr-2 ${reportScrollClass}`}>
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
                                <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
                                    <p className="text-sm leading-6 text-slate-300">{item.recommendation}</p>
                                    {jiraButton(`correlation-${index}`, {
                                        source_module: 'correlation',
                                        source_ref: item.target,
                                        title: item.title,
                                        description: item.recommendation,
                                        priority: item.severity,
                                        evidence: item.target,
                                        recommendation: item.recommendation,
                                        payload: item as unknown as Record<string, unknown>,
                                    })}
                                </div>
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
                    <div className={`mt-4 flex-1 space-y-3 overflow-y-auto pr-2 ${reportScrollClass}`}>
                        {securityActions.length ? securityActions.slice(0, 5).map((action, index) => (
                            <div key={`${action.title}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                                <div className="flex items-start justify-between gap-3">
                                    <h3 className="text-sm font-bold text-white">{action.title}</h3>
                                    <span className={`rounded-full border px-2.5 py-1 text-[11px] ${severityClass(action.severity)}`}>{action.severity}</span>
                                </div>
                                <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
                                    <p className="text-sm leading-6 text-slate-300">{action.recommendation}</p>
                                    {jiraButton(`security-${index}`, {
                                        source_module: 'security',
                                        source_ref: action.title,
                                        title: action.title,
                                        description: action.recommendation,
                                        priority: action.severity,
                                        evidence: action.category,
                                        recommendation: action.recommendation,
                                        payload: action as unknown as Record<string, unknown>,
                                    })}
                                </div>
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
                    <div className={`mt-4 flex-1 space-y-3 overflow-y-auto pr-2 ${reportScrollClass}`}>
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
                                            <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
                                                <p className="text-sm leading-6 text-blue-100">{action.bug_report.recommendation}</p>
                                                {jiraButton(`test-${index}`, {
                                                    source_module: 'bug_analysis',
                                                    source_ref: `run-${action.run_id}`,
                                                    title: action.title,
                                                    description: action.bug_report.probable_cause,
                                                    priority: action.severity,
                                                    evidence: action.bug_report.evidence.reason,
                                                    recommendation: action.bug_report.recommendation,
                                                    payload: action as unknown as Record<string, unknown>,
                                                })}
                                            </div>
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
                    <div className={`mt-4 flex-1 space-y-3 overflow-y-auto pr-2 ${reportScrollClass}`}>
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
