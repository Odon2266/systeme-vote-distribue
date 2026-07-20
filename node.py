import socket
import threading
import sys
import json
import hashlib

vote_registry = []

def hash_vote(candidate, ballot_id):
    raw_string = f"{candidate}-{ballot_id}-secret-salt-123"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()

def handle_client(client_node, address):
    global vote_registry
    try:
        data = client_node.recv(4096).decode('utf-8')  # Augmenté à 4096 pour les gros registres
        if not data:
            return
        
        payload = json.loads(data)
        message_type = payload.get("type")

        if message_type == "VOTE":
            vote_data = payload.get("data")
            # Évite d'ajouter des doublons basés sur le ballot_id
            if vote_data not in vote_registry:
                vote_registry.append(vote_data)
                print(f"\n[+] Nouveau VOTE CHIFFRÉ reçu ! Total : {len(vote_registry)}")
            
        elif message_type == "SYNC_REQUEST":
            # Un nœud nous demande nos votes, on lui répond en renvoyant tout le registre
            response = {"type": "SYNC_RESPONSE", "data": vote_registry}
            client_node.send(json.dumps(response).encode('utf-8'))

    except Exception as e:
        print(f"\n[-] Erreur lors du traitement du message : {e}")
    finally:
        client_node.close()

def listen_for_connections(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[*] Nœud en écoute sur {host}:{port}")

    while True:
        try:
            client_node, address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_node, address))
            client_thread.start()
        except Exception as e:
            break

def cast_vote(target_host, target_port, candidate):
    ballot_id = len(vote_registry) + 1
    encrypted_candidate_hash = hash_vote(candidate, ballot_id)
    
    vote_payload = {
        "type": "VOTE",
        "data": {
            "ballot_id": ballot_id,
            "encrypted_ballot": encrypted_candidate_hash,
            "signature_verification": hashlib.md5(str(ballot_id).encode()).hexdigest()
        }
    }
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))
        client_socket.send(json.dumps(vote_payload).encode('utf-8'))
        client_socket.close()
        print(f"[+] Vote chiffré envoyé à {target_host}:{target_port}")
    except Exception as e:
        print(f"[-] Échec de l'envoi : {e}")

def request_synchronization(target_host, target_port):
    """Demande le registre complet d'un autre nœud pour synchroniser le nôtre."""
    global vote_registry
    sync_payload = {"type": "SYNC_REQUEST"}
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))
        client_socket.send(json.dumps(sync_payload).encode('utf-8'))
        
        # Réception de la réponse
        response_data = client_socket.recv(4096).decode('utf-8')
        payload = json.loads(response_data)
        
        if payload.get("type") == "SYNC_RESPONSE":
            remote_registry = payload.get("data", [])
            # Fusion des registres sans doublons
            count = 0
            for vote in remote_registry:
                if vote not in vote_registry:
                    vote_registry.append(vote)
                    count += 1
            print(f"[+] Synchronisation réussie ! {count} nouveaux votes récupérés depuis le réseau.")
        
        client_socket.close()
    except Exception as e:
        print(f"[-] Échec de la synchronisation : {e}")

if __name__ == "__main__":
    my_port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    my_host = "0.0.0.0"

    listener_thread = threading.Thread(target=listen_for_connections, args=(my_host, my_port))
    listener_thread.daemon = True
    listener_thread.start()

    print("=== Commandes : 'vote', 'sync', 'show', 'exit' ===")
    
    while True:
        command = input("> ").strip().lower()
        if command == "exit":
            break
        elif command == "show":
            print(f"Registre local ({len(vote_registry)} votes) :\n{json.dumps(vote_registry, indent=2)}")
        elif command == "vote":
            target_ip = input("IP du nœud cible : ").strip()
            target_port = int(input("Port du nœud cible : "))
            candidate = input("Nom du candidat : ")
            cast_vote(target_ip, target_port, candidate)
        elif command == "sync":
            target_ip = input("IP du nœud à synchroniser : ").strip()
            target_port = int(input("Port du nœud à synchroniser : "))
            request_synchronization(target_ip, target_port)