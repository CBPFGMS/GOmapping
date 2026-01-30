import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';
import GOsummary from './GOsummary';
import GODetail from './GODetail';
import OrgMappings from './OrgMappings';
import MappingDashboard from './MappingDashboard';
import MergeDecisions from './MergeDecisions';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<GOsummary />} />
        <Route path="/go-summary" element={<GOsummary />} />
        <Route path="/go-detail/:goId" element={<GODetail />} />
        <Route path="/org-mappings/:goId" element={<OrgMappings />} />
        <Route path="/mapping-dashboard" element={<MappingDashboard />} />
        <Route path="/merge-decisions" element={<MergeDecisions />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
