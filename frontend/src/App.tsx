
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { CreateProjectPage } from './pages/CreateProjectPage'
import TestLibraryPage from './pages/TestLibraryPage'

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

                    {/* 🚫 Bilinmeyen Sayfalar */}
                    <Route path="*" element={<Navigate to="/" replace />} />

                </Route>

            </Routes>
        </Router>
    )
}

export default App
