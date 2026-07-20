import socket
import threading
import sys
import json

# Notre registre de votes local (base de données en mémoire)
vote_registry = []

def handle_client(client_node, address):
    """Gère les messages reçus d'un client spécifique."""
    try:
        data = client_node.recv(1024).decode('utf-8')
        if not data:
            return
        
        # On décode le message JSON
        payload = json.loads(data)
        message_type = payload.get("type")

        if message_type == "VOTE":
            vote_data = payload.get("data")
            vote_registry.append(vote_data)
            print(f"\n[+] Nouveau vote reçu et enregistré ! Nombre total de votes : {len(vote_registry)}")
            print(f"[Registre actuel] : {vote_registry}")
            
        elif message_type == "SYNC":
            # Un autre nœud demande à voir nos votes (pour plus tard)
            client_node.send(json.dumps(vote_registry).encode('utf-8'))

    except json.JSONDecodeError:
        print(f"\n[-] Erreur : Message reçu non valide (format non JSON)")
    except Exception as e:
        print(f"\n[-] Erreur lors du traitement : {e}")
    finally:
        client_node.close()

def listen_for_connections(host, port):
    """Écoute les connexions entrantes en arrière-plan."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[*] Nœud en écoute sur {host}:{port}")

    while True:
        try:
            client_node, address = server_socket.accept()
            # On lance un thread par connexion pour ne pas bloquer les autres
            client_thread = threading.Thread(target=handle_client, args=(client_node, address))
            client_thread.start()
        except Exception as e:
            print(f"[-] Erreur socket : {e}")
            break

def cast_vote(target_host, target_port, candidate):
    """Envoie un vote structuré à un nœud cible."""
    vote_payload = {
        "type": "VOTE",
        "data": {
            "ballot_id": len(vote_registry) + 1,
            "candidate": candidate,
            "signature": "anon_hash_placeholder" # On s'occupera du chiffrement juste après !
        }
    }
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))
        client_socket.send(json.dumps(vote_payload).encode('utf-8'))
        client_socket.close()
        print(f"[+] Vote pour '{candidate}' envoyé à {target_host}:{target_port}")
    except Exception as e:
        print(f"[-] Échec de l'envoi du vote : {e}")

if __name__ == "__main__":
    my_port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    my_host = "0.0.0.0"

    listener_thread = threading.Thread(target=listen_for_connections, args=(my_host, my_port))
    listener_thread.daemon = True
    listener_thread.start()

    print("=== Commandes : 'vote' pour voter, 'show' pour voir ton registre, 'exit' ===")
    
    while True:
        command = input("> ").strip().lower()
        if command == "exit":
            break
        elif command == "show":
            print(f"Registre local ({len(vote_registry)} votes) : {vote_registry}")
        elif command == "vote":
            target_ip = input("IP du nœud cible : ").strip()
            target_port = int(input("Port du nœud cible : "))
            candidate = input("Nom du candidat (ex: Batman, Superman) : ")
            cast_vote(target_ip, target_port, candidate)