
import { useState } from 'react';
import { Settings, User, Bell, Key, Monitor, Save } from 'lucide-react';

export function SettingsPage() {
    const [activeTab, setActiveTab] = useState('general');

    const renderTabContent = () => {
        switch (activeTab) {
            case 'general':
                return (
                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">Project Name</label>
                            <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500" defaultValue="VisionQA Platform" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">Workspace URL</label>
                            <div className="flex">
                                <span className="bg-slate-800 border border-r-0 border-slate-700 rounded-l-lg px-4 py-2 text-slate-400">visionqa.com/</span>
                                <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded-r-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500" defaultValue="enterprise-demo" />
                            </div>
                        </div>
                    </div>
                );
            case 'profile':
                return (
                    <div className="space-y-6">
                        <div className="flex items-center gap-4">
                            <div className="h-20 w-20 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 border-2 border-slate-700">
                                <User className="h-10 w-10" />
                            </div>
                            <div>
                                <button className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg text-sm font-medium border border-slate-700">
                                    Change Avatar
                                </button>
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">Full Name</label>
                            <input type="text" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white" defaultValue="Admin User" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">Email Address</label>
                            <input type="email" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white" defaultValue="admin@visionqa.com" />
                        </div>
                    </div>
                );
            case 'notifications':
                return (
                    <div className="space-y-4">
                        <div className="flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800">
                            <div>
                                <h3 className="text-white font-medium">Email Notifications</h3>
                                <p className="text-sm text-slate-500">Receive daily summaries of test runs</p>
                            </div>
                            <div className="relative inline-block w-12 mr-2 align-middle select-none transition duration-200 ease-in">
                                <input type="checkbox" name="toggle" id="toggle1" className="bg-green-500 absolute block w-6 h-6 rounded-full border-4 appearance-none cursor-pointer checked:right-0 checked:border-green-500" />
                                <label htmlFor="toggle1" className="block overflow-hidden h-6 rounded-full bg-slate-700 cursor-pointer"></label>
                            </div>
                        </div>
                        <div className="flex items-center justify-between p-4 bg-slate-900 rounded-lg border border-slate-800">
                            <div>
                                <h3 className="text-white font-medium">Slack Integration</h3>
                                <p className="text-sm text-slate-500">Post failed tests to #visionqa-alerts</p>
                            </div>
                            <button className="text-blue-400 text-sm hover:underline">Connect Slack</button>
                        </div>
                    </div>
                );
            case 'api':
                return (
                    <div className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">OpenAI API Key</label>
                            <div className="flex gap-2">
                                <input type="password" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white" defaultValue="sk-..........................." />
                                <button className="bg-slate-800 px-4 py-2 rounded-lg text-white border border-slate-700">Update</button>
                            </div>
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">Hugging Face Token</label>
                            <div className="flex gap-2">
                                <input type="password" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white" defaultValue="hf_..........................." />
                                <button className="bg-slate-800 px-4 py-2 rounded-lg text-white border border-slate-700">Update</button>
                            </div>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <Settings className="h-8 w-8 text-slate-400" />
                Settings
            </h1>

            <div className="flex flex-col md:flex-row gap-8">
                {/* Sidebar Navigation */}
                <div className="w-full md:w-64 space-y-1">
                    {[
                        { id: 'general', name: 'General', icon: Monitor },
                        { id: 'profile', name: 'Profile', icon: User },
                        { id: 'notifications', name: 'Notifications', icon: Bell },
                        { id: 'api', name: 'API Keys', icon: Key },
                    ].map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors
                                ${activeTab === tab.id
                                    ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                                }`}
                        >
                            <tab.icon className="h-5 w-5" />
                            {tab.name}
                        </button>
                    ))}
                </div>

                {/* Content Area */}
                <div className="flex-1 bg-slate-950 border border-slate-800 rounded-xl p-8 min-h-[500px]">
                    <h2 className="text-xl font-bold text-white mb-6 capitalize">{activeTab} Settings</h2>
                    {renderTabContent()}

                    <div className="mt-8 pt-6 border-t border-slate-800 flex justify-end">
                        <button className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg text-sm font-medium flex items-center gap-2">
                            <Save className="h-4 w-4" />
                            Save Changes
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default SettingsPage;
