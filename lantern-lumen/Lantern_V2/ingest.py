# =============================================================
# LANTERN INTELLIGENCE v2 — ingest.py
# Phase 2: Embed and store financial concept documents
# =============================================================
# WHAT THIS SCRIPT DOES:
#   1. Reads all 8 .txt concept documents from knowledge_base/
#   2. Embeds each document into a vector using sentence-transformers
#   3. Stores the vectors + original text in ChromaDB on disk
#   4. Runs a verification query to confirm retrieval works
#
# RUN THIS ONCE. After it completes, ChromaDB is loaded and
# ready. You do not need to run it again unless documents change.
# =============================================================

import os
import chromadb

from sentence_transformers import SentenceTransformer

KNOWLEDGE_BASE_DIR = "/workspace/lantern-lumen/Lantern_V2/knowledge_base"
CHROMA_STORE_DIR = "/workspace/lantern-lumen/Lantern_V2/chroma_store"
COLLECTION_NAME = 'lantern_financial_concepts'

# -------------------------------------------------------------
# STEP 1: LOAD THE EMBEDDING MODEL
# -------------------------------------------------------------
# SentenceTransformer converts text into vectors.
# "all-MiniLM-L6-v2" is small, fast, and excellent at
# semantic similarity tasks — perfect for RAG retrieval.
# The first run downloads the model (~90MB). After that
# it loads from local cache instantly.
# -------------------------------------------------------------

print("Loading embedding models....")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
print("Model Loaded.\n")

# -------------------------------------------------------------
# STEP 2: CONNECT TO CHROMADB (persistent on disk)
# -------------------------------------------------------------
# PersistentClient tells ChromaDB to save everything to disk
# at CHROMA_STORE_DIR. This means your embeddings survive
# between runs — you don't have to re-embed every time.
# -------------------------------------------------------------

print(f"Connecting to ChromaDB at : {CHROMA_STORE_DIR}")
chroma_client = chromadb.PersistentClient(path=CHROMA_STORE_DIR)

# -------------------------------------------------------------
# STEP 3: CREATE (OR LOAD) A COLLECTION
# -------------------------------------------------------------
# A ChromaDB collection is like a table in SQL — it holds
# a set of related documents and their vectors.
# get_or_create_collection: if it already exists, load it.
# If not, create it fresh. Safe to run multiple times.
# -------------------------------------------------------------

collection = chroma_client.get_or_create_collection(
    name = COLLECTION_NAME,
    # This tells ChromaDB how to measure similarity between vectors.
    # "cosine" means: find documents whose meaning is closest to
    # the query, regardless of document length. Best for text.
    metadata = {"hnsw:space": "cosine"}
)
print(f"Collection '{COLLECTION_NAME}' ready. \n")

# -------------------------------------------------------------
# STEP 4: READ ALL .TXT FILES FROM KNOWLEDGE BASE DIRECTORY
# -------------------------------------------------------------

print(f"Readinf documents from: {KNOWLEDGE_BASE_DIR}\n")

documents = [] # for raw text of each document
doc_ids = [] # unique id for each document in ChromaDB
metadatas = [] # extra info stored alongside each document

txt_files = sorted([
    f for f in os.listdir(KNOWLEDGE_BASE_DIR)
    if f.endswith('.txt')
])

if not txt_files:
    print("Error: no .txt file found in knowlege_base/")
    print("Make sure necessary concepts are uploaded/")
    exit(1)

for filename in txt_files:
    filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    #use the filename (without, txt) as the document ID
    doc_id = filename.replace(".txt", "")
    # Extract the metric name from the first line of the file
    # e.g. "METRIC: Net Profit Margin" → "Net Profit Margin"
    first_line = text.split("\n")[0]
    metric_name = first_line.replace("METRIC:", "").strip()
    documents.append(text)
    doc_ids.append(doc_id)
    metadatas.append({
        "filename": filename,
        "metric": metric_name,
        "source": "lanter_concept_doc"
    })
    print(f"Loaded: {filename} ({len(text)} characters)")
print(f"\n{len(documents)} documents loaded.\n")

# -------------------------------------------------------------
# STEP 5: EMBED AND STORE IN CHROMADB
# -------------------------------------------------------------
# Here's where the magic happens.
# embedding_model.encode() converts each text document into
# a list of 384 numbers (a vector) that represents its meaning.
# ChromaDB stores both the vector and the original text together.
# When you search later, it compares vectors to find the
# most semantically similar documents to your query.
# -------------------------------------------------------------

print("Embedding documents and storing in ChromaDB ....")
embeddings = embedding_model.encode(documents).tolist()
# .tolist() converts numpy arrays to plain Python lists
# which is what ChromaDB expects

#check if documents alreadu exist to avoid duplicates
existing = collection.get(ids=doc_ids)  
existing_ids = existing["ids"]

new_docs = []
new_embeddings = []
new_ids = []
new_metadatas = []

for i , doc_id in enumerate(doc_ids):
    if doc_id in existing_ids:
        print(f" Skipping (already exists): {doc_id}")
    else:
        new_docs.append(documents[i])
        new_embeddings.append(embeddings[i])
        new_ids.append(doc_ids[i])
        new_metadatas.append(metadatas[i])
        print(f" Embeddings: {doc_id}")

if new_docs:
    collection.add(
        documents= new_docs,
        embeddings = new_embeddings,
        ids= new_ids,
        metadatas=new_metadatas
    )
    print(f"\n{len(new_docs)} documents added to chromaDB")
else:
    print("\nAll documents already exist in ChromDB, Nothing added.")

print(f"Total documents in collection: {collection.count()}\n")

# -------------------------------------------------------------
# STEP 6: VERIFICATION — test that retrieval actually works
# -------------------------------------------------------------
# We run 3 test queries. For each one we embed the question
# and ask ChromaDB to return the most similar document.
# The correct document should come back every time.
# If it doesn't, something is wrong with the embeddings.
# -------------------------------------------------------------
 
print("=" * 60)
print("VERTIFICATOION = Running test quries")
print("=" * 60)

test_queries = [
    "How long can this company survive before running out of cash?",
    "Is out biggest client too large a portion of our revenue?",
    "What is our days sales outstanding and accounts receivable collection time?"
]

expected = [
    "concept_05_burn_rate_runway",
    "concept_04_client_concentration",
    "concept_03_days_sales_outstanding"
]
 
all_passed = True 

for i, query in enumerate(test_queries):
    #Embed the question using the same model
    query_vector = embedding_model.encode([query]).tolist()

    #Ask ChromaDB: Which stored documents is most similar?
    results = collection.query(
        query_embeddings = query_vector,
        n_results = 1 # return only the top match
    )
    top_match = results["ids"][0][0]
    top_score = round(1 - results["distances"][0][0], 4)

# distance is 0 = identical, 1 = completely different
# we subtract from 1 to get a similarity score instead

    status = "PASS" if top_match == expected[i] else "FAIL"
    if status == "FAIL":
        all_passed = False
    print(f'\nQuery:  {query}')
    print(f"Expected: {expected[i]}")
    print(f"Got:  {top_match}")
    print(f"Score: {top_score} [{status}]")
print("\n" + "=" * 60)
if all_passed:
    print("ALL TESTS PASSED - ChromaDB is ready for phase 3")
else:
    print("SOME TESTS FAILED - Check document content and re-run.")
print("=" * 60)

