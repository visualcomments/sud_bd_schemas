import os, json, psycopg2, numpy as np
from dotenv import load_dotenv
load_dotenv()

DB = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/sudrf')

def fetch_from_db(kind='chunks', limit=1000):
    conn = psycopg2.connect(DB)
    with conn.cursor() as cur:
        if kind == 'chunks':
            cur.execute("SELECT id, embedding, case_uid::text, doc_uid::text, chunk_text FROM vector_document_chunks LIMIT %s", (limit,))
        else:
            cur.execute("SELECT id, embedding, case_uid::text, doc_uid::text, value_text FROM vector_extracted_facts LIMIT %s", (limit,))
        rows = cur.fetchall()
    conn.close()
    return rows

def upsert_pinecone(items, namespace='default'):
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    index = pc.Index(os.getenv('PINECONE_INDEX','sudrf-index'))
    vectors = []
    for _id, emb, case_uid, doc_uid, text in items:
        vectors.append({'id': _id, 'values': emb, 'metadata': {'case_uid':case_uid, 'doc_uid':doc_uid, 'text':text}})
    index.upsert(vectors=vectors, namespace=namespace)
    print(f"Pinecone upserted: {len(vectors)} vectors")


def upsert_weaviate(items, class_name='SudrfVector'):
    import weaviate
    client = weaviate.connect_to_weaviate(
        http_host=os.getenv('WEAVIATE_URL','http://localhost:8080').replace('http://','').replace('https://',''),
        grpc_host=None,
        http_secure=os.getenv('WEAVIATE_URL','').startswith('https'),
        auth_credentials=weaviate.auth.AuthApiKey(os.getenv('WEAVIATE_API_KEY')) if os.getenv('WEAVIATE_API_KEY') else None
    )
    try:
        schema = client.collections
        if class_name not in [c for c in schema.list_all()]:  # simplified
            pass
        with client.batch.dynamic() as batch:
            for _id, emb, case_uid, doc_uid, text in items:
                batch.add_object(properties={'case_uid':case_uid,'doc_uid':doc_uid,'text':text}, vector=emb, uuid=_id, collection=class_name)
        print(f"Weaviate upserted: {len(items)} vectors")
    finally:
        client.close()

def upsert_qdrant(items, collection=None):
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import VectorParams, Distance, PointStruct
    coll = collection or os.getenv('QDRANT_COLLECTION','sudrf_collection')
    client = QdrantClient(url=os.getenv('QDRANT_URL','http://localhost:6333'), api_key=os.getenv('QDRANT_API_KEY'))
    dim = int(os.getenv('EMBED_DIM','1536'))
    existing = client.get_collections()
    if coll not in [c.name for c in existing.collections]:
        client.recreate_collection(coll, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
    points = []
    for _id, emb, case_uid, doc_uid, text in items:
        points.append(PointStruct(id=_id, vector=emb, payload={'case_uid':case_uid,'doc_uid':doc_uid,'text':text}))
    client.upsert(collection_name=coll, points=points)
    print(f"Qdrant upserted: {len(points)} vectors")


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', choices=['pinecone','weaviate','qdrant'], required=True)
    ap.add_argument('--upsert', choices=['chunks','facts','all'], default='chunks')
    ap.add_argument('--from-db', action='store_true', default=True)
    args = ap.parse_args()

    if args.upsert in ('chunks','all'):
        items = fetch_from_db('chunks', limit=1000)
        if args.engine=='pinecone': upsert_pinecone(items)
        elif args.engine=='weaviate': upsert_weaviate(items)
        elif args.engine=='qdrant': upsert_qdrant(items)

    if args.upsert in ('facts','all'):
        items = fetch_from_db('facts', limit=1000)
        if args.engine=='pinecone': upsert_pinecone(items)
        elif args.engine=='weaviate': upsert_weaviate(items)
        elif args.engine=='qdrant': upsert_qdrant(items)
