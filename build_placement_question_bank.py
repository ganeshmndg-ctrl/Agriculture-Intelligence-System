import json
import os
import re
import time
import hashlib
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# PLACEMENT / GD QUESTION BANK BUILDER
# Version: v1
#
# Purpose:
#   Build a cumulative, source-grounded question bank for
#   placement preparation, interviews and group discussions.
#
# INPUTS:
#
#   1. Master Intelligence Database
#   2. Government Intelligence Bank
#   3. Connections Bank
#
# OUTPUT:
#
#   data/
#       placement_question_bank_v1/
#           PLACEMENT_QUESTION_BANK_v1.json
#           PLACEMENT_QUESTION_BANK_REPORT_v1.txt
#
# IMPORTANT:
#   - Existing questions are preserved.
#   - New newspaper editions can be added later.
#   - Already processed records are skipped.
#   - Duplicate questions are skipped.
#   - Every question retains source provenance.
#   - Derived connections are clearly identified.
# ============================================================


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


MASTER_PATH = (
    BASE_DIR
    / "data"
    / "master_database_v1"
    / "MASTER_INTELLIGENCE_DATABASE_v1.json"
)


GOVERNMENT_PATH = (
    BASE_DIR
    / "data"
    / "government_intelligence_bank_v2"
    / "GOVERNMENT_INTELLIGENCE_BANK_v2.json"
)


CONNECTIONS_PATH = (
    BASE_DIR
    / "data"
    / "connections_bank_v1_1"
    / "VALIDATED_CONNECTIONS_BANK_v1.json"
)


OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "placement_question_bank_v1"
)


OUTPUT_PATH = (
    OUTPUT_DIR
    / "PLACEMENT_QUESTION_BANK_v1.json"
)


REPORT_PATH = (
    OUTPUT_DIR
    / "PLACEMENT_QUESTION_BANK_REPORT_v1.txt"
)


# ============================================================
# GEMINI SETTINGS
# ============================================================

MODEL_NAME = "gemini-3.1-flash-lite"

# Keep requests below Gemini free-tier rate limits.
REQUEST_DELAY_SECONDS = 5

# Delay before retrying temporary API errors.
RETRY_DELAY_SECONDS = 20

# Maximum number of attempts per Gemini request.
MAX_RETRIES = 3


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)


API_KEY = os.getenv(
    "GEMINI_API_KEY"
)


if not API_KEY:

    raise RuntimeError(
        "GEMINI_API_KEY was not found in .env. "
        "Keep your existing API key in the project .env file."
    )


client = genai.Client(
    api_key=API_KEY
)


# ============================================================
# ALLOWED VALUES
# ============================================================

VALID_QUESTION_TYPES = {

    "KNOWLEDGE",

    "WHY_HOW",

    "ANALYTICAL",

    "GD",

    "CASE_BASED",

    "INTERVIEW",

    "CROSS_EVENT_GD",
}


VALID_CATEGORIES = {

    "AGRICULTURE",

    "AGRIBUSINESS",

    "BANKING_FINANCE",

    "MACRO_ECONOMY",

    "INTERNATIONAL_TRADE",

    "GOVERNMENT_POLICY",

    "BUSINESS_MANAGEMENT",

    "CROSS_SECTOR",
}


VALID_DIFFICULTIES = {

    "EASY",

    "MEDIUM",

    "HARD",
}


VALID_RELEVANCE = {

    "HIGH",

    "MEDIUM",

    "LOW",
}


# ============================================================
# BASIC HELPERS
# ============================================================

def now_iso():

    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_json(path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


def clean_text(
    value,
    max_chars=None
):

    if value is None:

        return ""

    text = str(
        value
    ).strip()

    if (
        max_chars
        and len(text) > max_chars
    ):

        return (
            text[:max_chars]
            .rstrip()
            + "..."
        )

    return text


def normalize_question(text):

    text = clean_text(
        text
    ).lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"^[\-\*\d\.\)\s]+",
        "",
        text
    )

    text = re.sub(
        r"[\"'“”‘’]",
        "",
        text
    )

    return text.strip(
        " .?!:;,"
    )


def question_fingerprint(text):

    normalized = normalize_question(
        text
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:16]


def make_question_id(
    existing_ids,
    fingerprint
):

    base = (
        f"Q_{fingerprint}"
    )

    if base not in existing_ids:

        return base

    counter = 2

    while (
        f"{base}_{counter}"
        in existing_ids
    ):

        counter += 1

    return (
        f"{base}_{counter}"
    )


# ============================================================
# LOAD INPUT DATABASES
# ============================================================

def get_master_records(data):

    records = data.get(
        "records",
        []
    )

    if not isinstance(
        records,
        list
    ):

        raise ValueError(
            "Master database does not contain "
            "a valid 'records' list."
        )

    return records


def get_government_initiatives(data):

    initiatives = data.get(
        "initiatives",
        []
    )

    if not isinstance(
        initiatives,
        list
    ):

        raise ValueError(
            "Government Intelligence Bank does not contain "
            "a valid 'initiatives' list."
        )

    return initiatives


