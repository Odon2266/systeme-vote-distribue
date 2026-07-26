import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function VoterDashboard() {
  const [candidats, setCandidats] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [hasVoted, setHasVoted] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  // Charger la liste des candidats depuis l'API FastAPI au chargement de la page
  useEffect(() => {
    const fetchCandidats = async () => {
      try {
        const response = await axios.get('http://localhost:8000/candidats');
        setCandidats(response.data);
      } catch (err) {
        setError("Impossible de charger la liste des candidats depuis le serveur.");
      }
    };
    fetchCandidats();
  }, []);

  const handleVote = async () => {
    if (!selectedCandidate) {
      setError("Veuillez sélectionner un candidat avant de voter.");
      return;
    }

    try {
      // Envoi du vote à l'API FastAPI
      await axios.post('http://localhost:8000/voter', {
        candidat_id: selectedCandidate
      });
      setHasVoted(true);
      setSuccess("Votre vote a été enregistré avec succès !");
    } catch (err) {
      setError("Erreur lors de l'enregistrement du vote. Vous avez peut-être déjà voté.");
    }
  };

  const handleLogout = () => {
    navigate('/login');
  };

  return (
    <div className="bg-light min-vh-100 py-4">
      <div className="container">
        {/* Barre de navigation supérieure */}
        <div className="d-flex justify-content-between align-items-center mb-4 bg-white p-3 rounded-4 shadow-sm">
          <h4 className="fw-bold text-primary m-0">🗳️ Espace Électeur</h4>
          <button onClick={handleLogout} className="btn btn-outline-danger btn-sm fw-semibold">
            Déconnexion
          </button>
        </div>

        {error && <div className="alert alert-danger">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {hasVoted ? (
          <div className="card shadow border-0 text-center p-5 rounded-4 bg-white">
            <div className="display-4 mb-3">✅</div>
            <h3 className="fw-bold text-success">Vote validé</h3>
            <p className="text-muted">Merci d'avoir participé au scrutin sécurisé.</p>
          </div>
        ) : (
          <div>
            <h5 className="fw-semibold text-dark mb-3">Choisissez votre candidat :</h5>
            <div className="row g-4">
              {candidats.map((candidat) => (
                <div className="col-md-4" key={candidat.id}>
                  <div 
                    className={`card h-100 shadow-sm border-2 cursor-pointer rounded-4 p-3 ${selectedCandidate === candidat.id ? 'border-primary bg-subtle' : 'border-light'}`}
                    onClick={() => setSelectedCandidate(candidat.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="card-body text-center">
                      <h5 className="fw-bold text-dark">{candidat.nom}</h5>
                      <p className="text-muted small">{candidat.parti || "Indépendant"}</p>
                      <div className="form-check d-flex justify-content-center mt-3">
                        <input 
                          className="form-check-input" 
                          type="radio" 
                          name="candidatRadio" 
                          checked={selectedCandidate === candidat.id}
                          onChange={() => setSelectedCandidate(candidat.id)}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="text-center mt-4">
              <button 
                onClick={handleVote} 
                className="btn btn-primary btn-lg px-5 fw-semibold shadow"
                disabled={!selectedCandidate}
              >
                Confirmer mon vote
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}