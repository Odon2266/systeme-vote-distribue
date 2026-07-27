import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function VoterDashboard() {
  const [candidats, setCandidats] = useState([]);
  const [selectedCandidat, setSelectedCandidat] = useState(null);
  const [targetIp, setTargetIp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [voteSubmitted, setVoteSubmitted] = useState(false);
  const [receipt, setReceipt] = useState(null);

  const navigate = useNavigate();
  const cin = sessionStorage.getItem('cin');
  const password = sessionStorage.getItem('password');

  useEffect(() => {
    // Si l'utilisateur n'est pas connecté, retour au login
    if (!cin || !password) {
      navigate('/login');
      return;
    }

    // Récupérer la liste des candidats
    const fetchCandidats = async () => {
      try {
        const response = await axios.get('http://localhost:8000/candidats');
        setCandidats(response.data || []);
      } catch (err) {
        setError("Erreur lors de la récupération des candidats.");
      }
    };

    fetchCandidats();
  }, [cin, password, navigate]);

  const handleLogout = () => {
    sessionStorage.clear();
    navigate('/login');
  };

  const handleConfirmVote = async () => {
    if (!selectedCandidat) return;

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('http://localhost:8000/vote', {
        cin: cin,
        password: password,
        candidat_numero: selectedCandidat.numero,
        target_ip: targetIp.trim() !== '' ? targetIp.trim() : null,
        target_port: 6000
      });

      setReceipt({
        candidat: selectedCandidat.nom,
        numero: selectedCandidat.numero,
        message: response.data.message
      });
      setVoteSubmitted(true);
    } catch (err) {
      const backendMsg = err.response?.data?.detail;
      setError(backendMsg || "Une erreur est survenue lors du vote.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-light min-vh-100 py-5">
      <div className="container" style={{ maxWidth: '800px' }}>
        
        {/* En-tête */}
        <div className="d-flex justify-content-between align-items-center mb-4 bg-white p-3 rounded-4 shadow-sm">
          <div>
            <h4 className="fw-bold text-primary m-0">🗳️ Espace Électeur</h4>
            <small className="text-muted">CIN connecté : <strong>{cin}</strong></small>
          </div>
          <button onClick={handleLogout} className="btn btn-outline-danger btn-sm fw-semibold">
            Déconnexion
          </button>
        </div>

        {error && <div className="alert alert-danger rounded-3">{error}</div>}

        {/* ÉCRAN 1 : FORMULAIRE DE VOTE */}
        {!voteSubmitted ? (
          <div>
            <div className="card border-0 shadow-sm rounded-4 p-4 mb-4 bg-white">
              <h5 className="fw-bold text-dark mb-1">Sélectionnez votre candidat</h5>
              <p className="text-muted small mb-4">
                Votre choix sera anonymisé à l'aide d'une empreinte cryptographique SHA-256 avant d'être transmis au réseau P2P.
              </p>

              <div className="row g-3">
                {candidats.map((c) => (
                  <div className="col-md-6" key={c.numero}>
                    <div 
                      className={`card h-100 border-2 rounded-4 p-3 style-card ${selectedCandidat?.numero === c.numero ? 'border-primary bg-primary bg-opacity-10' : 'border-light bg-light'}`}
                      style={{ cursor: 'pointer', transition: 'all 0.2s' }}
                      onClick={() => setSelectedCandidat(c)}
                    >
                      <div className="d-flex align-items-center">
                        <div className="bg-primary text-white rounded-circle fw-bold d-flex align-items-center justify-content-center me-3" style={{ width: '45px', height: '45px' }}>
                          N°{c.numero}
                        </div>
                        <div>
                          <h6 className="fw-bold text-dark m-0">{c.nom}</h6>
                          <small className="text-muted">Candidat officiel</small>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Option Réseau P2P */}
            <div className="card border-0 shadow-sm rounded-4 p-4 mb-4 bg-white">
              <h6 className="fw-bold text-dark mb-2">🌐 Option Réseau P2P (Optionnel)</h6>
              <label className="form-label small text-muted">IP d'un autre nœud distant pour propager le vote</label>
              <input 
                type="text" 
                className="form-control" 
                placeholder="Ex: 192.168.1.50 (Laissez vide si vous votez en local)" 
                value={targetIp} 
                onChange={(e) => setTargetIp(e.target.value)}
              />
            </div>

            {/* Bouton de confirmation */}
            <button 
              className="btn btn-primary btn-lg w-100 fw-semibold rounded-3 shadow-sm"
              disabled={!selectedCandidat || loading}
              onClick={handleConfirmVote}
            >
              {loading ? "Validation et propagation en cours..." : selectedCandidat ? `Voter pour ${selectedCandidat.nom}` : "Veuillez choisir un candidat"}
            </button>
          </div>
        ) : (
          /* ÉCRAN 2 : REÇU DE CONFIRMATION DU VOTE */
          <div className="card border-0 shadow-lg rounded-4 p-5 text-center bg-white">
            <div className="bg-success text-white rounded-circle d-inline-flex align-items-center justify-content-center mb-3 mx-auto shadow" style={{ width: '70px', height: '70px', fontSize: '32px' }}>
              ✓
            </div>
            <h3 className="fw-bold text-dark">Vote Enregistré avec Succès !</h3>
            <p className="text-muted">{receipt?.message}</p>

            <div className="bg-light p-4 rounded-4 text-start my-3">
              <p className="mb-1"><strong>Candidat choisi :</strong> N°{receipt?.numero} - {receipt?.candidat}</p>
              <p className="mb-0 text-muted small">
                🔒 Votre compte a été mis à jour dans PostgreSQL. Vous ne pourrez plus voter à nouveau pour ce scrutin.
              </p>
            </div>

            <button onClick={handleLogout} className="btn btn-primary fw-semibold mt-3">
              Terminer et se déconnecter
            </button>
          </div>
        )}

      </div>
    </div>
  );
}