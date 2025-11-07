-- 03_indexes.sql
-- B-tree indexes
CREATE INDEX IF NOT EXISTS idx_cases_court ON cases(court_uid);
CREATE INDEX IF NOT EXISTS idx_cases_number ON cases(case_number);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_jurisdiction ON cases(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_cases_filing_date ON cases(filing_date);

CREATE INDEX IF NOT EXISTS idx_parties_case ON parties(case_uid);
CREATE INDEX IF NOT EXISTS idx_parties_role ON parties(role);
CREATE INDEX IF NOT EXISTS idx_parties_inn ON parties(inn);
CREATE INDEX IF NOT EXISTS idx_parties_ogrn ON parties(ogrn);

CREATE INDEX IF NOT EXISTS idx_docs_case ON documents(case_uid);
CREATE INDEX IF NOT EXISTS idx_docs_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_docs_decision_date ON documents(decision_date);
CREATE INDEX IF NOT EXISTS idx_docs_sha ON documents(text_sha256);

CREATE INDEX IF NOT EXISTS idx_hearings_case ON hearings(case_uid);
CREATE INDEX IF NOT EXISTS idx_hearings_start ON hearings(scheduled_start);

CREATE INDEX IF NOT EXISTS idx_doc_articles_doc ON document_applied_articles(doc_uid);
CREATE INDEX IF NOT EXISTS idx_extracted_doc ON extracted_decision_fields(doc_uid);
CREATE INDEX IF NOT EXISTS idx_extracted_time ON extracted_decision_fields(timestamp);

-- Vector indexes (ivfflat); requires ANALYZE and setting ivfflat lists appropriately.
-- Cosine distance (common for embeddings)
CREATE INDEX IF NOT EXISTS idx_vec_chunks_ivfflat ON vector_document_chunks
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_vec_facts_ivfflat ON vector_extracted_facts
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
