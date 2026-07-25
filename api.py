import socket
import threading
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import verify_and_mark_voter, save_vote_to_local_db, get_all_local_votes
from crypto import hash_vote
from p2p import propagate_vote

app = FastAPI(title="P2P Voting Node API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VoteSchema(BaseModel):
    cin: str
    password: str
    candidat_numero: int
    target_ip: Optional[str] = None
    target_port: int = 6000

@app.get("/votes")
def read_votes():
    return {"votes": get_all_local_votes()}

@app.post("/vote")
def receive_vote_from_web(vote_req: VoteSchema):
    # 1. Vérifier l'électeur et marquer 'has_voted' = True
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

    # 4. Propager aux autres nœuds (si target_ip renseignée)
    if vote_req.target_ip:
        threading.Thread(
            target=propagate_vote, 
            args=(vote_req.target_ip, vote_req.target_port, vote_payload)
        ).start()

    return {"status": "success", "message": "Vote validé, enregistré et propagé !"}