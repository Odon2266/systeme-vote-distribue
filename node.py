import socket
import threading
import sys

def listen_for_connections(host, port):
    """Fonction exécutée en arrière-plan pour écouter les autres nœuds."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permet de réutiliser le port immédiatement après l'arrêt du script
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[*] Nœud en écoute sur {host}:{port}")

    while True:
        try:
            client_node, address = server_socket.accept()
            print(f"\n[+] Connexion reçue de {address[0]}:{address[1]}")
            
            # Lecture du message reçu
            message = client_node.recv(1024).decode('utf-8')
            print(f"[Message reçu] : {message}")
            
            client_node.close()
        except Exception as e:
            print(f"[-] Erreur d'écoute : {e}")
            break

def send_message(target_host, target_port, message):
    """Fonction pour envoyer un message à un autre nœud."""
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_host, target_port))
        client_socket.send(message.encode('utf-8'))
        client_socket.close()
        print(f"[+] Message envoyé avec succès à {target_host}:{target_port}")
    except Exception as e:
        print(f"[-] Impossible de se connecter à {target_host}:{target_port} : {e}")

if __name__ == "__main__":
    # On récupère le port d'écoute locale via les arguments du terminal, sinon 5000 par défaut
    my_port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    my_host = "0.0.0.0" # Écoute sur toutes les interfaces réseau, y compris Tailscale

    # Démarrage du thread d'écoute pour ne pas bloquer le terminal
    listener_thread = threading.Thread(target=listen_for_connections, args=(my_host, my_port))
    listener_thread.daemon = True # S'arrête automatiquement quand le programme principal se coupe
    listener_thread.thread_name = "Listener"
    listener_thread.start()

    print("=== Commandes disponibles : 'send' pour envoyer un message, 'exit' pour quitter ===")
    
    # Boucle principale pour interagir avec le terminal
    while True:
        command = input("> ").strip().lower()
        if command == "exit":
            print("Fermeture du nœud...")
            break
        elif command == "send":
            target_ip = input("IP du nœud cible : ").strip()
            target_port = int(input("Port du nœud cible : "))
            msg = input("Votre message/vote : ")
            send_message(target_ip, target_port, msg)