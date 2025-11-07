-- 02_tables.sql
-- Helpers
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

-- Courts
CREATE TABLE IF NOT EXISTS courts (
  court_uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sudrf_ext_id TEXT,
  name TEXT NOT NULL,
  name_short TEXT,
  branch TEXT,
  instance_level INT,
  region_code TEXT,
  address TEXT,
  timezone TEXT,
  website_url TEXT,
  source_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cases
CREATE TABLE IF NOT EXISTS cases (
  case_uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  court_uid UUID NOT NULL REFERENCES courts(court_uid) ON DELETE CASCADE,
  case_number TEXT NOT NULL,
  sudrf_case_url TEXT,
  jurisdiction TEXT,
  category TEXT,
  subject TEXT,
  claim_amount_rub NUMERIC,
  filing_date DATE,
  status TEXT,
  secrecy TEXT,
  instance_path TEXT[],
  judges TEXT[],
  source_court_name TEXT,
  ingestion_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (court_uid, case_number)
);

-- Parties
CREATE TABLE IF NOT EXISTS parties (
  party_uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_uid UUID NOT NULL REFERENCES cases(case_uid) ON DELETE CASCADE,
  role TEXT NOT NULL,
  display_name TEXT NOT NULL,
  inn TEXT,
  ogrn TEXT,
  birthdate DATE,
  address TEXT,
  lawyers TEXT[]
);

-- Hearings
CREATE TABLE IF NOT EXISTS hearings (
  hearing_uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_uid UUID NOT NULL REFERENCES cases(case_uid) ON DELETE CASCADE,
  kind TEXT,
  scheduled_start TIMESTAMPTZ NOT NULL,
  scheduled_end TIMESTAMPTZ,
  room TEXT,
  result TEXT,
  judge TEXT,
  minutes_url TEXT,
  video_url TEXT
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
  doc_uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  case_uid UUID NOT NULL REFERENCES cases(case_uid) ON DELETE CASCADE,
  doc_type TEXT NOT NULL,
  decision_date DATE NOT NULL,
  published_at TIMESTAMPTZ,
  judge TEXT,
  panel TEXT[],
  url TEXT,
  filename TEXT,
  mime_type TEXT,
  language TEXT DEFAULT 'ru',
  text_length INT,
  text_sha256 CHAR(64) NOT NULL,
  text_gz_base64 TEXT,
  extraction_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (url),
  UNIQUE (text_sha256)
);

-- Document applied laws
CREATE TABLE IF NOT EXISTS document_applied_articles (
  doc_uid UUID NOT NULL REFERENCES documents(doc_uid) ON DELETE CASCADE,
  code TEXT NOT NULL,
  article TEXT NOT NULL,
  normalized_key TEXT,
  PRIMARY KEY (doc_uid, code, article)
);

-- Extracted LLM fields
CREATE TABLE IF NOT EXISTS extracted_decision_fields (
  extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  doc_uid UUID NOT NULL REFERENCES documents(doc_uid) ON DELETE CASCADE,
  model_name TEXT,
  model_version TEXT,
  prompt_hash TEXT,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  plaintiff_claims TEXT,
  plaintiff_arguments TEXT,
  defendant_arguments TEXT,
  evaluation_of_evidence TEXT,
  intermediate_conclusions TEXT,
  applicable_laws TEXT,
  judgment_summary TEXT,
  confidence DOUBLE PRECISION,
  evidence_spans JSONB
);

-- Case relations
CREATE TABLE IF NOT EXISTS case_relations (
  relation_uid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  from_case_uid UUID NOT NULL REFERENCES cases(case_uid) ON DELETE CASCADE,
  to_case_uid UUID NOT NULL REFERENCES cases(case_uid) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  note TEXT
);

-- Ingestion runs
CREATE TABLE IF NOT EXISTS ingestion_runs (
  ingestion_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_system TEXT,
  source_url TEXT,
  crawler_version TEXT,
  parser_version TEXT,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  http_status INT,
  robots_status TEXT,
  raw_sha256 CHAR(64)
);

-- Vector tables (pgvector)
-- Use EMBED_DIM env; here set to 1536 by default.
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='vector_document_chunks') THEN
    CREATE TABLE vector_document_chunks (
      id TEXT PRIMARY KEY,
      namespace TEXT,
      case_uid UUID REFERENCES cases(case_uid) ON DELETE CASCADE,
      doc_uid UUID REFERENCES documents(doc_uid) ON DELETE CASCADE,
      doc_type TEXT,
      decision_date DATE,
      chunk_no INT NOT NULL,
      char_start INT,
      char_end INT,
      token_count INT,
      section_hint TEXT,
      field_tag TEXT,
      chunk_text TEXT NOT NULL,
      embedding vector(1536),
      text_sha256 CHAR(64),
      source_url TEXT,
      model_name TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='vector_extracted_facts') THEN
    CREATE TABLE vector_extracted_facts (
      id TEXT PRIMARY KEY,
      case_uid UUID REFERENCES cases(case_uid) ON DELETE CASCADE,
      doc_uid UUID REFERENCES documents(doc_uid) ON DELETE CASCADE,
      field_name TEXT NOT NULL,
      value_text TEXT NOT NULL,
      confidence DOUBLE PRECISION,
      evidence_span JSONB,
      embedding vector(1536),
      source_url TEXT,
      model_name TEXT,
      model_version TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  END IF;
END $$;

-- Triggers
DROP TRIGGER IF EXISTS trg_cases_updated ON cases;
CREATE TRIGGER trg_cases_updated BEFORE UPDATE ON cases
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_documents_updated ON documents;
CREATE TRIGGER trg_documents_updated BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_courts_updated ON courts;
CREATE TRIGGER trg_courts_updated BEFORE UPDATE ON courts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
