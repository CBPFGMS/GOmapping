import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './App.css';
import GOsummary from './GOsummary';
import GODetail from './GODetail';
import OrgMappings from './OrgMappings';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<GOsummary />} />
        <Route path="/go-detail/:goId" element={<GODetail />} />
        <Route path="/org-mappings/:goId" element={<OrgMappings />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
