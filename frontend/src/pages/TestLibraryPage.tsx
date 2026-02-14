
import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { api, TestCase } from '../services/api';
import { Trash2, Plus, Play } from 'lucide-react';

const TestLibraryPage: React.FC = () => {
    const { projectId } = useParams<{ projectId: string }>();
    const [cases, setCases] = React.useState<TestCase[]>([]);
    const [loading, setLoading] = React.useState(false);
    const [runningCaseId, setRunningCaseId] = React.useState<number | null>(null);

    // Initial Load (Eğer API'de getCases endpointi olsaydı useQuery kullanırdık, şimdilik generate'den gelen data var)
    // TODO: getProjectCases endpointi eklenmeli. Şimdilik generate basılınca geliyor.

    // AI Generate Mutation
    const generateMutation = useMutation({
        mutationFn: () => api.generateCases(Number(projectId)),
        onMutate: () => setLoading(true),
        onSuccess: (data) => {
            setCases(data);
            setLoading(false);
        },
        onError: (error) => {
            alert("AI Error: " + error);
            setLoading(false);
        }
    });

    // Run Test Mutation
    const runMutation = useMutation({
        mutationFn: (caseId: number) => api.runTestCase(caseId),
        onMutate: (id) => setRunningCaseId(id),
        onSuccess: (data) => {
            setRunningCaseId(null);
            alert(`Test Completed! Status: ${data.status}`);
        },
        onError: (error) => {
            setRunningCaseId(null);
            alert("Execution Error: " + error);
        }
    });

    // Delete Mutation
    const deleteMutation = useMutation({
        mutationFn: (caseId: number) => api.deleteTestCase(caseId),
        onSuccess: (_, deletedId) => {
            setCases(prev => prev.filter(c => c.id !== deletedId));
        },
        onError: (error) => alert("Delete Error: " + error)
    });

    // Create Manual Case
    const handleCreateManual = async () => {
        const title = window.prompt("Enter Test Case Title:");
        if (!title) return;

        const description = window.prompt("Enter Description:", "Manual test case") || "";

        try {
            const newCaseData = {
                title,
                description,
                priority: "medium",
                steps: [] // Empty steps initially
            };
            const result = await api.createTestCase(Number(projectId), newCaseData);
            // Sunucudan gelen ID ile listeye ekle (basitçe)
            // Gerçekte refetch yapmak daha iyidir ama get endpointi henüz yok.
            // result.id var, diğerlerini elle dolduralım:
            const newCase: TestCase = { ...newCaseData, id: (result as any).id, project_id: Number(projectId), status: 'draft', steps: [] };
            setCases(prev => [newCase, ...prev]);
        } catch (e) {
            alert("Create Error: " + e);
        }
    };

    return (
        <div className="p-8">
            <header className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Test Library</h1>
                    <p className="text-gray-500 mt-2">Manage and generate test cases for Project #{projectId}</p>
                </div>
                <div className="flex space-x-4">
                    <Link to="/projects" className="px-4 py-2 text-gray-600 bg-gray-100 rounded hover:bg-gray-200">
                        Back to Projects
                    </Link>

                    <button
                        onClick={handleCreateManual}
                        className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 flex items-center gap-2"
                    >
                        <Plus className="h-4 w-4" />
                        Manual Case
                    </button>

                    <button
                        onClick={() => generateMutation.mutate()}
                        disabled={loading}
                        className={`px-6 py-2 rounded-lg font-medium text-white transition-all flex items-center gap-2
                            ${loading
                                ? 'bg-purple-400 cursor-not-allowed'
                                : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 shadow-lg hover:shadow-xl'
                            }
                        `}
                    >
                        {loading ? "Generating..." : "✨ Generate with AI"}
                    </button>
                </div>
            </header>

            {/* Test Case List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                {cases.length === 0 ? (
                    <div className="p-12 text-center text-gray-500">
                        <div className="text-6xl mb-4">🧪</div>
                        <h3 className="text-xl font-medium text-gray-700">No Test Cases Yet</h3>
                        <p className="mt-2">Click "Generate with AI" or add a manual case.</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {cases.map((testCase) => (
                            <div key={testCase.id} className="p-6 hover:bg-gray-50 transition-colors group">
                                <div className="flex justify-between items-start">
                                    {/* Sol Taraf */}
                                    <div>
                                        <div className="flex items-center space-x-3">
                                            <span className={`px-2 py-1 text-xs font-bold uppercase rounded 
                                                ${testCase.priority === 'high' || testCase.priority === 'critical' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}
                                            `}>
                                                {testCase.priority}
                                            </span>
                                            <h3 className="text-lg font-semibold text-gray-900">{testCase.title}</h3>
                                        </div>
                                        <p className="text-gray-600 mt-1">{testCase.description}</p>
                                    </div>

                                    {/* Sağ Taraf Actions */}
                                    <div className="flex items-center space-x-3">
                                        <span className="text-xs font-mono text-gray-400">ID: {testCase.id}</span>

                                        {/* Run Button */}
                                        <button
                                            onClick={() => runMutation.mutate(testCase.id)}
                                            disabled={runningCaseId === testCase.id}
                                            className={`flex items-center px-4 py-2 rounded-md text-sm font-bold transition-all
                                                ${runningCaseId === testCase.id
                                                    ? 'bg-yellow-100 text-yellow-700 cursor-wait'
                                                    : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
                                                }
                                            `}
                                        >
                                            {runningCaseId === testCase.id ? (
                                                <>Running...</>
                                            ) : (
                                                <><Play className="h-4 w-4 mr-2" /> Run Test</>
                                            )}
                                        </button>

                                        {/* Delete Button */}
                                        <button
                                            onClick={() => {
                                                if (window.confirm("Are you sure?")) deleteMutation.mutate(testCase.id);
                                            }}
                                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors"
                                            title="Delete Case"
                                        >
                                            <Trash2 className="h-5 w-5" />
                                        </button>
                                    </div>
                                </div>

                                {/* Steps */}
                                <div className="mt-4 bg-gray-50 rounded-lg p-4 border border-gray-200">
                                    <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Test Steps</h4>
                                    {testCase.steps && testCase.steps.length > 0 ? (
                                        <ul className="space-y-2">
                                            {testCase.steps.map((step, index) => (
                                                <li key={index} className="flex items-start text-sm">
                                                    <span className="font-mono text-gray-400 mr-3">{index + 1}.</span>
                                                    <div className="flex-1">
                                                        <span className="font-bold text-gray-700 mr-2">[{step.action}]</span>
                                                        <span className="text-gray-800">{step.target}</span>
                                                        {step.value && <span className="ml-2 text-indigo-600">"{step.value}"</span>}
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <p className="text-sm text-gray-400 italic">No steps defined. (Edit to add steps)</p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default TestLibraryPage;
