import os
import psycopg2
from psycopg2 import pool
from fastapi import HTTPException
from dotenv import load_dotenv
from crypto import hash_password

load_dotenv()

# Récupération de l'URL unique Neon.tech
DATABASE_URL = os.getenv("DATABASE_URL")

# ==========================================
# ⚙️ GESTION DU POOL DE CONNEXIONS (OPTIMISATION)
# ==========================================

try:
    # Création d'un pool basé sur l'URL de connexion (Neon.tech / Cloud)
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=20,
        dsn=DATABASE_URL
    )
    print("[*] Pool de connexions PostgreSQL (Neon.tech) initialisé.")
except Exception as e:
    print(f"[-] Erreur critique lors de la création du pool PostgreSQL : {e}")
    db_pool = None

def get_db_connection():
    """Récupère une connexion disponible depuis le pool."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Base de données inaccessible.")
    try:
        return db_pool.getconn()
    except Exception as e:
        print(f"[-] Pool saturé ou erreur : {e}")
        raise HTTPException(status_code=500, detail="Trop de connexions simultanées.")

def release_db_connection(conn):
    """Remet la connexion dans le pool au lieu de la détruire."""
    if db_pool and conn:
        db_pool.putconn(conn)


# ==========================================
# 🔑 AUTHENTIFICATION & UTILISATEURS
# ==========================================

def verify_user_login(identifiant: str, password: str):
    """Vérifie la connexion (Admin ou Électeur) sans modifier l'état du vote."""
    conn = get_db_connection()
    cur = conn.cursor()
    pwd_hash = hash_password(password)

    try:
        cur.execute("SELECT password_hash FROM administrateurs WHERE identifiant = %s;", (identifiant,))
        admin_row = cur.fetchone()

        if admin_row:
            if admin_row[0] != pwd_hash:
                raise HTTPException(status_code=401, detail="Mot de passe administrateur incorrect.")
            return "admin"

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
        release_db_connection(conn)


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

        cur.execute("UPDATE electeurs SET has_voted = TRUE WHERE cin = %s;", (cin,))
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        release_db_connection(conn)


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
        release_db_connection(conn)


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
        release_db_connection(conn)


def update_candidat_db(numero_original: int, nouveau_numero: int, nouveau_nom: str):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE candidats SET numero = %s, nom = %s WHERE numero = %s;",
            (nouveau_numero, nouveau_nom, numero_original)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur mise à jour candidat : {e}")
    finally:
        cur.close()
        release_db_connection(conn)


def delete_candidat_db(numero: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM candidats WHERE numero = %s;", (numero,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur suppression candidat : {e}")
    finally:
        cur.close()
        release_db_connection(conn)


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
        release_db_connection(conn)


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
        release_db_connection(conn)


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
        release_db_connection(conn)


# ==========================================
# 👥 CRUD ÉLECTEURS
# ==========================================

def get_all_electeurs():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT cin, has_voted FROM electeurs ORDER BY cin ASC;")
        rows = cur.fetchall()
        return [{"cin": r[0], "has_voted": r[1]} for r in rows]
    except Exception as e:
        print(f"[-] Erreur lecture électeurs : {e}")
        return []
    finally:
        cur.close()
        release_db_connection(conn)

def add_electeur_db(cin: str, password: str):
    conn = get_db_connection()
    cur = conn.cursor()
    pwd_hash = hash_password(password)
    try:
        cur.execute(
            "INSERT INTO electeurs (cin, password_hash, has_voted) VALUES (%s, %s, FALSE);",
            (cin, pwd_hash)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"CIN déjà existant ou erreur : {e}")
    finally:
        cur.close()
        release_db_connection(conn)

def reset_voter_status_db(cin: str):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE electeurs SET has_voted = FALSE WHERE cin = %s;", (cin,))
        conn.commit()
    finally:
        cur.close()
        release_db_connection(conn)

def delete_electeur_db(cin: str):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM electeurs WHERE cin = %s;", (cin,))
        conn.commit()
    finally:
        cur.close()
        release_db_connection(conn)


# ==========================================
# 🛡️ CRUD ADMINISTRATEURS
# ==========================================

def get_all_admins():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, identifiant, nom FROM administrateurs ORDER BY id ASC;")
        rows = cur.fetchall()
        return [{"id": r[0], "identifiant": r[1], "nom": r[2]} for r in rows]
    except Exception as e:
        print(f"[-] Erreur lecture admins : {e}")
        return []
    finally:
        cur.close()
        release_db_connection(conn)

def add_admin_db(identifiant: str, nom: str, password: str):
    conn = get_db_connection()
    cur = conn.cursor()
    pwd_hash = hash_password(password)
    try:
        cur.execute(
            "INSERT INTO administrateurs (identifiant, nom, password_hash) VALUES (%s, %s, %s);",
            (identifiant, nom, pwd_hash)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Identifiant admin déjà pris ou erreur : {e}")
    finally:
        cur.close()
        release_db_connection(conn)

def delete_admin_db(identifiant: str):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM administrateurs WHERE identifiant = %s;", (identifiant,))
        conn.commit()
    finally:
        cur.close()
        release_db_connection(conn)