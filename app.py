from flask import Flask, render_template, request, session, redirect, url_for
from waitress import serve

import logging
import re
import nltk

from data_loader import load_initial_data
from db_connection import MySQLConnection, load_queries
from search import bm25_search, get_results_texts, get_doc_entropy_quartiles, get_keyword_cooccurrences, get_keyword_clickthroughs
import os, sys

base_dir = '.'
if hasattr(sys, '_MEIPASS'):
    base_dir = os.path.join(sys._MEIPASS)

nltk.download("stopwords")
stopwords = nltk.corpus.stopwords.words("english")

app = Flask(
    __name__,
    # static_folder=os.path.join(base_dir, 'static'),
    # template_folder=os.path.join(base_dir, 'templates')
    )

app.secret_key = "supersecretkey"  # For session management
logging.basicConfig(level=logging.DEBUG)


with app.app_context():
    load_initial_data(force=False)

def highlight_keywords(text, keywords):
    """Highlight keywords in text with different background colors"""
    colors = ['bg-yellow-100', 'bg-blue-100', 'bg-green-100', 'bg-red-100', 'bg-pink-100', 'bg-purple-100', 'bg-indigo-100', 'bg-cyan-100', 'bg-teal-100', 'bg-gray-100']
    highlighted = text
    for idx, keyword in enumerate(keywords):
        color = colors[idx % len(colors)]
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)        
        highlighted = pattern.sub(
            lambda m: f'<span class="{color} px-1 rounded">{m.group()}</span>', 
            highlighted
        )
    return highlighted

app.jinja_env.filters['highlight_keywords'] = lambda text, keywords: highlight_keywords(text, keywords)


@app.route("/")
def start_search():
    session["keywords"] = []
    session["search_results"] = []
    session["beam_docs"] = []
    return redirect(url_for("search_page"))

@app.route("/search", methods=["GET", "POST"])
def search_page():
    results_texts = []
    quartile = request.form.get("quartile", "all")
    if request.method == "POST":
        kw = request.form.get("keyword").split(" ")
        # remove stopwords
        kw = [k for k in kw if k.lower() not in stopwords]
        if kw:
            session["keywords"].extend(kw)
            results_ids = bm25_search(session["keywords"])
            results_texts = get_results_texts(results_ids)
            # Query entropy quartiles
            entropy_map = get_doc_entropy_quartiles([r["doc_id"] for r in results_texts])
            for r in results_texts:
                r["entropy_quartile"] = entropy_map.get(r["doc_id"], "Unknown")
            if quartile != "all":
                results_texts = [r for r in results_texts if r["entropy_quartile"] == quartile]
    cooccurrences = get_keyword_cooccurrences(session["keywords"])
    keyword_clickthroughs = get_keyword_clickthroughs([r["doc_id"] for r in results_texts]) # returns dict of doc_id -> [term, clicks]
    # Add clickthroughs to results_texts
    for r in results_texts:
        r["clicks"] = keyword_clickthroughs.get(r["doc_id"], {})
    return render_template(
        "search.html",
        keywords=session["keywords"],
        search_results=[results_texts] if results_texts else [],
        beam_docs=session.get("beam_docs", []),
        cooccurrences=cooccurrences    
        )

@app.route("/click/<int:doc_id>/<keywords>")
def click_document(doc_id, keywords):
    """
    Simulate a user clicking on a document from the search results
    for a certain keyword in the session. This increments clickthrough.
    """    
    db = MySQLConnection()
    db.connect()
    
    # kw lookup
    keywords_str = ",".join(f"'{str(k)}'" for k in keywords.split(","))
    query = "SELECT id FROM vocabulary WHERE term in (:terms);".replace(":terms", keywords_str)
    db.cursor.execute(query)
    rows = db.cursor.fetchall()
    if not rows:
        db.close()
        return redirect(url_for("search_page"))
    
    # Now increment clickthrough
    queries = load_queries()
    doc_id = str(doc_id)
    keyword_ids = [str(r["id"]) for r in rows]
    for kw_id in keyword_ids:
        raw_sql = queries["update_clickthrough"].replace(":doc_id", doc_id).replace(":term_id", kw_id)
        db.execute(raw_sql)
    db.commit()
    db.close()

    return redirect(url_for("search_page"))

@app.route("/sessions")
def sessions_page():
    """
    Show the current session’s history.
    """
    return render_template("sessions.html",
                           keywords=session.get("keywords", []),
                           results=session.get("search_results", []))

if __name__ == "__main__":
    app.run(debug=False)
    # serve(app, host='0.0.0.0', port=5000, )