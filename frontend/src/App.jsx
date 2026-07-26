import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';

// Pages temporaires en attendant de coder les dashboards complets
function VoterDashboard() {
  return <div className="container mt-5"><h2>Tableau de bord - Électeur</h2></div>;
}

function AdminDashboard() {
  return <div className="container mt-5"><h2>Tableau de bord - Administrateur</h2></div>;
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/voter" element={<VoterDashboard />} />
        <Route path="/admin" element={<AdminDashboard />} />
        {/* Redirection par défaut vers la page de login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}