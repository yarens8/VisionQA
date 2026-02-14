
import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { api, TestCase } from '../services/api';

const TestLibraryPage: React.FC = () => {
    const { projectId } = useParams<{ projectId: string }>();
    const [cases, setCases] = React.useState<TestCase[]>([]);
    const [loading, setLoading] = React.useState(false);

    const [runningCaseId, setRunningCaseId] = React.useState<number | null>(null);

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

    return (
        <div className="p-8">
            <header className="flex justify-between items-center mb-8">
                {/* ... (Header aynı kalıyor) ... */}
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Test Library</h1>
                    <p className="text-gray-500 mt-2">Manage and generate test cases for Project #{projectId}</p>
                </div>
                <div className="flex space-x-4">
                    <Link to="/projects" className="px-4 py-2 text-gray-600 bg-gray-100 rounded hover:bg-gray-200">
                        Back to Projects
                    </Link>
                    <button
                        onClick={() => generateMutation.mutate()}
                        disabled={loading}
                        className={`px-6 py-2 rounded-lg font-medium text-white transition-all
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
                        {/* Empty state aynı */}
                        <div className="text-6xl mb-4">🧪</div>
                        <h3 className="text-xl font-medium text-gray-700">No Test Cases Yet</h3>
                        <p className="mt-2">Click the "Generate with AI" button to let VisionQA analyze your project.</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {cases.map((testCase) => (
                            <div key={testCase.id} className="p-6 hover:bg-gray-50 transition-colors">
                                <div className="flex justify-between items-start">
                                    {/* Sol Taraf (Başlık) */}
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

                                    {/* Sağ Taraf (Action Buttons) */}
                                    <div className="flex items-center space-x-3">
                                        <span className="text-xs font-mono text-gray-400">ID: {testCase.id || 'NEW'}</span>

                                        <button
                                            onClick={() => runMutation.mutate(testCase.id || 1)} // ID yoksa demo ID 1 kullan
                                            disabled={runningCaseId === testCase.id}
                                            className={`flex items-center px-4 py-2 rounded-md text-sm font-bold transition-all
                                                ${runningCaseId === testCase.id
                                                    ? 'bg-yellow-100 text-yellow-700 cursor-wait'
                                                    : 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
                                                }
                                            `}
                                        >
                                            {runningCaseId === testCase.id ? (
                                                <>
                                                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-yellow-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                    </svg>
                                                    Running...
                                                </>
                                            ) : (
                                                <>
                                                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                                    Run Test
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </div>

                                {/* Steps */}
                                <div className="mt-4 bg-gray-50 rounded-lg p-4 border border-gray-200">
                                    <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Test Steps</h4>
                                    <ul className="space-y-2">
                                        {testCase.steps && testCase.steps.map((step, index) => (
                                            <li key={index} className="flex items-start text-sm">
                                                <span className="font-mono text-gray-400 mr-3">{index + 1}.</span>
                                                <div className="flex-1">
                                                    <span className="font-bold text-gray-700 mr-2">[{step.action}]</span>
                                                    <span className="text-gray-800">{step.target}</span>
                                                    {step.value && <span className="ml-2 text-indigo-600">"{step.value}"</span>}
                                                    {step.expected_result && (
                                                        <div className="text-green-600 text-xs mt-1">
                                                            Expected: {step.expected_result}
                                                        </div>
                                                    )}
                                                </div>
                                            </li>
                                        ))}
                                    </ul>
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
