import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('resultats');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Données
  const [resultats, setResultats] = useState([]);
  const [candidats, setCandidats] = useState([]);
  const [electeurs, setElecteurs] = useState([]);
  const [admins, setAdmins] = useState([]);
  const [votes, setVotes] = useState([]);

  // Formulaires - Candidats
  const [candNumero, setCandNumero] = useState('');
  const [candNom, setCandNom] = useState('');
  const [editingCandNum, setEditingCandNum] = useState(null);

  // Formulaires - Électeurs
  const [voterCin, setVoterCin] = useState('');
  const [voterPass, setVoterPass] = useState('');

  // Formulaires - Admins
  const [adminId, setAdminId] = useState('');
  const [adminNom, setAdminNom] = useState('');
  const [adminPass, setAdminPass] = useState('');

  const navigate = useNavigate();

  // Chargement global des données
  const fetchData = async () => {
    try {
      const [resRes, resCand, resElect, resAdmin, resVotes] = await Promise.all([
        axios.get('http://localhost:8000/resultats'),
        axios.get('http://localhost:8000/candidats'),
        axios.get('http://localhost:8000/electeurs'),
        axios.get('http://localhost:8000/admins'),
        axios.get('http://localhost:8000/votes')
      ]);

      setResultats(resRes.data.resultats || []);
      setCandidats(resCand.data || []);
      setElecteurs(resElect.data || []);
      setAdmins(resAdmin.data || []);
      setVotes(resVotes.data.votes || []);
    } catch (err) {
      setError("Erreur lors de la récupération des données.");
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    sessionStorage.clear();
    navigate('/login');
  };

  // ==========================================
  // 🗳️ ACTIONS CANDIDATS
  // ==========================================
  const handleSaveCandidat = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    try {
      if (editingCandNum !== null) {
        await axios.put(`http://localhost:8000/candidats/${editingCandNum}`, {
          numero: parseInt(candNumero),
          nom: candNom
        });
        setSuccess("Candidat mis à jour avec succès !");
        setEditingCandNum(null);
      } else {
        await axios.post('http://localhost:8000/candidats', {
          numero: parseInt(candNumero),
          nom: candNom
        });
        setSuccess("Candidat ajouté avec succès !");
      }
      setCandNumero(''); setCandNom('');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de l'enregistrement du candidat.");
    }
  };

  const handleEditCandidat = (c) => {
    setEditingCandNum(c.numero);
    setCandNumero(c.numero);
    setCandNom(c.nom);
  };

  const handleDeleteCandidat = async (numero) => {
    if (!window.confirm(`Supprimer le candidat N°${numero} ?`)) return;
    try {
      await axios.delete(`http://localhost:8000/candidats/${numero}`);
      setSuccess("Candidat supprimé.");
      fetchData();
    } catch (err) {
      setError("Impossible de supprimer le candidat.");
    }
  };

  // ==========================================
  // 👥 ACTIONS ÉLECTEURS
  // ==========================================
  const handleAddElecteur = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    try {
      await axios.post('http://localhost:8000/electeurs', {
        cin: voterCin,
        password: voterPass
      });
      setSuccess("Électeur créé avec succès !");
      setVoterCin(''); setVoterPass('');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de l'ajout de l'électeur.");
    }
  };

  const handleResetVote = async (cin) => {
    try {
      await axios.put(`http://localhost:8000/electeurs/${cin}/reset`);
      setSuccess(`Statut de vote réinitialisé pour ${cin}`);
      fetchData();
    } catch (err) {
      setError("Erreur lors de la réinitialisation.");
    }
  };

  const handleDeleteElecteur = async (cin) => {
    if (!window.confirm(`Supprimer l'électeur ${cin} ?`)) return;
    try {
      await axios.delete(`http://localhost:8000/electeurs/${cin}`);
      setSuccess("Électeur supprimé.");
      fetchData();
    } catch (err) {
      setError("Erreur lors de la suppression.");
    }
  };

  // ==========================================
  // 🛡️ ACTIONS ADMINS
  // ==========================================
  const handleAddAdmin = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    try {
      await axios.post('http://localhost:8000/admins', {
        identifiant: adminId,
        nom: adminNom,
        password: adminPass
      });
      setSuccess("Nouvel administrateur ajouté !");
      setAdminId(''); setAdminNom(''); setAdminPass('');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || "Erreur lors de l'ajout d'un admin.");
    }
  };

  const handleDeleteAdmin = async (id) => {
    if (!window.confirm(`Supprimer l'administrateur ${id} ?`)) return;
    try {
      await axios.delete(`http://localhost:8000/admins/${id}`);
      setSuccess("Administrateur supprimé.");
      fetchData();
    } catch (err) {
      setError("Impossible de supprimer l'administrateur.");
    }
  };

  const totalVotes = resultats.reduce((acc, curr) => acc + parseInt(curr.votes || 0), 0);

  return (
    <div className="bg-light min-vh-100 py-4">
      <div className="container">
        
        {/* En-tête */}
        <div className="d-flex justify-content-between align-items-center mb-4 bg-white p-3 rounded-4 shadow-sm">
          <div>
            <h4 className="fw-bold text-primary m-0">🛠️ Panneau d'Administration</h4>
            <small className="text-muted">Gestion Globale & Scrutin P2P</small>
          </div>
          <button onClick={handleLogout} className="btn btn-outline-danger btn-sm fw-semibold">
            Déconnexion
          </button>
        </div>

        {error && <div className="alert alert-danger py-2">{error}</div>}
        {success && <div className="alert alert-success py-2">{success}</div>}

        {/* Navigation Onglets */}
        <ul className="nav nav-pills mb-4 bg-white p-2 rounded-4 shadow-sm justify-content-center">
          <li className="nav-item">
            <button className={`nav-link fw-semibold ${activeTab === 'resultats' ? 'active' : ''}`} onClick={() => setActiveTab('resultats')}>
              📊 Résultats
            </button>
          </li>
          <li className="nav-item">
            <button className={`nav-link fw-semibold ${activeTab === 'candidats' ? 'active' : ''}`} onClick={() => setActiveTab('candidats')}>
              🗳️ Candidats ({candidats.length})
            </button>
          </li>
          <li className="nav-item">
            <button className={`nav-link fw-semibold ${activeTab === 'electeurs' ? 'active' : ''}`} onClick={() => setActiveTab('electeurs')}>
              👥 Électeurs ({electeurs.length})
            </button>
          </li>
          <li className="nav-item">
            <button className={`nav-link fw-semibold ${activeTab === 'admins' ? 'active' : ''}`} onClick={() => setActiveTab('admins')}>
              🛡️ Admins ({admins.length})
            </button>
          </li>
          <li className="nav-item">
            <button className={`nav-link fw-semibold ${activeTab === 'votes' ? 'active' : ''}`} onClick={() => setActiveTab('votes')}>
              🔗 Registre ({votes.length})
            </button>
          </li>
        </ul>

        {/* 1. ONGLET RÉSULTATS */}
        {activeTab === 'resultats' && (
          <div className="row g-4">
            {resultats.map((res) => {
              const pct = totalVotes > 0 ? ((res.votes / totalVotes) * 100).toFixed(1) : 0;
              return (
                <div className="col-md-6 col-lg-4" key={res.numero}>
                  <div className="card shadow-sm border-0 rounded-4 p-3 bg-white">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span className="badge bg-primary rounded-pill">N° {res.numero}</span>
                      <h4 className="fw-bold text-primary m-0">{res.votes} voix</h4>
                    </div>
                    <h5 className="fw-bold text-dark">{res.nom}</h5>
                    <div className="progress mt-3" style={{ height: '10px' }}>
                      <div className="progress-bar bg-primary" style={{ width: `${pct}%` }}></div>
                    </div>
                    <small className="text-muted mt-1 d-block text-end">{pct}%</small>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* 2. ONGLET CRUD CANDIDATS */}
        {activeTab === 'candidats' && (
          <div className="row g-4">
            <div className="col-md-4">
              <div className="card border-0 shadow-sm rounded-4 p-3 bg-white">
                <h5 className="fw-bold mb-3">{editingCandNum !== null ? "Modifier Candidat" : "Nouveau Candidat"}</h5>
                <form onSubmit={handleSaveCandidat}>
                  <div className="mb-2">
                    <label className="form-label small fw-semibold">Numéro</label>
                    <input type="number" className="form-control" value={candNumero} onChange={(e) => setCandNumero(e.target.value)} required />
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Nom complet</label>
                    <input type="text" className="form-control" value={candNom} onChange={(e) => setCandNom(e.target.value)} required />
                  </div>
                  <button type="submit" className="btn btn-primary w-100 fw-semibold">
                    {editingCandNum !== null ? "Mettre à jour" : "Ajouter"}
                  </button>
                  {editingCandNum !== null && (
                    <button type="button" className="btn btn-link w-100 text-muted mt-1 btn-sm" onClick={() => { setEditingCandNum(null); setCandNumero(''); setCandNom(''); }}>
                      Annuler
                    </button>
                  )}
                </form>
              </div>
            </div>
            <div className="col-md-8">
              <div className="card border-0 shadow-sm rounded-4 p-3 bg-white">
                <h5 className="fw-bold mb-3">Liste des Candidats</h5>
                <table className="table table-hover align-middle">
                  <thead><tr><th>N°</th><th>Nom</th><th>Actions</th></tr></thead>
                  <tbody>
                    {candidats.map((c) => (
                      <tr key={c.numero}>
                        <td className="fw-bold">#{c.numero}</td>
                        <td>{c.nom}</td>
                        <td>
                          <button className="btn btn-sm btn-outline-warning me-2" onClick={() => handleEditCandidat(c)}>✏️</button>
                          <button className="btn btn-sm btn-outline-danger" onClick={() => handleDeleteCandidat(c.numero)}>🗑️</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 3. ONGLET CRUD ÉLECTEURS */}
        {activeTab === 'electeurs' && (
          <div className="row g-4">
            <div className="col-md-4">
              <div className="card border-0 shadow-sm rounded-4 p-3 bg-white">
                <h5 className="fw-bold mb-3">Ajouter un Électeur</h5>
                <form onSubmit={handleAddElecteur}>
                  <div className="mb-2">
                    <label className="form-label small fw-semibold">Numéro CIN (12 chiffres)</label>
                    <input type="text" className="form-control" value={voterCin} onChange={(e) => setVoterCin(e.target.value)} required placeholder="Ex: 423011017551" />
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Mot de passe</label>
                    <input type="password" className="form-control" value={voterPass} onChange={(e) => setVoterPass(e.target.value)} required />
                  </div>
                  <button type="submit" className="btn btn-success w-100 fw-semibold">Enregistrer Électeur</button>
                </form>
              </div>
            </div>
            <div className="col-md-8">
              <div className="card border-0 shadow-sm rounded-4 p-3 bg-white">
                <h5 className="fw-bold mb-3">Liste des Électeurs</h5>
                <table className="table table-hover align-middle">
                  <thead><tr><th>CIN</th><th>Statut Vote</th><th>Actions</th></tr></thead>
                  <tbody>
                    {electeurs.map((e) => (
                      <tr key={e.cin}>
                        <td className="fw-bold">{e.cin}</td>
                        <td>
                          {e.has_voted ? (
                            <span className="badge bg-danger">A déjà voté</span>
                          ) : (
                            <span className="badge bg-success">N'a pas voté</span>
                          )}
                        </td>
                        <td>
                          {e.has_voted && (
                            <button className="btn btn-sm btn-outline-primary me-2" onClick={() => handleResetVote(e.cin)} title="Autoriser à revoter">🔄 Reset</button>
                          )}
                          <button className="btn btn-sm btn-outline-danger" onClick={() => handleDeleteElecteur(e.cin)}>🗑️</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 4. ONGLET CRUD ADMINS */}
        {activeTab === 'admins' && (
          <div className="row g-4">
            <div className="col-md-4">
              <div className="card border-0 shadow-sm rounded-4 p-3 bg-white">
                <h5 className="fw-bold mb-3">Ajouter un Admin</h5>
                <form onSubmit={handleAddAdmin}>
                  <div className="mb-2">
                    <label className="form-label small fw-semibold">Identifiant</label>
                    <input type="text" className="form-control" value={adminId} onChange={(e) => setAdminId(e.target.value)} required placeholder="Ex: admin2" />
                  </div>
                  <div className="mb-2">
                    <label className="form-label small fw-semibold">Nom Complet</label>
                    <input type="text" className="form-control" value={adminNom} onChange={(e) => setAdminNom(e.target.value)} required />
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Mot de passe</label>
                    <input type="password" className="form-control" value={adminPass} onChange={(e) => setAdminPass(e.target.value)} required />
                  </div>
                  <button type="submit" className="btn btn-dark w-100 fw-semibold">Créer Administrateur</button>
                </form>
              </div>
            </div>
            <div className="col-md-8">
              <div className="card border-0 shadow-sm rounded-4 p-3 bg-white">
                <h5 className="fw-bold mb-3">Administrateurs du Système</h5>
                <table className="table table-hover align-middle">
                  <thead><tr><th>ID</th><th>Identifiant</th><th>Nom</th><th>Actions</th></tr></thead>
                  <tbody>
                    {admins.map((a) => (
                      <tr key={a.id}>
                        <td>#{a.id}</td>
                        <td className="fw-bold">{a.identifiant}</td>
                        <td>{a.nom}</td>
                        <td>
                          <button className="btn btn-sm btn-outline-danger" onClick={() => handleDeleteAdmin(a.identifiant)}>🗑️</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* 5. ONGLET REGISTRE DES VOTES */}
        {activeTab === 'votes' && (
          <div className="card border-0 shadow-sm rounded-4 p-3 bg-white">
            <h5 className="fw-bold mb-3">Registre P2P des Votes Anonymes</h5>
            <div className="table-responsive">
              <table className="table table-hover align-middle">
                <thead>
                  <tr><th>ID</th><th>Candidat</th><th>Hash SHA-256</th><th>IP Nœud</th><th>Date</th></tr>
                </thead>
                <tbody>
                  {votes.map((v) => (
                    <tr key={v.id}>
                      <td className="fw-bold">#{v.id}</td>
                      <td><span className="badge bg-secondary">{v.candidat_nom}</span></td>
                      <td><code>{v.vote_hash}</code></td>
                      <td><span className="badge bg-info text-dark">{v.node_origin}</span></td>
                      <td className="small text-muted">{v.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}