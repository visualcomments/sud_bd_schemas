# Руководство по схемам и источникам данных (sudrf.ru и сайты судов)

Данный раздел связывает **каждую схему** из `schemas/json/` и таблицу из `sql/ddl/` с **реальными типами страниц** на sudrf.ru и порталах судов. Для каждой сущности перечислены **поля**, **где брать данные**, **как парсить**, и **какие ссылки-источники** соответствуют типовой странице.

> ⚠️ Интерфейсы судов отличаются (единый шаблон `*.sudrf.ru/modules.php?name=sud_delo` vs порталы субъектов — например, `mos-gorsud.ru`). Мы поддерживаем **оба** семейства страниц.

---

## Обозначения источников

- **[SUDRF КАТАЛОГ]**: Поисковая/навигационная форма на sudrf.ru, ведущая на сайты судов. Пример: https://sudrf.ru/index.php?id=300
- **[SUDRF СУДЕБНОЕ ДЕЛОПРОИЗВОДСТВО]**: Страницы вида `https://<subdomain>.sudrf.ru/modules.php?name=sud_delo` (списки заседаний, поиск по делам, карточка дела, текст документа).
  - Примеры:
    - Петроградский районный суд СПб: https://pgr--spb.sudrf.ru/modules.php?name=sud_delo
    - Кейс (карточка): `name_op=case` (пример с параметрами): https://centr-simph--krm.sudrf.ru/modules.php?case_id=209327907&case_uid=d029791a-5c30-461d-b2b8-45415c6eb5ad&delo_id=1540006&name=sud_delo&name_op=case&srv_num=1
    - Документ (текст): `name_op=doc` (пример): https://leninsky--tula.sudrf.ru/modules.php?delo_id=1540006&name=sud_delo&name_op=doc&new=0&number=195375479&srv_num=1&text_number=1
- **[MOS-GORSUD Портал]**: Региональный портал Москвы (единый для районных/городского суда).
  - Главная: https://mos-gorsud.ru/
  - Сервисы/дела (списки): https://mos-gorsud.ru/mgs/services/cases
  - Примеры списков:
    - Гражданские, 1 инстанция: https://mos-gorsud.ru/mgs/services/cases/first-civil
    - Уголовные, 1 инстанция: https://mos-gorsud.ru/mgs/services/cases/first-criminal
    - Апелляция, гражданские: https://mos-gorsud.ru/mgs/services/cases/board-civil
  - **Карточка дела**: пример: https://mos-gorsud.ru/rs/dorogomilovskij/services/cases/civil/details/7872a841-4848-11ef-b803-89c2d2ec456e
  - **Текст судебного акта**: пример: https://mos-gorsud.ru/mgs/cases/docs/content/1043b060-f366-11ef-8bdd-e3923d813ecf

---

## Сопоставление схем → типов страниц

### 1) `courts.schema.json` ↔ карточки судов (каталог sudrf + шапки сайтов судов)
**Откуда брать:**
- [SUDRF КАТАЛОГ] — наименование суда, тип/инстанция, регион, ссылка на сайт суда.
- Шапка сайта `*.sudrf.ru` или портал (например, `mos-gorsud.ru/<court>/`) — адрес, часовой пояс (если указан), контактные данные, URL.

**Поля → источники:**
- `name`, `name_short`: заголовки/логотип на сайте суда.
- `branch`, `instance_level`: текстовые признаки в описании суда (верховный/кассация/областной/районный/мировой).
- `region_code`: по региону суда из каталога; нормализуйте до своего справочника.
- `website_url`, `source_url`: целевая ссылка на сайт суда и ссылка-источник, откуда её получили.

**SQL-таблица:** `courts`.

---

### 2) `cases.schema.json` ↔ карточки дел
**Откуда брать:**
- [SUDRF СУДЕБНОЕ ДЕЛОПРОИЗВОДСТВО] `name_op=case` (пример карточки):
  https://centr-simph--krm.sudrf.ru/modules.php?case_id=209327907&case_uid=...&name_op=case …
  В карточке обычно есть **номер дела**, **категория**, **стадия/статус**, **состав суда**, **ссылки на заседания и документы**.
- [MOS-GORSUD Портал] карточки `/services/cases/.../details/{uuid}` (пример: Дорогомиловский суд — см. ссылку выше).

**Поля → источники:**
- `case_number`: явный «Номер дела» на странице.
- `jurisdiction`: тип (гражданское/административное/уголовное/арбитраж) — из заголовков/фильтров.
- `category`/`subject`: блок «Категория дела», «Суть требования»/«Предмет» (если присутствуют).
- `filing_date`: дата регистрации/поступления из «История состояний»/«Регистрация заявления».
- `status`: «Текущее состояние»/«Стадия» (MOS-GORSUD показывает: «Вступило в силу» и т.д.).
- `judges`: «Судья», «Состав суда» (если есть).
- `sudrf_case_url`: URL карточки дела (как в параметрах `name_op=case` или `details/{uuid}`).

