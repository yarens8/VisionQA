
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { CreateProjectPage } from './pages/CreateProjectPage'
import { ProjectPagesList } from './pages/ProjectPagesList' // Yeni eklenen sayfa
import TestLibraryPage from './pages/TestLibraryPage'
import TestRunsPage from './pages/TestRunsPage'
import FindingsPage from './pages/FindingsPage'
import TestLabPage from './pages/TestLabPage'
import DatabasePage from './pages/DatabasePage'
import SecurityPage from './pages/SecurityPage'
import AccessibilityPage from './pages/AccessibilityPage'
import UIUXPage from './pages/UIUXPage'
import SettingsPage from './pages/SettingsPage'
import ScenarioPage from './pages/ScenarioPage'

function App() {
    return (
        <Router>
            <Routes>

                {/* 🟢 Ana Layout */}
                <Route path="/" element={<AppLayout />}>

                    {/* 🏠 Ana Sayfa (Dashboard) */}
                    <Route index element={<DashboardPage />} />

                    {/* 📂 Projeler & Modüller (Hiyerarşik Yapı) */}
                    <Route path="projects" element={<ProjectsPage />} />
                    <Route path="projects/new" element={<CreateProjectPage />} />

                    {/* 🚀 Projeye tıklandığında URL segmentleri/sayfaları gelir */}
                    <Route path="projects/:projectId/pages" element={<ProjectPagesList />} />

                    {/* 🧪 Belirli bir sayfaya (URL'e) ait test kütüphanesi */}
                    <Route path="projects/:projectId/pages/:pageId/tests" element={<TestLibraryPage />} />

                    {/* Geriye dönük uyumluluk veya genel kütüphane erişimi için eski rotayı koruyabiliriz ama biz yeni yapıyı tercih ediyoruz */}
                    <Route path="projects/:projectId/tests" element={<Navigate to="pages" replace />} />

                    {/* 🏃‍♂️ Test Koşuları & Bulgular */}
                    <Route path="test-runs" element={<TestRunsPage />} />
                    <Route path="findings" element={<FindingsPage />} />

                    {/* 🧪 Tools & Labs */}
                    <Route path="lab" element={<TestLabPage />} />
                    <Route path="database" element={<DatabasePage />} />
                    <Route path="scenarios" element={<ScenarioPage />} />
                    <Route path="security" element={<SecurityPage />} />
                    <Route path="uiux" element={<UIUXPage />} />
                    <Route path="accessibility" element={<AccessibilityPage />} />

                    {/* ⚙️ Ayarlar */}
                    <Route path="settings" element={<SettingsPage />} />

                    {/* 🚫 Bilinmeyen Sayfalar */}
                    <Route path="*" element={<Navigate to="/" replace />} />

                </Route>

            </Routes>
        </Router>
    )
}

export default App
