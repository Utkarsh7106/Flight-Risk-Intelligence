import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './routes/ProtectedRoute';
import { AppShell } from './components/layout/AppShell';
import { LoginPage } from './pages/auth/LoginPage';
import { DirectoryPage } from './pages/directory/DirectoryPage';
import { WorkforceHealthPage } from './pages/workforce-health/WorkforceHealthPage';
import { EmployeeScoreDrilldownPage } from './pages/workforce-health/EmployeeScoreDrilldownPage';
import { FairnessAuditPage } from './pages/workforce-health/FairnessAuditPage';
import { RiskAnalysisPage } from './pages/risk-analysis/RiskAnalysisPage';
import { RiskEmployeeDrilldownPage } from './pages/risk-analysis/RiskEmployeeDrilldownPage';
import { DeparturesPage } from './pages/departures/DeparturesPage';
import { RecordDeparturePage } from './pages/departures/RecordDeparturePage';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/directory" element={<DirectoryPage />} />
            <Route path="/workforce-health" element={<WorkforceHealthPage />} />
            <Route path="/workforce-health/employees/:id" element={<EmployeeScoreDrilldownPage />} />
            <Route path="/workforce-health/fairness-audit" element={<FairnessAuditPage />} />
            <Route path="/risk-analysis" element={<RiskAnalysisPage />} />
            <Route path="/risk-analysis/employees/:id" element={<RiskEmployeeDrilldownPage />} />
            <Route path="/departures" element={<DeparturesPage />} />
            <Route path="/departures/new" element={<RecordDeparturePage />} />
          </Route>
        </Route>

        <Route path="/" element={<Navigate to="/directory" replace />} />
        <Route path="*" element={<Navigate to="/directory" replace />} />
      </Routes>
    </AuthProvider>
  );
}
