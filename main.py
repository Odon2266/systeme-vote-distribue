import sys
import threading
import uvicorn
from api import app
from p2p import listen_for_connections

if __name__ == "__main__":
    # Récupération des ports depuis la ligne de commande (ou par défaut)
    socket_port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    api_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

    # Lancer le serveur d'écoute Socket TCP en tâche de fond (daemon=True)
    threading.Thread(
        target=listen_for_connections, 
        args=("0.0.0.0", socket_port), 
        daemon=True
    ).start()

    # Lancer le serveur Web FastAPI (Uvicorn)
    print(f"[*] API Web prête sur http://0.0.0.0:{api_port}")
    uvicorn.run(app, host="0.0.0.0", port=api_port)