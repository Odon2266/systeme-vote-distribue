import os
import socket
import threading
import sys
import json
import hashlib
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 🤫 Chargement des variables d'environnement depuis le fichier .env
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

def save_vote_to_local_db(ballot_id, encrypted_ballot, signature_verification):
    """Insère un vote dans la base PostgreSQL locale s'il n'existe pas déjà."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO votes (ballot_id, encrypted_ballot, signature_verification)
            VALUES (%s, %s, %s)
            ON CONFLICT (ballot_id) DO NOTHING;
        """, (ballot_id, encrypted_ballot, signature_verification))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[DB] Vote {ballot_id} enregistré dans PostgreSQL local.")
    except Exception as e:
        print(f"[-] Erreur DB locale : {e}")

def get_all_local_votes():
    """Récupère la liste des votes depuis la base locale."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT ballot_id, encrypted_ballot, signature_verification FROM votes ORDER BY ballot_id ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"ballot_id": r[0], "encrypted_ballot": r[1], "signature_verification": r[2]} for r in rows]
    except Exception as e:
        print(f"[-] Erreur lecture DB locale : {e}")
        return []

def hash_vote(candidate, ballot_id):
    raw_string = f"{candidate}-{ballot_id}-{SECRET_SALT}"
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
                vote_data["ballot_id"], 
                vote_data["encrypted_ballot"], 
                vote_data["signature_verification"]
            )
            print(f"\n[+] Vote chiffré reçu via Socket TCP !")

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

@app.get("/votes")
def read_votes():
    return {"votes": get_all_local_votes()}

@app.post("/vote")
def receive_vote_from_web(data: dict):
    candidate = data.get("candidate")
    target_ip = data.get("target_ip")
    target_port = data.get("target_port", 6000)

    current_votes = get_all_local_votes()
    ballot_id = len(current_votes) + 1
    encrypted_hash = hash_vote(candidate, ballot_id)
    
    vote_payload = {
        "type": "VOTE",
        "data": {
            "ballot_id": ballot_id,
            "encrypted_ballot": encrypted_hash,
            "signature_verification": hashlib.md5(str(ballot_id).encode()).hexdigest()
        }
    }

    save_vote_to_local_db(ballot_id, encrypted_hash, vote_payload["data"]["signature_verification"])

    if target_ip:
        threading.Thread(target=propagate_vote, args=(target_ip, target_port, vote_payload)).start()

    return {"status": "success", "message": "Vote enregistré et propagé !"}

if __name__ == "__main__":
    socket_port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    api_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

    threading.Thread(target=listen_for_connections, args=("0.0.0.0", socket_port), daemon=True).start()

    print(f"[*] API Web prête sur http://0.0.0.0:{api_port}")
    uvicorn.run(app, host="0.0.0.0", port=api_port)