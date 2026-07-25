import socket
import json
import threading
from database import save_vote_to_local_db, get_all_local_votes

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

def listen_for_connections(host: str, port: int):
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

def propagate_vote(target_host: str, target_port: int, vote_payload: dict):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((target_host, target_port))
        s.send(json.dumps(vote_payload).encode('utf-8'))
        s.close()
        print(f"[+] Vote propagé à {target_host}:{target_port}")
    except Exception as e:
        print(f"[-] Échec de la propagation vers {target_host}:{target_port} -> {e}")