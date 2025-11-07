# sudrf-ingest — репозиторий схем, DDL (PostgreSQL + pgvector), миграций, валидаторов и ETL/ELT

Этот репозиторий даёт готовую структуру хранения данных судебных дел (sudrf.ru и сайты судов), включает:
- **JSON Schema** (нормализованная реляционная модель + векторная модель для RAG).
- **DDL PostgreSQL** (расширения, таблицы, индексы, триггеры) и **миграции** (SQL-файлы).
- **Валидаторы JSON** на базе `jsonschema`.
- **ETL/ELT-пайплайны** для загрузки дел и актов, извлечения полей LLM, разбиения на чанки и заливки в векторные движки.
- Поддержка популярных векторных движков: **pgvector (PostgreSQL)**, **Pinecone**, **Weaviate**, **Qdrant** (плагины-коннекторы).
- Готовый **Docker Compose** для PostgreSQL + pgvector.

## Быстрый старт

### 1) Подготовка окружения
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # заполните переменные подключения
```

### 2) Запуск PostgreSQL с pgvector (локально через Docker)
```bash
docker compose -f docker/docker-compose.yml up -d
# ждём, затем применяем миграции
./scripts/init_db.sh
./scripts/migrate.sh
```

### 3) Валидация JSON по схемам
```bash
python validation/validate_json.py --dir schemas/json --example examples/sample_extraction.json
```

### 4) ETL/ELT пример
```bash
# Загрузка примера в реляционную модель + векторизацию и запись в pgvector
./scripts/etl_example.sh
```
Скрипт:
- создаёт запись суда/дела/документа,
- вычисляет SHA-256 текста, сжимает и сохраняет,
- вносит извлечённые поля LLM,
- режет текст на чанки, строит эмбеддинги,
- записывает в `vector_document_chunks` и `vector_extracted_facts` (pgvector).

### 5) Альтернативные векторные движки
Дополнительно можно синхронизировать чанки/факты в **Pinecone**, **Weaviate** или **Qdrant**:
```bash
python etl/vector_sync.py --engine pinecone --upsert facts --from-db
python etl/vector_sync.py --engine weaviate --upsert chunks --from-db
python etl/vector_sync.py --engine qdrant --upsert all --from-db
```
> Параметры подключения берутся из `.env`.

## Структура проекта
```
schemas/json/           # JSON Schema (реляционные сущности и векторные схемы)
sql/ddl/                # DDL: расширения, таблицы, индексы, триггеры
sql/migrations/         # Нумерованные SQL миграции
validation/             # Валидация JSON по схемам
etl/                    # ETL/ELT пайплайны и коннекторы к векторным БД
examples/               # Примеры
scripts/                # Утилиты запуска
docker/                 # Dockerfile и docker-compose для PostgreSQL + pgvector
```

## Требования
- Python 3.10+
- PostgreSQL 14+ (рекомендуется 15/16) с расширением **pgvector 0.5+**
- Для внешних движков: актуальные ключи/эндпоинты (Pinecone/Weaviate/Qdrant)

## Переменные окружения (.env)
Смотрите `.env.example`. Минимум:
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sudrf
EMBED_DIM=1536
EMBEDDER=random  # openai | sentence-transformers | random
```

### Эмбеддеры
- `openai`: использует OpenAI Embeddings (`OPENAI_API_KEY`, `OPENAI_EMBED_MODEL`).
- `sentence-transformers`: локальные модели (укажите `ST_MODEL_NAME`).
- `random`: детерминированная генерация (для отладки без сети).

## Миграции
SQL-файлы в `sql/migrations/` применяются по порядку. Повторный прогон безопасен благодаря `IF NOT EXISTS` и проверкам.

## Лицензия
GNU GPL v.3