def get_connections(data):

    connections = data.get(
        "connections",
        []
    )

    if not isinstance(
        connections,
        list
    ):

        raise ValueError(
            "Connections Bank does not contain "
            "a valid 'connections' list."
        )

    return connections


# ============================================================
# BUILD GOVERNMENT INTELLIGENCE INDEX
# ============================================================

def build_government_index(
    initiatives
):

    """
    Maps source record IDs to government intelligence.

    Example:

        record_id
            ↓
        UPI initiative
            ↓
        MDR update
    """

    index = {}

    for initiative in initiatives:

        mentions = (
            initiative.get(
                "newspaper_mentions",
                []
            )
            or []
        )

        for mention in mentions:

            record_id = mention.get(
                "record_id"
            )

            if not record_id:

                continue

            item = {

                "initiative_id":
                    initiative.get(
                        "initiative_id",
                        ""
                    ),

                "initiative_name":
                    initiative.get(
                        "initiative_name",
                        ""
                    ),

                "initiative_type":
                    initiative.get(
                        "initiative_type",
                        ""
                    ),

                "latest_update":
                    initiative.get(
                        "latest_update",
                        ""
                    ),

                "event_type":
                    mention.get(
                        "event_type",
                        ""
                    ),

                "details":
                    mention.get(
                        "details",
                        ""
                    ),
            }

            index.setdefault(
                record_id,
                []
            ).append(
                item
            )

    return index


# ============================================================
# BUILD CONNECTION INDEX
# ============================================================

def build_connection_index(
    connections
):

    """
    Maps each source record to the connections
    in which that record participates.
    """

    index = {}

    for connection in connections:

        source_record_ids = (
            connection.get(
                "source_record_ids",
                []
            )
            or []
        )

        for record_id in source_record_ids:

            index.setdefault(
                record_id,
                []
            ).append(
                connection
            )

    return index


# ============================================================
# COMPACT MASTER RECORD
# ============================================================

def compact_master_record(
    record
):

    """
    Sends only useful evidence to Gemini.

    This reduces token usage while preserving
    the information required for grounded questions.
    """

    return {

        "record_id":
            record.get(
                "record_id",
                ""
            ),

        "newspaper":
            record.get(
                "newspaper",
                ""
            ),

        "date":
            record.get(
                "date",
                ""
            ),

        "page":
            record.get(
                "page",
                ""
            ),

        "headline":
            record.get(
                "headline",
                ""
            ),

        "content_type":
            record.get(
                "content_type",
                ""
            ),

        "primary_category":
            record.get(
                "primary_category",
                ""
            ),

        "secondary_categories":
            record.get(
                "secondary_categories",
                []
            ),

        "intelligence_type":
            record.get(
                "intelligence_type",
                ""
            ),

        "agriculture_connection":
            record.get(
                "agriculture_connection",
                ""
            ),

        "agriculture_relevance":
            record.get(
                "agriculture_relevance",
                ""
            ),

        "placement_relevance":
            record.get(
                "placement_relevance",
                ""
            ),

        "summary":
            record.get(
                "summary",
                ""
            ),

        "reported_facts":
            record.get(
                "reported_facts",
                []
            ),

        "key_facts":
            record.get(
                "key_facts",
                []
            ),

        "key_numbers":
            record.get(
                "key_numbers",
                []
            ),

        "agriculture_impact":
            record.get(
                "agriculture_impact",
                ""
            ),

        "why_it_matters":
            record.get(
                "why_it_matters",
                ""
            ),

        "connections":
            record.get(
                "connections",
                []
            ),

        "government_schemes":
            record.get(
                "government_schemes",
                []
            ),

        "existing_placement_questions":
            record.get(
                "placement_questions",
                []
            ),
    }


# ============================================================
# COMPACT GOVERNMENT INTELLIGENCE
# ============================================================

def compact_government_items(
    items
):

    result = []

    for item in items:

        result.append({

            "initiative_id":
                item.get(
                    "initiative_id",
                    ""
                ),

            "initiative_name":
                item.get(
                    "initiative_name",
                    ""
                ),

            "initiative_type":
                item.get(
                    "initiative_type",
                    ""
                ),

            "latest_update":
                item.get(
                    "latest_update",
                    ""
                ),

            "event_type":
                item.get(
                    "event_type",
                    ""
                ),

            "details":
                item.get(
                    "details",
                    ""
                ),
        })

    return result


# ============================================================
# COMPACT CONNECTION
# ============================================================

