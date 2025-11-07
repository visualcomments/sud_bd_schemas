import os, gzip, base64, hashlib, json, math
from datetime import datetime
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from embeddings.providers import embed_texts

load_dotenv()

DB = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/sudrf')

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def gzip_b64(text: str) -> str:
    return base64.b64encode(gzip.compress(text.encode('utf-8'))).decode('ascii')

def chunk_text(text: str, size: int = 1200, overlap: int = 200):
    chunks = []
    start = 0
    n = len(text)
    no = 0
    while start < n:
        end = min(n, start + size)
        chunk = text[start:end]
        chunks.append((no, start, end, chunk))
        no += 1
        start = end - overlap
        if start < 0:
            start = 0
        if start >= n:
            break
    return chunks

def ensure_court(conn, name, branch='общая юрисдикция', region_code='77', website_url=None, source_url=None):
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO courts (name, branch, region_code, website_url, source_url)
                       VALUES (%s,%s,%s,%s,%s)
                       ON CONFLICT DO NOTHING
                       RETURNING court_uid""", (name, branch, region_code, website_url, source_url))
        row = cur.fetchone()
        if row: return row[0]
        cur.execute("SELECT court_uid FROM courts WHERE name=%s AND region_code=%s LIMIT 1", (name, region_code))
        return cur.fetchone()[0]

def create_case(conn, court_uid, case_number, jurisdiction, filing_date, status='в производстве', sudrf_case_url=None):
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO cases (court_uid, case_number, jurisdiction, filing_date, status, sudrf_case_url)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (court_uid, case_number) DO UPDATE SET jurisdiction=EXCLUDED.jurisdiction
                       RETURNING case_uid""", (court_uid, case_number, jurisdiction, filing_date, status, sudrf_case_url))
        return cur.fetchone()[0]

