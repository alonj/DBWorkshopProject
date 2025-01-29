# search.py
from db_connection import MySQLConnection, load_queries
from config import K1, B, QUERY_FILE


def bm25_search(query_terms, limit=10):
    """
    Execute a BM25 search using the raw SQL from queries.yaml.
    query_terms: list of strings
    """
    # Convert the list of terms into a properly quoted string for SQL
    placeholder_terms = [t.replace("'", "''").replace("\\", "") for t in query_terms]
    placeholder_terms = ",".join([f'"{t}"' for t in placeholder_terms])

    db = MySQLConnection()
    db.connect()
    
    # Load query template
    queries = load_queries(QUERY_FILE)

    # average document length
    avgdl = "SELECT AVG(doc_length) FROM documents;"
    cursor = db.execute(avgdl)
    avgdl = cursor.fetchone()["AVG(doc_length)"]

    raw_sql = queries["search_bm25"]
    
    # Replace placeholders:
    raw_sql = raw_sql.replace(":k1", str(K1))
    raw_sql = raw_sql.replace(":b", str(B))
    raw_sql = raw_sql.replace(":limit", str(limit))
    raw_sql = raw_sql.replace(":query_terms", placeholder_terms)
    raw_sql = raw_sql.replace(":avgdl", str(avgdl))

    # Run
    cursor = db.execute(raw_sql)
    results = cursor.fetchall()
    db.close()
    return results

def get_results_texts(results):
    """
    Given a list of results, return the full text for each result.
    """
    if not results:
        return []
    
    db = MySQLConnection()
    db.connect()
    queries = load_queries()
    raw_sql = queries["get_results_texts"]
    
    # Example: convert doc_ids to "1,2,3"
    id_list = ",".join(str(r["doc_id"]) for r in results)
    raw_sql = raw_sql.replace(":doc_ids", id_list)
    
    cursor = db.execute(raw_sql)
    texts = cursor.fetchall()

    id_to_text = {t["doc_id"]: t["abstract"] for t in texts}
    for r in results:
        r["abstract"] = id_to_text[r["doc_id"]]

    db.close()
    return results

def get_doc_entropy_quartiles(doc_ids):
    """
    Given a list of document IDs, return the entropy quartile for each document.
    """
    if not doc_ids:
        return {}
    db = MySQLConnection()
    db.connect()
    queries = load_queries()
    raw_sql = queries["tfidf_entropy"]
    query = raw_sql.replace(":doc_ids", ",".join(str(i) for i in doc_ids))
    cursor = db.execute(query)
    rows = cursor.fetchall()
    db.close()
    return {row["doc_id"]: row["entropy_quartile"] for row in rows}

def get_keyword_cooccurrences(keywords):
    db = MySQLConnection()
    db.connect()
    queries = load_queries()
    if not keywords or len(keywords) < 2:
        return []
    query = queries["get_keyword_cooccurrences"].replace(":terms", ",".join(f"'{str(k)}'" for k in keywords))
    cursor = db.execute(query)
    rows = cursor.fetchall()
    return rows

def get_keyword_clickthroughs(doc_ids):
    db = MySQLConnection()
    db.connect()
    queries = load_queries()
    if not doc_ids:
        return {}
    query = queries["get_clickthrough_rate"].replace(":doc_ids", ",".join(str(i) for i in doc_ids))
    cursor = db.execute(query)
    rows = cursor.fetchall() # returns document_id, term, clicks
    # Convert to dict of doc_id -> [term, clicks]
    rows_dict = {}
    for row in rows:
        if row["document_id"] not in rows_dict:
            rows_dict[row["document_id"]] = {}
        rows_dict[row["document_id"]][row["term"]] = row["clicks"]
    return rows_dict