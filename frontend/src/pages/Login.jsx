import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Login() {
  const [cin, setCin] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/login', {
        cin,
        password
      });

      const { role } = response.data;
      if (role === 'admin') {
        navigate('/admin');
      } else {
        navigate('/voter');
      }
    } catch (err) {
      setError('Identifiants incorrects ou serveur injoignable.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-light vh-100 d-flex align-items-center justify-content-center">
      <div className="card shadow-lg border-0 p-4 rounded-4" style={{ width: '420px', backgroundColor: '#ffffff' }}>
        
        <div className="text-center mb-4">
          <div className="bg-primary text-white rounded-circle d-inline-flex align-items-center justify-content-center mb-3 shadow" style={{ width: '60px', height: '60px', fontSize: '24px' }}>
            🗳️
          </div>
          <h3 className="fw-bold text-dark">Système de Vote</h3>
          <p className="text-muted small">Connectez-vous pour accéder à votre espace</p>
        </div>

        {error && <div className="alert alert-danger py-2 small text-center">{error}</div>}

        <form onSubmit={handleLogin}>
          <div className="mb-3">
            <label className="form-label fw-semibold small text-secondary">Numéro CIN</label>
            <input
              type="text"
              className="form-control form-control-lg fs-6"
              value={cin}
              onChange={(e) => setCin(e.target.value)}
              required
              placeholder="Ex: 42301101751"
            />
          </div>

          <div className="mb-4">
            <label className="form-label fw-semibold small text-secondary">Mot de passe</label>
            <input
              type="password"
              className="form-control form-control-lg fs-6"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>

          <button type="submit" className="btn btn-primary btn-lg w-100 fw-semibold shadow-sm" disabled={loading}>
            {loading ? 'Connexion en cours...' : 'Se connecter'}
          </button>
        </form>

        <div className="text-center mt-4">
          <small className="text-muted">Plateforme de Vote Distribuée & Sécurisée</small>
        </div>
      </div>
    </div>
  );
}