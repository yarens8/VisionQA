
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";

export function AppLayout() {
    return (
        <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-200">

            {/* 🟢 Sidebar (Sabit) */}
            <Sidebar />

            {/* 🔵 Main Content Area */}
            <div className="flex min-w-0 flex-1 flex-col pl-64"> {/* pl-64: Sidebar genişliği kadar boşluk */}

                {/* Header (Basit versiyon) */}
                <header className="h-16 flex items-center justify-between px-8 border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-10">
                    <div className="flex items-center gap-4">
                        <h1 className="text-xl font-semibold text-slate-100">
                            VisionQA Platform
                        </h1>
                        <span className="bg-blue-500/10 text-blue-400 text-xs px-2 py-0.5 rounded-full font-medium border border-blue-500/20">
                            Enterprise
                        </span>
                    </div>

                    <div className="text-sm text-slate-500">
                        {/* Buraya User profile / Theme switcher gelecek */}
                        admin@visionqa.com
                    </div>
                </header>

                {/* 🔴 Page Content (Değişken Alan) */}
                <main className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto p-8 scroll-smooth">
                    <div className="mx-auto w-full max-w-7xl min-w-0">
                        <Outlet />
                    </div>
                </main>

            </div>
        </div>
    )
}