def create_document(conn, case_uid, doc_type, decision_date, text, url=None, filename=None, mime_type='text/plain', judge=None):
    sha = sha256_hex(text)
    gz = gzip_b64(text)
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO documents
            (case_uid, doc_type, decision_date, url, filename, mime_type, language, text_length, text_sha256, text_gz_base64, judge)
            VALUES (%s,%s,%s,%s,%s,%s,'ru',%s,%s,%s,%s)
            ON CONFLICT (text_sha256) DO UPDATE SET decision_date=EXCLUDED.decision_date
            RETURNING doc_uid""", (case_uid, doc_type, decision_date, url, filename, mime_type, len(text), sha, gz, judge))
        return cur.fetchone()[0], sha

def insert_extraction(conn, doc_uid, fields: dict, model_name='llm', model_version='v1', prompt_hash=None, confidence=None):
    payload = {
        'doc_uid': str(doc_uid),
        'model_name': model_name,
        'model_version': model_version,
        'prompt_hash': prompt_hash or '',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        **fields
    }
    cols = ['doc_uid','model_name','model_version','prompt_hash','plaintiff_claims','plaintiff_arguments','defendant_arguments','evaluation_of_evidence','intermediate_conclusions','applicable_laws','judgment_summary','confidence','evidence_spans']
    values = [payload.get('doc_uid'), payload.get('model_name'), payload.get('model_version'), payload.get('prompt_hash'),
              payload.get('plaintiff_claims'), payload.get('plaintiff_arguments'), payload.get('defendant_arguments'),
              payload.get('evaluation_of_evidence'), payload.get('intermediate_conclusions'), payload.get('applicable_laws'),
              payload.get('judgment_summary'), payload.get('confidence'), json.dumps(payload.get('evidence_spans') or [])]
    with conn.cursor() as cur:
        cur.execute(f"""INSERT INTO extracted_decision_fields ({','.join(cols)})
                        VALUES ({','.join(['%s']*len(cols))})
                        RETURNING extraction_id""", values)
        return cur.fetchone()[0]

def upsert_chunks_and_facts(conn, case_uid, doc_uid, text, sha, extraction: dict, embed_dim: int = None):
    chunks = chunk_text(text)
    chunk_texts = [c[3] for c in chunks]
    embs = embed_texts(chunk_texts)
    rows = []
    for (no, start, end, ch), e in zip(chunks, embs):
        rows.append((f"{doc_uid}:{no}", None, case_uid, doc_uid, extraction.get('doc_type','решение'),
                     extraction.get('decision_date'), no, start, end, None, None, extraction.get('field_tag','other'),
                     ch, e, sha, extraction.get('source_url'), extraction.get('model_name','embedder'), datetime.utcnow()))
    with conn.cursor() as cur:
        execute_values(cur,
            """INSERT INTO vector_document_chunks
            (id, namespace, case_uid, doc_uid, doc_type, decision_date, chunk_no, char_start, char_end, token_count,
             section_hint, field_tag, chunk_text, embedding, text_sha256, source_url, model_name, created_at)
             VALUES %s ON CONFLICT (id) DO NOTHING""", rows, template=None, page_size=500)

    # facts vectorization (if extraction payload fields are present)
    fact_fields = ['plaintiff_claims','plaintiff_arguments','defendant_arguments','evaluation_of_evidence','intermediate_conclusions','applicable_laws','judgment_summary']
    facts = [(k, extraction.get(k)) for k in fact_fields if extraction.get(k)]
    if facts:
        fact_texts = [v for _, v in facts]
        fact_embs = embed_texts(fact_texts)
        fact_rows = []
        for (name, text_val), e in zip(facts, fact_embs):
            fid = f"{doc_uid}:{name}"
            fact_rows.append((fid, case_uid, doc_uid, name, text_val, extraction.get('confidence'), json.dumps(extraction.get('evidence_span')), e, extraction.get('source_url'), extraction.get('model_name'), extraction.get('model_version'), datetime.utcnow()))
        with conn.cursor() as cur:
            execute_values(cur,
                """INSERT INTO vector_extracted_facts
                (id, case_uid, doc_uid, field_name, value_text, confidence, evidence_span, embedding, source_url, model_name, model_version, created_at)
                VALUES %s ON CONFLICT (id) DO UPDATE SET value_text=EXCLUDED.value_text""", fact_rows, page_size=200)

def main():
    import argparse, pathlib
    ap = argparse.ArgumentParser()
    ap.add_argument('--case-number', default='2-123/2024')
    ap.add_argument('--jurisdiction', default='гражданское')
    ap.add_argument('--filing-date', default='2024-01-15')
    ap.add_argument('--court-name', default='Н-ский районный суд г. Москвы')
    ap.add_argument('--doc-type', default='решение')
    ap.add_argument('--decision-date', default='2024-03-10')
    ap.add_argument('--text-file', default='examples/sample_decision.txt')
    ap.add_argument('--extraction-json', default='examples/sample_extraction.json')
    args = ap.parse_args()

    conn = psycopg2.connect(DB)
    conn.autocommit = False
    try:
        court_uid = ensure_court(conn, name=args.court_name, region_code='77')
        case_uid = create_case(conn, court_uid, args.case_number, args.jurisdiction, args.filing_date)
        with open(args.text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        doc_uid, sha = create_document(conn, case_uid, args.doc_type, args.decision_date, text, filename=os.path.basename(args.text_file))
        with open(args.extraction_json, 'r', encoding='utf-8') as f:
            fields = json.load(f)
        extraction_id = insert_extraction(conn, doc_uid, fields, model_name=fields.get('model_name','llm'), model_version=fields.get('model_version','v1'), confidence=fields.get('confidence'))
        # Vectorize & upsert
        upsert_chunks_and_facts(conn, case_uid, doc_uid, text, sha, {"model_name":"embedder","decision_date":args.decision_date,"doc_type":args.doc_type})
        conn.commit()
        print("OK: court_uid=", court_uid, " case_uid=", case_uid, " doc_uid=", doc_uid, " extraction_id=", extraction_id)
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
