# data_loader.py
import os
from db_connection import MySQLConnection, load_queries
from config import DATASET_DIR, QUERY_FILE
import json
from collections import Counter
from tqdm import tqdm

def load_dataset(path):
    """
    Load a dataset from a file.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(path, "r") as f:
        # read lines
        lines = f.readlines()
    return lines

def process_keywords(text):
    # Dummy function for now
    return []

def process_dataset(path):
    """
    Process a dataset into a list of dictionaries.
    """

    data = load_dataset(path)
    dataset_name = path.split("/")[-1].split(".")[0]

    if not data:
        return []
    
    output = []
    for line in data:
        line_ = json.loads(line)
        text = line_['sentences']
        categories = line_['labels'].split(",")
        keywords = process_keywords(text)
        output.append({
            "text": text.replace("'", "").replace('"', '').replace("\\", ""),
            "categories": categories,
            "keywords": keywords,
            "dataset": dataset_name,
            "length": len(text)
        })

    return output


def load_initial_data(force=False):
    """
    If force=True, forcibly re-load data.
    Otherwise, only load if some minimal condition is not met.
    """

    queries = load_queries(QUERY_FILE)
    db = MySQLConnection()
    db.connect()

    db.execute("SELECT COUNT(*) as cnt FROM categories")
    row = db.cursor.fetchone()
    if row["cnt"] > 0 and not force:
        print("Data already exists; skipping initial load.")
        db.close()
        return

    # Load the datasets
    datasets = os.listdir(DATASET_DIR)
    if not datasets:
        raise FileNotFoundError("No datasets found.")
    
    data = []
    for dataset in datasets[::-1]:
        data += process_dataset(os.path.join(DATASET_DIR, dataset))

    # Sampling the data
    data = data[:15_000]
    
    dataset_names = set()
    for item in data:
        dataset_names.add(item["dataset"])
    for name in dataset_names:
        db.execute("INSERT INTO datasets (name) VALUES (%s)", (name,))
    db.commit()

    # get dataset->id mapping
    db.execute("SELECT id, name FROM datasets")
    dataset_map = {row["name"]: row["id"] for row in db.cursor.fetchall()}
    
    categories = set()
    for item in data:
        categories |= set(item["categories"])
    for cat in categories:
        q = queries["insert_category"].format(category_name=cat)
        db.execute(q)
    
    db.commit()

    # get category->id mapping
    db.execute("SELECT id, name FROM categories")
    cat_map = {row["name"]: row["id"] for row in db.cursor.fetchall()}
    row = db.cursor.fetchone()
    # if row["cnt"] < 1:
    #     db.close()
    #     raise Exception("Failed to insert categories.")    
    
    docs = []
    for item in data:
        cat_ids = [cat_map[cat] for cat in item["categories"]][0]
        docs.append((item["text"], cat_ids, item["length"]))
        
    for (abstract, cat_id, length) in tqdm(docs, desc="Inserting documents"):
        dataset_name = item["dataset"]
        q = queries["insert_document"].format(
            abstract=abstract.replace("'", "''"),
            category_id=cat_id,
            doc_length=length,
            dataset_id=dataset_map[dataset_name]
        )
        db.execute(q)
    db.commit()

    # abstract -> doc_id mapping
    db.execute("SELECT id, abstract FROM documents")
    doc_map = {row["abstract"]: row["id"] for row in db.cursor.fetchall()}

    vocab = set()
    for item in data:
        vocab.update(item["text"].lower().split())
    for word in tqdm(vocab, desc="Inserting vocabulary"):
        # escape single quotes
        q = queries["insert_vocabulary"].format(word=word)
        db.execute(q)
    db.commit()

    # get vocab->id mapping
    db.execute("SELECT id, term FROM vocabulary")
    vocab_map = {row["term"]: row["id"] for row in db.cursor.fetchall()}

    # Insert document-vocabulary pair counts (double primary key on doc_id, vocab_id)
    doc_voc_counter = Counter()
    for item in data:

        doc_id = doc_map[item["text"]]
        vocab_ids = [vocab_map[word] for word in item["text"].lower().split()]
        for vocab_id in vocab_ids:
            doc_voc_counter[(doc_id, vocab_id)] += 1

    for (doc_id, vocab_id), freq in tqdm(doc_voc_counter.items(), desc="Inserting document-vocabulary pairs"):
        q = queries["insert_document_vocabulary"].format(
            doc_id=doc_id,
            vocabulary_id=vocab_id,
            term_frequency=1
        )
        db.execute(q)
    db.commit()
    

    # Insert sample keywords & doc-keywords
    keywords = [
      ("gene", 1), ("covid", 2), ("forest", 3)
    ]
    for kw, vocab_id in keywords:
        q = queries["insert_keyword"].format(
            keyword=kw,
            vocabulary_id=vocab_id
        )
        db.execute(q)
    
    db.commit()

    ## Dummy data, to be replaced with real data

    # doc_keywords
    doc_keywords_data = [
      (1, 1, 3),  # doc1 - keyword1 freq=3
      (2, 2, 5),  # doc2 - keyword2 freq=5
      (3, 3, 2)   # doc3 - keyword3 freq=2
    ]
    for (doc_id, kw_id, freq) in doc_keywords_data:
        q = queries["insert_document_keyword"].format(
            doc_id=doc_id,
            keyword_id=kw_id,
            term_frequency=freq
        )
        db.execute(q)
    
    # insert document_frequencies (# of docs containing a term)
    docs_, vocs_ = zip(*doc_voc_counter.keys())
    vocs_counter = Counter(vocs_)
    n_data = len(data)
    for vocab_id in tqdm(vocab_map.values(), desc="Inserting document frequencies"):
        df = vocs_counter[vocab_id]
        idf = n_data / df
        
        q = queries["insert_document_frequency"].format(
            vocabulary_id=vocab_id,
            doc_freq=df,
            idf=idf
        )
        db.execute(q)
    db.commit()

    # Insert doc_doc_similarities (sample beam search data)
    db.execute("INSERT INTO doc_doc_similarities (doc_id1, doc_id2, similarity) VALUES (1,2,0.8), (1,3,0.4), (2,3,0.5)")
    
    db.commit()
    db.close()
    print("Initial data loaded.")
