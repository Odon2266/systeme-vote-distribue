import socket
import threading
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import (
    verify_and_mark_voter,
    save_vote_to_local_db,
    get_all_local_votes,
    get_resultats_db,
    get_all_candidats,
    verify_user_login,
    add_candidat_db
)
from crypto import hash_vote
from p2p import propagate_vote

app = FastAPI(title="P2P Voting Node API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SCHÉMAS PYDANTIC ---

class VoteSchema(BaseModel):
    cin: str
    password: str
    candidat_numero: int
    target_ip: Optional[str] = None
    target_port: int = 6000

class LoginSchema(BaseModel):
    cin: str
    password: str

class CandidatSchema(BaseModel):
    numero: int
    nom: str


# --- ROUTES DE L'API ---

@app.post("/login")
def login(creds: LoginSchema):
    # Vérifie si c'est un administrateur ou un électeur via la BDD
    role = verify_user_login(creds.cin, creds.password)
    return {"status": "success", "role": role, "message": "Connexion réussie"}


@app.get("/candidats")
def get_candidats():
    # Récupère la liste de tous les candidats
    return get_all_candidats()


@app.post("/candidats")
def add_candidat(candidat: CandidatSchema):
    # Ajoute un nouveau candidat dans la BDD
    add_candidat_db(candidat.numero, candidat.nom)
    return {"status": "success", "message": "Candidat ajouté avec succès !"}


@app.post("/vote")
def receive_vote_from_web(vote_req: VoteSchema):
    # 1. Vérifier l'électeur et marquer 'has_voted' = True dans la BDD
    verify_and_mark_voter(vote_req.cin, vote_req.password)

    # 2. Hacher le vote pour la table anonyme
    vote_hash = hash_vote(vote_req.cin, vote_req.candidat_numero)
    my_ip = socket.gethostbyname(socket.gethostname())

    vote_payload = {
        "type": "VOTE",
        "data": {
            "candidat_numero": vote_req.candidat_numero,
            "vote_hash": vote_hash,
            "node_origin": my_ip
        }
    }

    # 3. Sauvegarder dans la DB locale
    save_vote_to_local_db(vote_req.candidat_numero, vote_hash, my_ip)

    # 4. Propager aux autres nœuds (si target_ip est renseignée)
    if vote_req.target_ip:
        threading.Thread(
            target=propagate_vote, 
            args=(vote_req.target_ip, vote_req.target_port, vote_payload)
        ).start()

    return {"status": "success", "message": "Vote validé, enregistré et propagé !"}


@app.get("/votes")
def read_votes():
    # Récupère tous les votes enregistrés en BDD (pour l'admin)
    return {"votes": get_all_local_votes()}


@app.get("/resultats")
def obtenir_resultats():
    # Récupère le décompte des voix par candidat
    resultats = get_resultats_db()
    return {"status": "success", "resultats": resultats}