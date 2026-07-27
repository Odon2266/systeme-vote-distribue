import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function AdminDashboard() {
  const [resultats, setResultats] = useState([]);
  const [votes, setVotes] = useState([]);
  const [nouveauNom, setNouveauNom] = useState('');
  const [nouveauNumero, setNouveauNumero] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('resultats'); // 'resultats', 'votes', 'candidats'
  const navigate = useNavigate();

  // Charger les données de l'API
  const fetchData = async () => {
    try {
      // Récupérer les résultats
      const resResultats = await axios.get('http://localhost:8000/resultats');
      setResultats(resResultats.data.resultats || []);

      // Récupérer la liste des votes hachés locales
      const resVotes = await axios.get('http://localhost:8000/votes');
      setVotes(resVotes.data.votes || []);
    } catch (err) {
      setError("Erreur lors du chargement des données d'administration.");
    }
  };

  useEffect(() => {
    fetchData();
    // Rafraîchissement automatique toutes les 5 secondes
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    sessionStorage.clear();
    navigate('/login');
  };

  const handleAddCandidat = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      await axios.post('http://localhost:8000/candidats', {
        numero: parseInt(nouveauNumero),
        nom: nouveauNom
      });
      setSuccess(`Le candidat "${nouveauNom}" a été ajouté avec succès !`);
      setNouveauNom('');
      setNouveauNumero('');
      fetchData();
    } catch (err) {
      const msg = err.response?.data?.detail || "Erreur lors de l'ajout du candidat.";
      setError(msg);
    }
  };

  // Calcul du nombre total de votes enregistrés
  const totalVotes = resultats.reduce((acc, curr) => acc + parseInt(curr.votes || 0), 0);

  return (
    <div className="bg-light min-vh-100 py-4">
      <div className="container">
        {/* En-tête */}
        <div className="d-flex justify-content-between align-items-center mb-4 bg-white p-3 rounded-4 shadow-sm">
          <div>
            <h4 className="fw-bold text-primary m-0">🛠️ Panneau d'Administration</h4>
            <small className="text-muted">Gestion du scrutin & Résultats P2P</small>
          </div>
          <button onClick={handleLogout} className="btn btn-outline-danger btn-sm fw-semibold">
            Déconnexion
          </button>
        </div>

        {error && <div className="alert alert-danger py-2">{error}</div>}
        {success && <div className="alert alert-success py-2">{success}</div>}

        {/* Barre d'onglets */}
        <ul className="nav nav-pills mb-4 bg-white p-2 rounded-4 shadow-sm justify-content-center">
          <li className="nav-item">
            <button 
              className={`nav-link fw-semibold ${activeTab === 'resultats' ? 'active' : ''}`}
              onClick={() => setActiveTab('resultats')}
            >
              📊 Résultats ({totalVotes} votes)
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link fw-semibold ${activeTab === 'votes' ? 'active' : ''}`}
              onClick={() => setActiveTab('votes')}
            >
              🔗 Registre des Votes ({votes.length})
            </button>
          </li>
          <li className="nav-item">
            <button 
              className={`nav-link fw-semibold ${activeTab === 'candidats' ? 'active' : ''}`}
              onClick={() => setActiveTab('candidats')}
            >
              ➕ Ajouter un Candidat
            </button>
          </li>
        </ul>

        {/* ONGLET 1 : RESULTATS EN DIRECT */}
        {activeTab === 'resultats' && (
          <div className="row g-4">
            {resultats.map((res) => {
              const pourcentage = totalVotes > 0 ? ((res.votes / totalVotes) * 100).toFixed(1) : 0;
              return (
                <div className="col-md-6 col-lg-4" key={res.numero}>
                  <div className="card shadow-sm border-0 rounded-4 p-3 bg-white">
                    <div className="card-body">
                      <div className="d-flex justify-content-between align-items-center mb-2">
                        <span className="badge bg-primary rounded-pill">N° {res.numero}</span>
                        <h4 className="fw-bold text-primary m-0">{res.votes} voix</h4>
                      </div>
                      <h5 className="fw-bold text-dark">{res.nom}</h5>
                      <div className="progress mt-3" style={{ height: '10px' }}>
                        <div 
                          className="progress-bar bg-primary rounded" 
                          role="progressbar" 
                          style={{ width: `${pourcentage}%` }}
                        ></div>
                      </div>
                      <small className="text-muted mt-1 d-block text-end">{pourcentage}% des suffrages</small>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ONGLET 2 : REGISTRE DES VOTES (HASHES & ORIGINES) */}
        {activeTab === 'votes' && (
          <div className="card border-0 shadow-sm rounded-4 p-3 bg-white">
            <h5 className="fw-bold text-dark mb-3">Votes Enregistrés en BDD (Anonymisés)</h5>
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead className="table-light">
                  <tr>
                    <th>ID</th>
                    <th>Candidat</th>
                    <th>Empreinte Hash (SHA-256)</th>
                    <th>Nœud d'Origine (IP)</th>
                    <th>Horodatage</th>
                  </tr>
                </thead>
                <tbody>
                  {votes.map((v) => (
                    <tr key={v.id}>
                      <td className="fw-bold">#{v.id}</td>
                      <td><span className="badge bg-secondary">{v.candidat_nom || `N°${v.candidat_numero}`}</span></td>
                      <td><code className="text-break">{v.vote_hash}</code></td>
                      <td><span className="badge bg-info text-dark">{v.node_origin}</span></td>
                      <td className="small text-muted">{v.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ONGLET 3 : AJOUTER UN CANDIDAT */}
        {activeTab === 'candidats' && (
          <div className="row justify-content-center">
            <div className="col-md-6">
              <div className="card border-0 shadow-sm rounded-4 p-4 bg-white">
                <h5 className="fw-bold text-dark mb-3">Nouveau Candidat</h5>
                <form onSubmit={handleAddCandidat}>
                  <div className="mb-3">
                    <label className="form-label fw-semibold small">Numéro du Candidat</label>
                    <input 
                      type="number" 
                      className="form-control" 
                      value={nouveauNumero}
                      onChange={(e) => setNouveauNumero(e.target.value)}
                      required 
                      placeholder="Ex: 3"
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label fw-semibold small">Nom Complet</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      value={nouveauNom}
                      onChange={(e) => setNouveauNom(e.target.value)}
                      required 
                      placeholder="Ex: Randria Paul"
                    />
                  </div>
                  <button type="submit" className="btn btn-primary w-100 fw-semibold">
                    Enregistrer le candidat
                  </button>
                </form>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}