def compact_connection(
    connection
):

    return {

        "connection_id":
            connection.get(
                "connection_id",
                ""
            ),

        "source_record_ids":
            connection.get(
                "source_record_ids",
                []
            ),

        "source_event_ids":
            connection.get(
                "source_event_ids",
                []
            ),

        "connection_type":
            connection.get(
                "connection_type",
                ""
            ),

        "entities":
            connection.get(
                "entities",
                []
            ),

        "relationship":
            connection.get(
                "relationship",
                ""
            ),

        "chain":
            connection.get(
                "chain",
                []
            ),

        "explanation":
            connection.get(
                "explanation",
                ""
            ),

        "agriculture_relevance":
            connection.get(
                "agriculture_relevance",
                ""
            ),

        "placement_relevance":
            connection.get(
                "placement_relevance",
                ""
            ),

        "confidence":
            connection.get(
                "confidence",
                ""
            ),

        "validation_status":
            connection.get(
                "validation_status",
                ""
            ),

        "source_evidence":
            connection.get(
                "source_evidence",
                []
            ),
    }


# ============================================================
# BUILD INDIVIDUAL RECORD PROMPT
# ============================================================

def build_prompt(
    record,
    gov_items,
    related_connections
):

    source = compact_master_record(
        record
    )

    government_context = (
        compact_government_items(
            gov_items
        )
    )

    connection_context = [

        compact_connection(
            connection
        )

        for connection
        in related_connections

        if connection.get(
            "validation_status"
        )
        in {
            "VALIDATED",
            "REVIEW",
            "",
            None
        }
    ]

    prompt = f"""
You are building a high-quality, source-grounded
placement and group-discussion question bank for an
Indian MBA/PGDM Agribusiness Management student.

The student is preparing for:
- campus placements
- agribusiness interviews
- banking/finance interviews
- management interviews
- group discussions
- current-affairs discussions

Use ONLY the supplied source evidence.

============================================================
SOURCE RECORD
============================================================

{json.dumps(
    source,
    ensure_ascii=False,
    indent=2
)}

============================================================
RELATED GOVERNMENT INTELLIGENCE
============================================================

{json.dumps(
    government_context,
    ensure_ascii=False,
    indent=2
)}

============================================================
RELATED CONNECTIONS
============================================================

{json.dumps(
    connection_context,
    ensure_ascii=False,
    indent=2
)}

============================================================
TASK
============================================================

Generate exactly 3 high-quality questions from this
source record.

The questions should normally cover different purposes:

1. KNOWLEDGE or WHY_HOW
2. ANALYTICAL, CASE_BASED or INTERVIEW
3. GD or another ANALYTICAL question

If a genuine cross-event connection is supplied,
one question may be CROSS_EVENT_GD.

============================================================
QUALITY REQUIREMENTS
============================================================

The questions must be useful for a management student.

Avoid:
- trivial headline-based questions
- questions whose answer is simply one number
- repetitive wording
- generic questions that could apply to any article
- artificial agriculture connections
- invented facts
- invented numbers
- invented schemes
- invented policies
- invented causes
- invented outcomes
- unsupported claims

Prefer questions that test:
- understanding
- reasoning
- application
- business implications
- managerial decision-making
- policy implications
- risk analysis
- trade-offs
- stakeholder analysis
- agriculture-business linkages
- financial implications
- strategic thinking

============================================================
SOURCE-GROUNDING RULES
============================================================

1. Use only supplied evidence.

2. You may ask analytical questions that require
   reasonable managerial reasoning.

3. Do not put unsupported factual claims inside
   the question.

4. Do not convert an interpretation into an established fact.

5. If a connection is DERIVED, treat it as derived.

6. Do not claim that a derived relationship was
   explicitly reported by the newspaper.

7. If the article has limited agriculture relevance,
   do not force an agriculture question.

8. If the story is mainly banking/finance/business,
   generate questions appropriate to that subject.

9. If government intelligence is supplied,
   questions may test policy understanding or implications.

10. Questions should be answerable using the supplied
    facts plus reasonable managerial reasoning.

============================================================
CATEGORY
============================================================

Choose the category most relevant to the actual question.

Allowed categories:

AGRICULTURE
AGRIBUSINESS
BANKING_FINANCE
MACRO_ECONOMY
INTERNATIONAL_TRADE
GOVERNMENT_POLICY
BUSINESS_MANAGEMENT
CROSS_SECTOR

============================================================
QUESTION TYPES
============================================================

Allowed:

KNOWLEDGE
WHY_HOW
ANALYTICAL
GD
CASE_BASED
INTERVIEW
CROSS_EVENT_GD

============================================================
DIFFICULTY
============================================================

Allowed:

EASY
MEDIUM
HARD

============================================================
PLACEMENT RELEVANCE
============================================================

Allowed:

HIGH
MEDIUM
LOW

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Exact structure:

{{
  "questions": [
    {{
      "question": "...",
      "question_type": "KNOWLEDGE",
      "category": "BANKING_FINANCE",
      "difficulty": "MEDIUM",
      "placement_relevance": "HIGH",
      "key_facts_needed": [
        "..."
      ],
      "expected_answer_points": [
        "..."
      ],
      "source_basis": "..."
    }}
  ]
}}
"""

    return prompt


# ============================================================
# GEMINI API CALL
# ============================================================

