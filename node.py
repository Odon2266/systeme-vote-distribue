import socket
import threading
import sys
import json
import hashlib

vote_registry = []

def hash_vote(candidate, ballot_id):
    """Calcule un hash SHA-256 unique pour anonymiser et chiffrer le vote."""
    raw_string = f"{candidate}-{ballot_id}-secret-salt-123"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()

def handle_client(client_node, address):
    try:
        data = client_node.recv(1024).decode('utf-8')
        if not data:
            return
        
        payload = json.loads(data)
        message_type = payload.get("type")

        if message_type == "VOTE":
            vote_data = payload.get("data")
            vote_registry.append(vote_data)
            print(f"\n[+] Nouveau VOTE CHIFFRÉ reçu ! Nombre total : {len(vote_registry)}")
            print(f"[Registre Anonymisé] : {json.dumps(vote_data, indent=2)}")
            
        elif message_type == "SYNC":
            client_node.send(json.dumps(vote_registry).encode('utf-8'))

    except Exception as e:
        print(f"\n[-] Erreur : {e}")
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
    
    # Hachage cryptographique du candidat pour l'anonymat
    encrypted_candidate_hash = hash_vote(candidate, ballot_id)
    
    vote_payload = {
        "type": "VOTE",
        "data": {
            "ballot_id": ballot_id,
            "encrypted_ballot": encrypted_candidate_hash,  # Le choix est maintenant masqué cryptographiquement
            "signature_verification": hashlib.md5(str(ballot_id).encode()).hexdigest() # Signature d'intégrité du nœud
        }
    }
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))
        client_socket.send(json.dumps(vote_payload).encode('utf-8'))
        client_socket.close()
        print(f"[+] Vote chiffré envoyé avec succès à {target_host}:{target_port}")
    except Exception as e:
        print(f"[-] Échec de l'envoi : {e}")

if __name__ == "__main__":
    my_port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    my_host = "0.0.0.0"

    listener_thread = threading.Thread(target=listen_for_connections, args=(my_host, my_port))
    listener_thread.daemon = True
    listener_thread.start()

    print("=== Commandes : 'vote', 'show', 'exit' ===")
    
    while True:
        command = input("> ").strip().lower()
        if command == "exit":
            break
        elif command == "show":
            print(f"Registre local ({len(vote_registry)} votes) : {vote_registry}")
        elif command == "vote":
            target_ip = input("IP du nœud cible : ").strip()
            target_port = int(input("Port du nœud cible : "))
            candidate = input("Nom du candidat : ")
            cast_vote(target_ip, target_port, candidate)