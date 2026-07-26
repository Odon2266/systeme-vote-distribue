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
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def save_vote_to_local_db(candidat_numero: int, vote_hash: str, node_origin: str):
    """Insère un vote anonyme dans la table votes locale."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO votes (candidat_numero, vote_hash, node_origin)
            VALUES (%s, %s, %s)
            ON CONFLICT (vote_hash) DO NOTHING;
        """, (candidat_numero, vote_hash, node_origin))
        conn.commit()
        cur.close()
        conn.close()
        print(f"[DB] Vote {vote_hash[:10]}... enregistré dans PostgreSQL.")
    except Exception as e:
        print(f"[-] Erreur DB locale : {e}")

def get_all_local_votes():
    """Récupère tous les votes enregistrés."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT v.id, v.candidat_numero, c.nom, v.vote_hash, v.created_at, v.node_origin 
            FROM votes v
            LEFT JOIN candidats c ON v.candidat_numero = c.numero
            ORDER BY v.id ASC;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0],
                "candidat_numero": r[1],
                "candidat_nom": r[2],
                "vote_hash": r[3],
                "created_at": str(r[4]),
                "node_origin": r[5]
            } for r in rows
        ]
    except Exception as e:
        print(f"[-] Erreur lecture DB : {e}")
        return []

def verify_and_mark_voter(cin: str, password: str):
    """Vérifie les identifiants de l'électeur et coche has_voted = True."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    pwd_hash = hash_password(password)
    
    cur.execute("SELECT has_voted, password_hash FROM electeurs WHERE cin = %s;", (cin,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Électeur non trouvé (CIN invalide).")
    
    has_voted, stored_pwd_hash = row
    
    print("\n" + "="*50)
    print(f"🔍 DEBUG LOGIN POUR LE CIN : '{cin}'")
    print(f"Mot de passe brut reçu du terminal : '{password}'")
    print(f"Hash calculé par Python            : '{pwd_hash}'")
    print(f"Hash lu depuis PostgreSQL          : '{stored_pwd_hash}'")
    print("="*50 + "\n")

    if stored_pwd_hash != pwd_hash:
        cur.close()
        conn.close()
        raise HTTPException(status_code=401, detail="Mot de passe incorrect.")
        
    if has_voted:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Vous avez déjà voté !")

    cur.execute("UPDATE electeurs SET has_voted = TRUE WHERE cin = %s;", (cin,))
    conn.commit()
    cur.close()
    conn.close()

def get_resultats_db():
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        # Requête pour compter les votes par candidat
        cursor.execute("""
            SELECT c.numero, c.nom, COUNT(v.id) as total_votes 
            FROM candidats c 
            LEFT JOIN votes v ON c.numero = v.candidat_numero 
            GROUP BY c.numero, c.nom
            ORDER BY total_votes DESC;
        """)
        resultats = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Formatage des résultats en liste de dictionnaires
        return [{"numero": r[0], "nom": r[1], "votes": r[2]} for r in resultats]
    except Exception as e:
        print(f"[-] Erreur lors du calcul des résultats : {e}")
        if conn:
            conn.close()
        return []

def get_all_candidats():
    """Récupère la liste de tous les candidats depuis PostgreSQL."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT numero, nom, parti FROM candidats ORDER BY numero ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0],
                "numero": r[0],
                "nom": r[1],
                "parti": r[2]
            } for r in rows
        ]
    except Exception as e:
        print(f"[-] Erreur lecture candidats : {e}")
        return []

def verify_login_only(cin: str, password: str):
    """Vérifie uniquement les identifiants sans cocher la case a voté."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    pwd_hash = hash_password(password)
    
    cur.execute("SELECT has_voted, password_hash FROM electeurs WHERE cin = %s;", (cin,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Électeur non trouvé.")
    
    has_voted, stored_pwd_hash = row

    if stored_pwd_hash != pwd_hash:
        cur.close()
        conn.close()
        raise HTTPException(status_code=401, detail="Mot de passe incorrect.")
        
    if has_voted:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Vous avez déjà voté ! Action impossible.")

    cur.close()
    conn.close()
    return True