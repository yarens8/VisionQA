
import { NavLink } from "react-router-dom";
import {
    LayoutDashboard,
    Layers,
    Activity,
    Bug,
    Settings,
    FlaskConical,
    Database,
    ShieldCheck,
    Accessibility
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Projects", href: "/projects", icon: Layers },
    { name: "Test Runs", href: "/test-runs", icon: Activity },
    { name: "Findings", href: "/findings", icon: Bug },
]

const tools = [
    { name: "Test Lab", href: "/lab", icon: FlaskConical },
    { name: "Database", href: "/database", icon: Database },
    { name: "Security", href: "/security", icon: ShieldCheck },
    { name: "Accessibility", href: "/accessibility", icon: Accessibility },
]

export function Sidebar() {
    return (
        <div className="flex flex-col w-64 border-r border-slate-800 bg-slate-950 h-screen fixed left-0 top-0">

            {/* 🟢 Logo Area */}
            <div className="flex h-16 items-center px-6 border-b border-slate-800">
                <Activity className="h-6 w-6 text-blue-500 mr-2" />
                <span className="text-lg font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                    VisionQA
                </span>
            </div>

            {/* 🔵 Main Navigation */}
            <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">

                {/* Core Modules */}
                <div>
                    <h3 className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        Platform
                    </h3>
                    <nav className="space-y-1">
                        {navigation.map((item) => (
                            <NavLink
                                key={item.name}
                                to={item.href}
                                className={({ isActive }) =>
                                    cn(
                                        "flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                                        isActive
                                            ? "bg-blue-500/10 text-blue-400"
                                            : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                                    )
                                }
                            >
                                <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                                {item.name}
                            </NavLink>
                        ))}
                    </nav>
                </div>

                {/* Tools Modules */}
                <div>
                    <h3 className="px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                        Tools & Labs
                    </h3>
                    <nav className="space-y-1">
                        {tools.map((item) => (
                            <NavLink
                                key={item.name}
                                to={item.href}
                                className={({ isActive }) =>
                                    cn(
                                        "flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
                                        isActive
                                            ? "bg-purple-500/10 text-purple-400"
                                            : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                                    )
                                }
                            >
                                <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                                {item.name}
                            </NavLink>
                        ))}
                    </nav>
                </div>

            </div>

            {/* 🔴 User Profile (Bottom) */}
            <div className="border-t border-slate-800 p-4">
                <NavLink to="/settings" className="flex items-center w-full group">
                    <div className="h-9 w-9 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 group-hover:bg-slate-700 transition-colors">
                        <Settings className="h-5 w-5" />
                    </div>
                    <div className="ml-3">
                        <p className="text-sm font-medium text-slate-300 group-hover:text-white">Settings</p>
                        <p className="text-xs text-slate-500">v2.1.0-beta</p>
                    </div>
                </NavLink>
            </div>

        </div>
    )
}