def call_gemini(
    prompt
):

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = (
                client.models.generate_content(

                    model=MODEL_NAME,

                    contents=prompt,

                    config=types.GenerateContentConfig(

                        temperature=0.2,

                        response_mime_type=
                            "application/json",
                    ),
                )
            )

            text = (
                response.text
                or ""
            ).strip()

            if not text:

                raise ValueError(
                    "Gemini returned an empty response."
                )

            return json.loads(
                text
            )

        except Exception as exc:

            last_error = exc

            if attempt < MAX_RETRIES:

                print(
                    f"    Gemini attempt "
                    f"{attempt} failed: {exc}"
                )

                print(
                    f"    Retrying in "
                    f"{RETRY_DELAY_SECONDS} seconds..."
                )

                time.sleep(
                    RETRY_DELAY_SECONDS
                )

    raise RuntimeError(
        "Gemini failed after "
        f"{MAX_RETRIES} attempts: "
        f"{last_error}"
    )


# ============================================================
# SANITIZE QUESTIONS
# ============================================================

def infer_category(
    record
):

    category = clean_text(
        record.get(
            "primary_category"
        )
    ).upper()

    mapping = {

        "CORE_AGRICULTURE":
            "AGRICULTURE",

        "BANKING_FINANCE":
            "BANKING_FINANCE",

        "MACRO_ECONOMY":
            "MACRO_ECONOMY",

        "INTERNATIONAL_TRADE":
            "INTERNATIONAL_TRADE",

        "GENERAL_BUSINESS":
            "BUSINESS_MANAGEMENT",
    }

    return mapping.get(
        category,
        "BUSINESS_MANAGEMENT"
    )


def sanitize_question(
    raw,
    record
):

    if not isinstance(
        raw,
        dict
    ):

        return None

    question = clean_text(
        raw.get(
            "question"
        )
    )

    if len(question) < 15:

        return None

    question_type = clean_text(
        raw.get(
            "question_type"
        )
    ).upper()

    category = clean_text(
        raw.get(
            "category"
        )
    ).upper()

    difficulty = clean_text(
        raw.get(
            "difficulty"
        )
    ).upper()

    relevance = clean_text(
        raw.get(
            "placement_relevance"
        )
    ).upper()

    if question_type not in VALID_QUESTION_TYPES:

        question_type = "ANALYTICAL"

    if category not in VALID_CATEGORIES:

        category = infer_category(
            record
        )

    if difficulty not in VALID_DIFFICULTIES:

        difficulty = "MEDIUM"

    if relevance not in VALID_RELEVANCE:

        relevance = clean_text(
            record.get(
                "placement_relevance"
            )
        ).upper()

        if relevance not in VALID_RELEVANCE:

            relevance = "MEDIUM"

    key_facts = raw.get(
        "key_facts_needed",
        []
    )

    if not isinstance(
        key_facts,
        list
    ):

        key_facts = (

            [str(key_facts)]

            if key_facts

            else []
        )

    answer_points = raw.get(
        "expected_answer_points",
        []
    )

    if not isinstance(
        answer_points,
        list
    ):

        answer_points = (

            [str(answer_points)]

            if answer_points

            else []
        )

    key_facts = [

        clean_text(x)

        for x in key_facts

        if clean_text(x)
    ]

    answer_points = [

        clean_text(x)

        for x in answer_points

        if clean_text(x)
    ]

    source_basis = clean_text(
        raw.get(
            "source_basis"
        )
    )

    if not source_basis:

        source_basis = (
            "Generated from the supplied "
            "master intelligence record."
        )

    return {

        "question":
            question,

        "question_type":
            question_type,

        "category":
            category,

        "difficulty":
            difficulty,

        "placement_relevance":
            relevance,

        "key_facts_needed":
            key_facts[:8],

        "expected_answer_points":
            answer_points[:10],

        "source_basis":
            source_basis,
    }


# ============================================================
# LOAD EXISTING QUESTION BANK
# ============================================================

def load_existing_bank():

    if not OUTPUT_PATH.exists():

        return {

            "database_version":
                "v1",

            "created_at":
                now_iso(),

            "last_updated":
                now_iso(),

            "question_count":
                0,

            "questions":
                [],
        }

    data = load_json(
        OUTPUT_PATH
    )

    if not isinstance(
        data,
        dict
    ):

        raise ValueError(
            "Existing question bank is not "
            "a JSON object."
        )

    data.setdefault(
        "database_version",
        "v1"
    )

    data.setdefault(
        "created_at",
        now_iso()
    )

    data.setdefault(
        "last_updated",
        now_iso()
    )

    data.setdefault(
        "question_count",
        len(
            data.get(
                "questions",
                []
            )
        )
    )

    data.setdefault(
        "questions",
        []
    )

    return data


# ============================================================
# EXISTING QUESTION FINGERPRINTS
# ============================================================

def existing_fingerprints(
    bank
):

    fingerprints = set()

    for item in bank.get(
        "questions",
        []
    ):

        question = item.get(
            "question",
            ""
        )

        if question:

            fingerprints.add(
                question_fingerprint(
                    question
                )
            )

    return fingerprints


