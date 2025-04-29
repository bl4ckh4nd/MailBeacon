import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { CssBaseline } from '@mui/material';
import Layout from './components/Layout';
import SingleFinderPage from './pages/SingleFinderPage';
import BatchFinderPage from './pages/BatchFinderPage';

const App: React.FC = () => {
  return (
    <>
      <CssBaseline /> {/* Normalizes CSS across browsers */}
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/single" replace />} /> {/* Redirect base path */}
            <Route path="/single" element={<SingleFinderPage />} />
            <Route path="/batch" element={<BatchFinderPage />} />
            {/* Add other routes here if needed */}
            <Route path="*" element={<Navigate to="/single" replace />} /> {/* Fallback route */}
          </Routes>
        </Layout>
      </Router>
    </>
  );
};

export default App;
