import socket
import json
import threading
import os
from dotenv import load_dotenv
from database import save_vote_to_local_db, get_all_local_votes

load_dotenv()

# Chargement automatique des pairs depuis le fichier .env
PEERS = []
peers_env = os.getenv("PEERS", "")
if peers_env:
    for p in peers_env.split(","):
        if ":" in p:
            host, port = p.split(":")
            PEERS.append((host.strip(), int(port.strip())))

def add_peer(host: str, port: int):
    """Ajoute dynamiquement un nouveau pair au réseau"""
    if (host, port) not in PEERS:
        PEERS.append((host, port))
        print(f"[*] Nouveau pair ajouté au réseau : {host}:{port}")

def send_to_peer(peer_host: str, peer_port: int, payload: dict):
    """Fonction interne pour envoyer un message à un nœud spécifique"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3) # Timeout court pour ne pas bloquer si la machine est hors-ligne
        s.connect((peer_host, peer_port))
        s.send(json.dumps(payload).encode('utf-8'))
        s.close()
        print(f"[+] Vote propagé avec succès vers {peer_host}:{peer_port}")
    except Exception as e:
        print(f"[-] Nœud inaccessible ({peer_host}:{peer_port}) -> {e}")

def propagate_to_all(vote_payload: dict):
    """Propage automatiquement les données à TOUS les nœuds connus, en arrière-plan"""
    for peer_host, peer_port in PEERS:
        # Utilisation d'un thread pour chaque envoi afin de ne pas bloquer l'application
        threading.Thread(
            target=send_to_peer, 
            args=(peer_host, peer_port, vote_payload),
            daemon=True
        ).start()

def handle_client(client_node, address):
    try:
        data = client_node.recv(4096).decode('utf-8')
        if not data:
            return
        payload = json.loads(data)
        
        if payload.get("type") == "VOTE":
            vote_data = payload.get("data")
            # Sauvegarde locale du vote reçu par le réseau
            save_vote_to_local_db(
                vote_data["candidat_numero"], 
                vote_data["vote_hash"], 
                vote_data["node_origin"]
            )
            print(f"\n[+] Vote P2P reçu de {address[0]} et synchronisé !")

        elif payload.get("type") == "SYNC_REQUEST":
            local_votes = get_all_local_votes()
            response = {"type": "SYNC_RESPONSE", "data": local_votes}
            client_node.send(json.dumps(response).encode('utf-8'))

    except Exception as e:
        print(f"[-] Erreur de traitement Socket : {e}")
    finally:
        client_node.close()

def listen_for_connections(host: str, port: int):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(10)
    print(f"[*] Serveur P2P (Sockets TCP) actif et en écoute sur {host}:{port}")
    print(f"[*] Pairs connus au démarrage : {PEERS}")
    
    while True:
        try:
            client_node, address = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_node, address), daemon=True).start()
        except Exception as e:
            print(f"[-] Arrêt du serveur Socket : {e}")
            break