# ============================================================
# RECORDS ALREADY REPRESENTED
# ============================================================

def existing_source_records(
    bank
):

    result = set()

    for item in bank.get(
        "questions",
        []
    ):

        source_record_ids = (
            item.get(
                "source_record_ids",
                []
            )
            or []
        )

        for record_id in source_record_ids:

            result.add(
                record_id
            )

    return result


# ============================================================
# CREATE QUESTION RECORD
# ============================================================

def make_record_question(
    sanitized,
    record,
    gov_items,
    related_connections,
    question_id
):

    source_record_id = record.get(
        "record_id",
        ""
    )

    source_event_ids = []

    connection_ids = []

    for connection in related_connections:

        source_event_ids.extend(
            connection.get(
                "source_event_ids",
                []
            )
            or []
        )

        connection_id = (
            connection.get(
                "connection_id"
            )
        )

        if connection_id:

            connection_ids.append(
                connection_id
            )

    source_event_ids = list(
        dict.fromkeys(
            source_event_ids
        )
    )

    connection_ids = list(
        dict.fromkeys(
            connection_ids
        )
    )

    government_ids = [

        item.get(
            "initiative_id",
            ""
        )

        for item in gov_items

        if item.get(
            "initiative_id"
        )
    ]

    return {

        "question_id":
            question_id,

        "question":
            sanitized[
                "question"
            ],

        "question_type":
            sanitized[
                "question_type"
            ],

        "category":
            sanitized[
                "category"
            ],

        "difficulty":
            sanitized[
                "difficulty"
            ],

        "placement_relevance":
            sanitized[
                "placement_relevance"
            ],

        "source_record_ids":
            [source_record_id],

        "source_event_ids":
            source_event_ids,

        "related_connection_ids":
            connection_ids,

        "government_intelligence_ids":
            list(
                dict.fromkeys(
                    government_ids
                )
            ),

        "key_facts_needed":
            sanitized[
                "key_facts_needed"
            ],

        "expected_answer_points":
            sanitized[
                "expected_answer_points"
            ],

        "source_basis":
            sanitized[
                "source_basis"
            ],

        "generated_from":
            "MASTER_INTELLIGENCE_RECORD",

        "newspaper":
            record.get(
                "newspaper",
                ""
            ),

        "date":
            record.get(
                "date",
                ""
            ),

        "page":
            record.get(
                "page",
                ""
            ),

        "source_headline":
            record.get(
                "headline",
                ""
            ),

        "created_at":
            now_iso(),
    }


# ============================================================
# CONNECTION PROMPT
# ============================================================

