
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { CreateProjectPage } from './pages/CreateProjectPage'
import TestLibraryPage from './pages/TestLibraryPage'
import TestRunsPage from './pages/TestRunsPage'
import FindingsPage from './pages/FindingsPage'
import TestLabPage from './pages/TestLabPage'
import DatabasePage from './pages/DatabasePage'
import SecurityPage from './pages/SecurityPage'
import AccessibilityPage from './pages/AccessibilityPage'
import SettingsPage from './pages/SettingsPage'

function App() {
    return (
        <Router>
            <Routes>

                {/* 🟢 Ana Layout */}
                <Route path="/" element={<AppLayout />}>

                    {/* 🏠 Ana Sayfa (Dashboard) */}
                    <Route index element={<DashboardPage />} />

                    {/* 📂 Projeler Sayfası */}
                    <Route path="projects" element={<ProjectsPage />} />
                    <Route path="projects/new" element={<CreateProjectPage />} />
                    <Route path="projects/:projectId/tests" element={<TestLibraryPage />} />

                    {/* 🏃‍♂️ Test Koşuları & Bulgular */}
                    <Route path="test-runs" element={<TestRunsPage />} />
                    <Route path="findings" element={<FindingsPage />} />

                    {/* 🧪 Tools & Labs */}
                    <Route path="lab" element={<TestLabPage />} />
                    <Route path="database" element={<DatabasePage />} />
                    <Route path="security" element={<SecurityPage />} />
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
