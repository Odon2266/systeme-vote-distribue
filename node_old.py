import os
import socket
import threading
import sys
import json
import hashlib
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 🤫 Chargement des variables d'environnement
load_dotenv()

DB_NAME = os.getenv("DB_NAME", "vote_db")
DB_USER = os.getenv("DB_USER", "odon")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
SECRET_SALT = os.getenv("SECRET_SALT", "default_salt")

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

# --- FONCTIONS BASE DE DONNÉES ---

def save_vote_to_local_db(candidat_numero, vote_hash, node_origin):
    """Insère un vote anonyme dans la table votes locale."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO votes (candidat_numero, vote_hash, node_origin)
            VALUES (%s, %s, %s)
            ON CONFLICT (vote_hash) DO NOTHING;
        """, (candidat_numero, vote_hash, node_origin))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[DB] Vote {vote_hash[:10]}... enregistré dans PostgreSQL.")
    except Exception as e:
        print(f"[-] Erreur DB locale : {e}")

def get_all_local_votes():
    """Récupère tous les votes enregistrés."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT v.id, v.candidat_numero, c.nom, v.vote_hash, v.created_at, v.node_origin 
            FROM votes v
            LEFT JOIN candidats c ON v.candidat_numero = c.numero
            ORDER BY v.id ASC;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0],
                "candidat_numero": r[1],
                "candidat_nom": r[2],
                "vote_hash": r[3],
                "created_at": str(r[4]),
                "node_origin": r[5]
            } for r in rows
        ]
    except Exception as e:
        print(f"[-] Erreur lecture DB : {e}")
        return []

def verify_and_mark_voter(cin, password):
    """Vérifie les identifiants de l'électeur et coche has_voted = True."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Hachage simple du mot de passe fourni pour comparaison (SHA-256)
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    
    cur.execute("SELECT has_voted, password_hash FROM electeurs WHERE cin = %s;", (cin,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Électeur non trouvé (CIN invalide).")
    
    has_voted, stored_pwd_hash = row
    
    # --- DÉBUT DU BLOC DE DEBUG À AJOUTER ---
    print("\n" + "="*50)
    print(f"🔍 DEBUG LOGIN POUR LE CIN : '{cin}'")
    print(f"Mot de passe brut reçu du terminal : '{password}'")
    print(f"Hash calculé par Python            : '{pwd_hash}'")
    print(f"Hash lu depuis PostgreSQL          : '{stored_pwd_hash}'")
    print("="*50 + "\n")
    # --- FIN DU BLOC DE DEBUG ---

    if stored_pwd_hash != pwd_hash:
        cur.close()
        conn.close()
        raise HTTPException(status_code=401, detail="Mot de passe incorrect.")
        
    if has_voted:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Vous avez déjà voté !")

    # Marquer comme ayant voté
    cur.execute("UPDATE electeurs SET has_voted = TRUE WHERE cin = %s;", (cin,))
    conn.commit()
    cur.close()
    conn.close()
def hash_vote(cin, candidat_numero):
    """Génère un hash SHA-256 unique pour garantir l'immuabilité du vote."""
    raw_string = f"{cin}-{candidat_numero}-{SECRET_SALT}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()

# --- GESTION DES SOCKETS TCP (RÉSEAU P2P) ---

def handle_client(client_node, address):
    try:
        data = client_node.recv(4096).decode('utf-8')
        if not data:
            return
        payload = json.loads(data)
        
        if payload.get("type") == "VOTE":
            vote_data = payload.get("data")
            save_vote_to_local_db(
                vote_data["candidat_numero"], 
                vote_data["vote_hash"], 
                vote_data["node_origin"]
            )
            print(f"\n[+] Vote chiffré reçu du réseau P2P !")

        elif payload.get("type") == "SYNC_REQUEST":
            local_votes = get_all_local_votes()
            response = {"type": "SYNC_RESPONSE", "data": local_votes}
            client_node.send(json.dumps(response).encode('utf-8'))

    except Exception as e:
        print(f"[-] Erreur traitement Socket : {e}")
    finally:
        client_node.close()

def listen_for_connections(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[*] Sockets TCP en écoute sur {host}:{port}")
    while True:
        try:
            client_node, address = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_node, address)).start()
        except:
            break

def propagate_vote(target_host, target_port, vote_payload):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((target_host, target_port))
        s.send(json.dumps(vote_payload).encode('utf-8'))
        s.close()
        print(f"[+] Vote propagé à {target_host}:{target_port}")
    except Exception as e:
        print(f"[-] Échec de la propagation vers {target_host}:{target_port} -> {e}")

# --- API WEB FASTAPI ---

app = FastAPI()

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
    target_ip: str = None
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

if __name__ == "__main__":
    socket_port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    api_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

    threading.Thread(target=listen_for_connections, args=("0.0.0.0", socket_port), daemon=True).start()

    print(f"[*] API Web prête sur http://0.0.0.0:{api_port}")
    uvicorn.run(app, host="0.0.0.0", port=api_port)