def build_connection_prompt(
    connection,
    source_records
):

    sources = [

        compact_master_record(
            record
        )

        for record in source_records
    ]

    prompt = f"""
You are creating placement and group-discussion
questions from a validated cross-event connection.

============================================================
VALIDATED / REVIEWED CONNECTION
============================================================

{json.dumps(
    compact_connection(connection),
    ensure_ascii=False,
    indent=2
)}

============================================================
SOURCE RECORDS
============================================================

{json.dumps(
    sources,
    ensure_ascii=False,
    indent=2
)}

============================================================
TASK
============================================================

Generate exactly 2 questions:

1. One CROSS_EVENT_GD question.
2. One CASE_BASED or ANALYTICAL question.

============================================================
IMPORTANT
============================================================

The connection is a DERIVED relationship.

It may not have been explicitly stated by either source.

Therefore:

- Do not present the relationship as proven causation.
- Do not say the newspaper established the relationship.
- Use careful wording such as:
  "How could..."
  "Discuss whether..."
  "What mechanisms could..."
  "To what extent could..."
  where appropriate.

Use only supplied facts.

Do not invent:
- numbers
- policies
- events
- causes
- outcomes
- statistics

Questions should be useful for MBA/PGDM Agribusiness
placement preparation.

Return ONLY valid JSON.

Structure:

{{
  "questions": [
    {{
      "question": "...",
      "question_type": "CROSS_EVENT_GD",
      "category": "CROSS_SECTOR",
      "difficulty": "HARD",
      "placement_relevance": "HIGH",
      "key_facts_needed": [
        "..."
      ],
      "expected_answer_points": [
        "..."
      ],
      "source_basis": "..."
    }}
  ]
}}
"""

    return prompt


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "PLACEMENT / GD QUESTION BANK BUILDER v1"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # CHECK INPUT FILES
    # --------------------------------------------------------

    required_files = [

        MASTER_PATH,

        GOVERNMENT_PATH,

        CONNECTIONS_PATH,
    ]

    for path in required_files:

        if not path.exists():

            raise FileNotFoundError(
                f"Required input not found:\n{path}"
            )

    # --------------------------------------------------------
    # LOAD DATABASES
    # --------------------------------------------------------

    master_data = load_json(
        MASTER_PATH
    )

    government_data = load_json(
        GOVERNMENT_PATH
    )

    connections_data = load_json(
        CONNECTIONS_PATH
    )

    records = get_master_records(
        master_data
    )

    initiatives = get_government_initiatives(
        government_data
    )

    connections = get_connections(
        connections_data
    )

    # --------------------------------------------------------
    # BUILD INDEXES
    # --------------------------------------------------------

    government_index = (
        build_government_index(
            initiatives
        )
    )

    connection_index = (
        build_connection_index(
            connections
        )
    )

    # --------------------------------------------------------
    # LOAD EXISTING QUESTION BANK
    # --------------------------------------------------------

    bank = load_existing_bank()

    existing_questions = bank.get(
        "questions",
        []
    )

    existing_count = len(
        existing_questions
    )

    fingerprints = (
        existing_fingerprints(
            bank
        )
    )

    existing_ids = {

        question.get(
            "question_id"
        )

        for question in existing_questions

        if question.get(
            "question_id"
        )
    }

    represented_records = (
        existing_source_records(
            bank
        )
    )

    new_questions = []

    skipped_duplicates = 0

    failed_records = 0

    # --------------------------------------------------------
    # DISPLAY INPUT SUMMARY
    # --------------------------------------------------------

    print()

    print(
        f"Master records: "
        f"{len(records)}"
    )

    print(
        f"Government initiatives: "
        f"{len(initiatives)}"
    )

    print(
        f"Connections: "
        f"{len(connections)}"
    )

    print(
        f"Existing questions: "
        f"{existing_count}"
    )

    print(
        f"Records already represented: "
        f"{len(represented_records)}"
    )

    print()

    # ========================================================
    # STAGE 1
    # GENERATE QUESTIONS FROM MASTER RECORDS
    # ========================================================

    print(
        "=" * 70
    )

    print(
        "STAGE 1 — MASTER INTELLIGENCE QUESTIONS"
    )

    print(
        "=" * 70
    )

    for index, record in enumerate(
        records,
        start=1
    ):

        record_id = record.get(
            "record_id",
            ""
        )

        headline = clean_text(
            record.get(
                "headline",
                ""
            ),
            100
        )

        # ----------------------------------------------------
        # Missing record ID
        # ----------------------------------------------------

        if not record_id:

            print(
                f"[{index}/{len(records)}] "
                "SKIP — missing record_id"
            )

            failed_records += 1

            continue

        # ----------------------------------------------------
        # Future-proof incremental processing
        # ----------------------------------------------------

        if record_id in represented_records:

            print(
                f"[{index}/{len(records)}] "
                f"SKIP existing — {headline}"
            )

            continue

        print(
            f"[{index}/{len(records)}] "
            f"Generating — {headline}"
        )

        gov_items = (
            government_index.get(
                record_id,
                []
            )
        )

        related_connections = (
            connection_index.get(
                record_id,
                []
            )
        )

        prompt = build_prompt(
            record,
            gov_items,
            related_connections
        )

        try:

            result = call_gemini(
                prompt
            )

            raw_questions = result.get(
                "questions",
                []
            )

            if not isinstance(
                raw_questions,
                list
            ):

                raise ValueError(
                    "Gemini output does not contain "
                    "a valid questions list."
                )

            accepted = 0

            for raw_question in raw_questions:

                sanitized = (
                    sanitize_question(
                        raw_question,
                        record
                    )
                )

                if not sanitized:

                    continue

                fingerprint = (
                    question_fingerprint(
                        sanitized[
                            "question"
                        ]
                    )
                )

                # --------------------------------------------
                # Duplicate check
                # --------------------------------------------

                if fingerprint in fingerprints:

                    skipped_duplicates += 1

                    continue

                question_id = (
                    make_question_id(
                        existing_ids,
                        fingerprint
                    )
                )

                final_question = (
                    make_record_question(

                        sanitized=
                            sanitized,

                        record=
                            record,

                        gov_items=
                            gov_items,

                        related_connections=
                            related_connections,

                        question_id=
                            question_id,
                    )
                )

                new_questions.append(
                    final_question
                )

                fingerprints.add(
                    fingerprint
                )

                existing_ids.add(
                    question_id
                )

                accepted += 1

            print(
                f"    Added: {accepted}"
            )

        except Exception as exc:

            failed_records += 1

            print(
                f"    FAILED: {exc}"
            )

        # ----------------------------------------------------
        # Rate-limit protection
        # ----------------------------------------------------

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    # ========================================================
    # STAGE 2
    # CROSS-EVENT CONNECTION QUESTIONS
    # ========================================================

    print()

    print(
        "=" * 70
    )

    print(
        "STAGE 2 — CROSS-EVENT QUESTIONS"
    )

    print(
        "=" * 70
    )

    record_map = {

        record.get(
            "record_id"
        ):
            record

        for record in records

        if record.get(
            "record_id"
        )
    }

    for index, connection in enumerate(
        connections,
        start=1
    ):

        connection_id = connection.get(
            "connection_id",
            ""
        )

        validation_status = (
            connection.get(
                "validation_status"
            )
        )

        # ----------------------------------------------------
        # Allow VALIDATED and REVIEW
        # ----------------------------------------------------

        if validation_status not in {

            "VALIDATED",

            "REVIEW",

            "",

            None,

        }:

            print(
                f"[{index}/{len(connections)}] "
                f"SKIP validation status — "
                f"{connection_id}"
            )

            continue

        source_ids = (
            connection.get(
                "source_record_ids",
                []
            )
            or []
        )

        # ----------------------------------------------------
        # Need at least two source records
        # ----------------------------------------------------

        if len(
            set(source_ids)
        ) < 2:

            print(
                f"[{index}/{len(connections)}] "
                f"SKIP — fewer than 2 source records"
            )

            continue

        source_records = [

            record_map[record_id]

            for record_id in source_ids

            if record_id in record_map
        ]

        if len(source_records) < 2:

            print(
                f"[{index}/{len(connections)}] "
                f"SKIP — source records unavailable"
            )

            continue

        print()

        print(
            f"[{index}/{len(connections)}] "
            f"{connection_id}"
        )

        print(
            f"    Relationship: "
            f"{connection.get('relationship', '')}"
        )

        try:

            prompt = build_connection_prompt(
                connection,
                source_records
            )

            result = call_gemini(
                prompt
            )

            raw_questions = result.get(
                "questions",
                []
            )

            if not isinstance(
                raw_questions,
                list
            ):

                raise ValueError(
                    "Gemini output does not contain "
                    "a valid questions list."
                )

            accepted = 0

            for raw_question in raw_questions:

                base_record = (
                    source_records[0]
                )

                sanitized = (
                    sanitize_question(
                        raw_question,
                        base_record
                    )
                )

                if not sanitized:

                    continue

                # ------------------------------------------------
                # Force appropriate types for connection questions
                # ------------------------------------------------

                if sanitized[
                    "question_type"
                ] not in {

                    "CROSS_EVENT_GD",

                    "CASE_BASED",

                    "ANALYTICAL",

                }:

                    sanitized[
                        "question_type"
                    ] = "ANALYTICAL"

                fingerprint = (
                    question_fingerprint(
                        sanitized[
                            "question"
                        ]
                    )
                )

                if fingerprint in fingerprints:

                    skipped_duplicates += 1

                    continue

                question_id = (
                    make_question_id(
                        existing_ids,
                        fingerprint
                    )
                )

                source_event_ids = list(
                    dict.fromkeys(
                        connection.get(
                            "source_event_ids",
                            []
                        )
                        or []
                    )
                )

                government_ids = []

                for source_record in source_records:

                    source_record_id = (
                        source_record.get(
                            "record_id",
                            ""
                        )
                    )

                    for item in (
                        government_index.get(
                            source_record_id,
                            []
                        )
                    ):

                        initiative_id = (
                            item.get(
                                "initiative_id"
                            )
                        )

                        if initiative_id:

                            government_ids.append(
                                initiative_id
                            )

                final_question = {

                    "question_id":
                        question_id,

                    "question":
                        sanitized[
                            "question"
                        ],

                    "question_type":
                        sanitized[
                            "question_type"
                        ],

                    "category":
                        sanitized[
                            "category"
                        ],

                    "difficulty":
                        sanitized[
                            "difficulty"
                        ],

                    "placement_relevance":
                        sanitized[
                            "placement_relevance"
                        ],

                    "source_record_ids":
                        source_ids,

                    "source_event_ids":
                        source_event_ids,

                    "related_connection_ids":
                        [connection_id],

                    "government_intelligence_ids":
                        list(
                            dict.fromkeys(
                                government_ids
                            )
                        ),

                    "key_facts_needed":
                        sanitized[
                            "key_facts_needed"
                        ],

                    "expected_answer_points":
                        sanitized[
                            "expected_answer_points"
                        ],

                    "source_basis":
                        sanitized[
                            "source_basis"
                        ],

                    # IMPORTANT:
                    # This is intentionally CONNECTION_BANK,
                    # not VALIDATED_CONNECTION, because a
                    # connection can have REVIEW status.
                    "generated_from":
                        "CONNECTION_BANK",

                    "newspaper":
                        "Multiple",

                    "date":
                        base_record.get(
                            "date",
                            ""
                        ),

                    "page":
                        "Multiple",

                    "source_headline":
                        "Cross-event connection",

                    "created_at":
                        now_iso(),
                }

                new_questions.append(
                    final_question
                )

                fingerprints.add(
                    fingerprint
                )

                existing_ids.add(
                    question_id
                )

                accepted += 1

            print(
                f"    Added: {accepted}"
            )

        except Exception as exc:

            failed_records += 1

            print(
                f"    FAILED: {exc}"
            )

        time.sleep(
            REQUEST_DELAY_SECONDS
        )

    # ========================================================
    # COMBINE OLD + NEW
    # ========================================================

    all_questions = (
        existing_questions
        + new_questions
    )

    bank["questions"] = (
        all_questions
    )

    bank["question_count"] = (
        len(all_questions)
    )

    bank["last_updated"] = (
        now_iso()
    )

    # ========================================================
    # SAVE QUESTION BANK
    # ========================================================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    save_json(
        OUTPUT_PATH,
        bank
    )

    # ========================================================
    # STATISTICS
    # ========================================================

    type_counts = {}

    category_counts = {}

    difficulty_counts = {}

    relevance_counts = {}

    generated_from_counts = {}

    for question in all_questions:

        question_type = question.get(
            "question_type",
            "UNKNOWN"
        )

        category = question.get(
            "category",
            "UNKNOWN"
        )

        difficulty = question.get(
            "difficulty",
            "UNKNOWN"
        )

        relevance = question.get(
            "placement_relevance",
            "UNKNOWN"
        )

        generated_from = question.get(
            "generated_from",
            "UNKNOWN"
        )

        type_counts[
            question_type
        ] = (
            type_counts.get(
                question_type,
                0
            )
            + 1
        )

        category_counts[
            category
        ] = (
            category_counts.get(
                category,
                0
            )
            + 1
        )

        difficulty_counts[
            difficulty
        ] = (
            difficulty_counts.get(
                difficulty,
                0
            )
            + 1
        )

        relevance_counts[
            relevance
        ] = (
            relevance_counts.get(
                relevance,
                0
            )
            + 1
        )

        generated_from_counts[
            generated_from
        ] = (
            generated_from_counts.get(
                generated_from,
                0
            )
            + 1
        )

    # ========================================================
    # REPORT
    # ========================================================

    report_lines = [

        "PLACEMENT / GD QUESTION BANK REPORT",

        "=" * 60,

        f"Generated: {now_iso()}",

        "",

        "DATABASE INPUTS",

        "-" * 40,

        f"Master records: {len(records)}",

        f"Government initiatives: "
        f"{len(initiatives)}",

        f"Connections: {len(connections)}",

        "",

        "PROCESSING",

        "-" * 40,

        f"Existing questions before run: "
        f"{existing_count}",

        f"New questions added: "
        f"{len(new_questions)}",

        f"Duplicate questions skipped: "
        f"{skipped_duplicates}",

        f"Failed records/connections: "
        f"{failed_records}",

        f"Total questions after run: "
        f"{len(all_questions)}",

        "",

        "QUESTION TYPES",

        "-" * 40,
    ]

    for key in sorted(
        type_counts
    ):

        report_lines.append(
            f"{key}: "
            f"{type_counts[key]}"
        )

    report_lines += [

        "",

        "CATEGORIES",

        "-" * 40,
    ]

    for key in sorted(
        category_counts
    ):

        report_lines.append(
            f"{key}: "
            f"{category_counts[key]}"
        )

    report_lines += [

        "",

        "DIFFICULTY",

        "-" * 40,
    ]

    for key in sorted(
        difficulty_counts
    ):

        report_lines.append(
            f"{key}: "
            f"{difficulty_counts[key]}"
        )

    report_lines += [

        "",

        "PLACEMENT RELEVANCE",

        "-" * 40,
    ]

    for key in sorted(
        relevance_counts
    ):

        report_lines.append(
            f"{key}: "
            f"{relevance_counts[key]}"
        )

    report_lines += [

        "",

        "GENERATED FROM",

        "-" * 40,
    ]

    for key in sorted(
        generated_from_counts
    ):

        report_lines.append(
            f"{key}: "
            f"{generated_from_counts[key]}"
        )

    report_lines += [

        "",

        "PROVENANCE",

        "-" * 40,

        "Every question retains its source_record_ids.",

        "Individual questions retain newspaper, date, page "
        "and source headline.",

        "Cross-event questions retain source_event_ids "
        "and related_connection_ids.",

        "Government-linked questions retain "
        "government_intelligence_ids.",

        "",

        "FUTURE PROCESSING",

        "-" * 40,

        "The question bank is append-first.",

        "Existing questions are preserved.",

        "Existing source records are skipped.",

        "New newspaper editions can be added later.",

        "Duplicate questions are fingerprint-checked.",
    ]

    report = "\n".join(
        report_lines
    )

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            report
        )

    # ========================================================
    # FINAL TERMINAL OUTPUT
    # ========================================================

    print()

    print(
        "=" * 70
    )

    print(
        "BUILD COMPLETE"
    )

    print(
        "=" * 70
    )

    print(
        f"Existing questions: "
        f"{existing_count}"
    )

    print(
        f"New questions:      "
        f"{len(new_questions)}"
    )

    print(
        f"Duplicates skipped: "
        f"{skipped_duplicates}"
    )

    print(
        f"Failed items:       "
        f"{failed_records}"
    )

    print(
        f"Total questions:    "
        f"{len(all_questions)}"
    )

    print()

    print(
        f"JSON:   {OUTPUT_PATH}"
    )

    print(
        f"Report: {REPORT_PATH}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()