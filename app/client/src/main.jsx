import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { TraceProvider } from './lib/trace.jsx';
import { SessionProvider } from './lib/session.jsx';
import Layout from './components/Layout.jsx';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import AttackLab from './pages/AttackLab.jsx';
import CloudView from './pages/CloudView.jsx';
import Results from './pages/Results.jsx';
import './styles.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <TraceProvider>
      <SessionProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/lab" element={<AttackLab />} />
              <Route path="/cloud" element={<CloudView />} />
              <Route path="/results" element={<Results />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </SessionProvider>
    </TraceProvider>
  </React.StrictMode>,
);
