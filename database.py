import os
import psycopg2
from fastapi import HTTPException
from dotenv import load_dotenv
from crypto import hash_password

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "vote_db")
DB_USER = os.getenv("DB_USER", "odon")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")


def get_db_connection():
    """Établit la connexion à la base de données PostgreSQL."""
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
    except Exception as e:
        print(f"[-] Erreur de connexion à PostgreSQL : {e}")
        raise HTTPException(status_code=500, detail="Impossible de se connecter à la base de données.")


# ==========================================
# 🔑 AUTHENTIFICATION & UTILISATEURS
# ==========================================

def verify_user_login(identifiant: str, password: str):
    """Vérifie la connexion (Admin ou Électeur) sans modifier l'état du vote."""
    conn = get_db_connection()
    cur = conn.cursor()
    pwd_hash = hash_password(password)

    try:
        # 1. Vérifier si l'utilisateur est un Administrateur
        cur.execute("SELECT password_hash FROM administrateurs WHERE identifiant = %s;", (identifiant,))
        admin_row = cur.fetchone()

        if admin_row:
            if admin_row[0] != pwd_hash:
                raise HTTPException(status_code=401, detail="Mot de passe administrateur incorrect.")
            return "admin"

        # 2. Vérifier si l'utilisateur est un Électeur
        cur.execute("SELECT has_voted, password_hash FROM electeurs WHERE cin = %s;", (identifiant,))
        voter_row = cur.fetchone()

        if not voter_row:
            raise HTTPException(status_code=404, detail="CIN ou identifiant inconnu.")

        has_voted, stored_pwd_hash = voter_row

        if stored_pwd_hash != pwd_hash:
            raise HTTPException(status_code=401, detail="Mot de passe incorrect.")

        if has_voted:
            raise HTTPException(status_code=400, detail="Vous avez déjà voté ! Action impossible.")

        return "voter"

    finally:
        cur.close()
        conn.close()


def verify_and_mark_voter(cin: str, password: str):
    """Vérifie le mot de passe de l'électeur ET le marque comme 'a voté' (has_voted = TRUE)."""
    conn = get_db_connection()
    cur = conn.cursor()
    pwd_hash = hash_password(password)

    try:
        cur.execute("SELECT has_voted, password_hash FROM electeurs WHERE cin = %s;", (cin,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Électeur non trouvé.")

        has_voted, stored_pwd_hash = row

        if stored_pwd_hash != pwd_hash:
            raise HTTPException(status_code=401, detail="Mot de passe incorrect.")

        if has_voted:
            raise HTTPException(status_code=400, detail="Vous avez déjà voté !")

        # Marquer l'électeur comme ayant voté
        cur.execute("UPDATE electeurs SET has_voted = TRUE WHERE cin = %s;", (cin,))
        conn.commit()

    finally:
        cur.close()
        conn.close()


# ==========================================
# 🗳️ GESTION DES CANDIDATS
# ==========================================

def get_all_candidats():
    """Récupère la liste de tous les candidats."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT numero, nom FROM candidats ORDER BY numero ASC;")
        rows = cur.fetchall()
        return [{"id": r[0], "numero": r[0], "nom": r[1]} for r in rows]
    except Exception as e:
        print(f"[-] Erreur lecture candidats : {e}")
        return []
    finally:
        cur.close()
        conn.close()


def add_candidat_db(numero: int, nom: str):
    """Insère un nouveau candidat dans PostgreSQL."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO candidats (numero, nom) VALUES (%s, %s);", (numero, nom))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Numéro déjà attribué ou erreur : {e}")
    finally:
        cur.close()
        conn.close()


# ==========================================
# 📊 GESTION DES VOTES ET RÉSULTATS
# ==========================================

def save_vote_to_local_db(candidat_numero: int, vote_hash: str, node_origin: str):
    """Insère un vote anonyme dans la table 'votes'."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO votes (candidat_numero, vote_hash, node_origin)
            VALUES (%s, %s, %s)
            ON CONFLICT (vote_hash) DO NOTHING;
        """, (candidat_numero, vote_hash, node_origin))
        conn.commit()
        print(f"[DB] Vote {vote_hash[:10]}... enregistré avec succès.")
    except Exception as e:
        conn.rollback()
        print(f"[-] Erreur sauvegarde vote locale : {e}")
    finally:
        cur.close()
        conn.close()


def get_all_local_votes():
    """Récupère l'historique complet des votes anonymes."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT v.id, v.candidat_numero, c.nom, v.vote_hash, v.created_at, v.node_origin 
            FROM votes v
            LEFT JOIN candidats c ON v.candidat_numero = c.numero
            ORDER BY v.id ASC;
        """)
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "candidat_numero": r[1],
                "candidat_nom": r[2] or f"Candidat N°{r[1]}",
                "vote_hash": r[3],
                "created_at": str(r[4]),
                "node_origin": r[5]
            } for r in rows
        ]
    except Exception as e:
        print(f"[-] Erreur lecture votes : {e}")
        return []
    finally:
        cur.close()
        conn.close()


def get_resultats_db():
    """Calcule le décompte des voix par candidat."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.numero, c.nom, COUNT(v.id) as total_votes 
            FROM candidats c 
            LEFT JOIN votes v ON c.numero = v.candidat_numero 
            GROUP BY c.numero, c.nom
            ORDER BY total_votes DESC;
        """)
        resultats = cur.fetchall()
        return [{"numero": r[0], "nom": r[1], "votes": r[2]} for r in resultats]
    except Exception as e:
        print(f"[-] Erreur calcul résultats : {e}")
        return []
    finally:
        cur.close()
        conn.close()