**SQL-таблица:** `cases` (UNIQUE по (`court_uid`, `case_number`)).

---

### 3) `hearings.schema.json` ↔ списки заседаний/движение дела
**Откуда брать:**
- [SUDRF] список дел на дату и внутри карточки дела — раздел «Судебные заседания».
- [MOS-GORSUD] в карточке дела раздел «Судебные заседания», а также агрегированные списки `/services/cases/*` с колонками «Дата и время», «Стадия», «Судья», «Зал».

**Поля → источники:**
- `scheduled_start`/`scheduled_end`: дата/время заседания (в колонках списка или внутри карточки).
- `kind`: тип события — «заседание», «перерыв», «объявление резолютивной части» (если указано).
- `result`: краткий итог (например, «отложено», «перенос» — встречается в карточках и протоколах).
- `room`, `judge`: «Зал судебного заседания», «Судья».

**SQL-таблица:** `hearings` (индекс по `(case_uid, scheduled_start)`).

---

### 4) `documents.schema.json` ↔ тексты судебных актов
**Откуда брать:**
- [SUDRF] документ: `name_op=doc` с параметрами `text_number` и `number` (пример:
  https://leninsky--tula.sudrf.ru/modules.php?name=sud_delo&name_op=doc&...&text_number=1).
- [MOS-GORSUD] контент документа: `/cases/docs/content/{uuid}` (пример см. выше).

**Поля → источники:**
- `doc_type`: «РЕШЕНИЕ», «ОПРЕДЕЛЕНИЕ», «ПРИГОВОР» — заголовок текста.
- `decision_date`: дата из шапки документа/карточки.
- `judge` и `panel`: из шапки/подписной части («судья», «в составе»).
- `url`, `filename`, `mime_type`: URL отображения/скачивания (если есть pdf/rtf/html).
- `text_gz_base64`, `text_sha256`, `text_length`: сгенерируйте на вашей стороне после нормализации текста.
- `applied_articles`: парсите упоминания «ст.», «ч.», «п.» кодексов (ГК, ГПК, УК, КоАП и т.п.) для заполнения `document_applied_articles`.

**SQL-таблицы:** `documents`, `document_applied_articles`.

---

### 5) `extracted_decision_fields.schema.json` ↔ результаты LLM-извлечения
**Откуда брать:**
- На вход — **нормализованный текст** судебного акта (`documents.text_gz_base64`).
- LLM возвращает: `plaintiff_claims`, `plaintiff_arguments`, `defendant_arguments`, `evaluation_of_evidence`, `intermediate_conclusions`, `applicable_laws`, `judgment_summary` + `evidence_spans` (опционально).

**Как сохранять:**
- Каждая выгрузка — новая запись (`extraction_id`), со ссылкой на `doc_uid`, полями `model_name`, `model_version`, `prompt_hash`, `confidence`.
- Рекомендуется хранить `evidence_spans` с **позициями** (char offsets) исходного нормализованного текста.

**SQL-таблица:** `extracted_decision_fields`.

---

### 6) `case_relations.schema.json` ↔ связи между делами/инстанциями
**Откуда брать:**
- В карточках дел верхних инстанций часто есть ссылка на номер дела нижестоящей инстанции («номер дела суда первой инстанции»).
  Пример (апелляция на MOS-GORSUD): https://mos-gorsud.ru/mgs/services/cases/board-civil — колонки «Номер дела», «Номер дела в суде нижестоящей инстанции».

**Поля → источники:**
- `kind`: «апелляция», «кассация», «надзор».
- `from_case_uid`/`to_case_uid`: заполнить внутренними UUID после сопоставления by `case_number` и `court_uid`.

**SQL-таблица:** `case_relations`.

---

### 7) `ingestion.schema.json` ↔ метаданные импорта
**Откуда брать:**
- Ваш краулер/парсер сохраняет тех.информацию: `source_system` (`sudrf.ru`, `court_site`, `ej.sudrf.ru`), `source_url`, версии, `http_status`, `raw_sha256` (хэш сырого HTML/PDF).

**SQL-таблица:** `ingestion_runs`.

---

### 8) Векторные схемы (`vector_document_chunk`, `vector_extracted_fact`)
**Откуда брать:**
- На вход — сырой текст документа и (опционально) уже извлечённые поля.
- Производим чанкование (800–1200 симв., overlap 150–250), считаем эмбеддинги, сохраняем:
  - `vector_document_chunks`: универсальное RAG-поиск по фрагментам.
  - `vector_extracted_facts`: точечные факты по названиям полей (`field_name`).

**Метаданные поиска:**
- `case_uid`, `doc_uid`, `doc_type`, `decision_date`, `field_tag/field_name`, `source_url` — в `metadata` у внешних движков (Pinecone/Qdrant/Weaviate) и в колонках pgvector-таблиц.

---

## Полевая карта (Field Map) — где искать на странице

| Схема / Поле | SUDRF (`modules.php?name=sud_delo`) | MOS-GORSUD |
|---|---|---|
| cases.case_number | Видно в заголовке карточки `name_op=case` (пара «Номер дела») | В карточке `/details/{uuid}` — блок **Номер дела** |
| cases.jurisdiction | Текстовая категория/фильтр (гражд./админ./угол.) | По URL раздела (`first-civil`, `first-criminal`, `first-admin`) и заголовкам |
| cases.category / subject | В карточке: «Категория», «Суть требования» (если присутствует) | «Категория дела», «Суть требования» |
| cases.filing_date | «Регистрация заявления» / «История состояний» | «История состояний»: дата регистрации |
| cases.status | «Стадия/Текущее состояние» | «Текущее состояние» |
| cases.judges | «Судья», «Состав суда» | «Судебные заседания» и шапка карточки |
| hearings.scheduled_start | В списках дел/внутри карточки — дата/время слушания | В таблицах списков и карточке |
| documents.doc_type | Заголовок акта: «РЕШЕНИЕ/ОПРЕДЕЛЕНИЕ/…» | Заголовок контента документа |
| documents.decision_date | В шапке документа/карточки | В шапке документа |
| documents.judge/panel | В шапке/подписи акта | В шапке/подписи акта |
| documents.url | Текущий URL `name_op=doc` | `/cases/docs/content/{uuid}` |
| documents.text | В HTML страницы; может быть PDF/RTF | В HTML; иногда доступен для скачивания |
| extracted_* | Результаты LLM по нормализованному тексту | То же |

---

## Нормализация текста и извлечение статей законов

1. **Нормализация:** снимаем неразрывные пробелы, заменяем «умные» кавычки, убираем маркеры навигации сайта.
2. **Сегментация:** эвристики по маркерам «УСТАНОВИЛ», «СЧИТАЕТ», «РЕШИЛ», «ОПРЕДЕЛИЛ».
3. **Статьи законов:** регэкспы по шаблонам: `ст\.?\s*\d+[\.\d]*\s*(ГК|ГПК|УК|КоАП|ТК)\s*РФ` (поддержите вариации).
4. **Хэширование:** `text_sha256`, хранение `text_gz_base64` (gzip+base64).

---

## Сопоставление инстанций и связей дел

- Для апелляции/кассации **ищем в карточках вышестоящих судов** колонку «Номер дела в суде нижестоящей инстанции» (пример: список апелляции MOS-GORSUD — ссылка выше). Далее сшиваем с `cases` по `case_number`+`court_uid` и сохраняем связь в `case_relations` (`kind='апелляция'`/`кассация'`).

---

## Надёжность: дубли и устойчивые ключи

- На разных порталах **URL нестабилен**, используйте:
  - `text_sha256` для актов (уникальность содержания),
  - `UNIQUE (court_uid, case_number)` для дел,
  - Внутренние `UUID` как первичные ключи, внешние ID держите в отдельных полях (как есть в источнике).

---

## Ссылки-образцы (для отладки парсера)

- Каталог sudrf: https://sudrf.ru/index.php?id=300
- Петроградский районный суд СПб (список/поиск дел): https://pgr--spb.sudrf.ru/modules.php?name=sud_delo
- Карточка дела на суд.сайте (пример с параметрами): https://centr-simph--krm.sudrf.ru/modules.php?case_id=209327907&case_uid=d029791a-5c30-461d-b2b8-45415c6eb5ad&delo_id=1540006&name=sud_delo&name_op=case&srv_num=1
- Документ «текст» на суд.сайте: https://leninsky--tula.sudrf.ru/modules.php?delo_id=1540006&name=sud_delo&name_op=doc&new=0&number=195375479&srv_num=1&text_number=1
- MOS-GORSUD (списки/карточки/документы):
  - https://mos-gorsud.ru/mgs/services/cases/first-civil
  - https://mos-gorsud.ru/rs/dorogomilovskij/services/cases/civil/details/7872a841-4848-11ef-b803-89c2d2ec456e
  - https://mos-gorsud.ru/mgs/cases/docs/content/1043b060-f366-11ef-8bdd-e3923d813ecf

> Эти ссылки приведены **как примеры шаблонов страниц** для сопоставления полей и тестирования парсеров.
