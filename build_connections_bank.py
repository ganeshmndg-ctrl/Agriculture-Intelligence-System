from pathlib import Path
import json
import os
import time
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# CONNECTIONS / RELATIONSHIP INTELLIGENCE BANK v1
# ============================================================

MASTER_DB = Path(
    "data/master_database_v1/"
    "MASTER_INTELLIGENCE_DATABASE_v1.json"
)

OUTPUT_DIR = Path("data/connections_bank_v1")

OUTPUT_JSON = (
    OUTPUT_DIR /
    "CONNECTIONS_INTELLIGENCE_BANK_v1.json"
)

OUTPUT_REPORT = (
    OUTPUT_DIR /
    "CONNECTIONS_BANK_REPORT_v1.txt"
)

MODEL_NAME = "gemini-3.1-flash-lite"

REQUEST_DELAY = 5
MAX_RETRIES = 3


# ============================================================
# GEMINI SETUP
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY was not found in the .env file."
    )

client = genai.Client(api_key=API_KEY)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """
    Convert arbitrary values into clean text suitable for prompts.
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return "; ".join(
            clean_text(item)
            for item in value
            if clean_text(item)
        )

    if isinstance(value, dict):
        parts = []

        for key, item in value.items():
            item_text = clean_text(item)

            if item_text:
                parts.append(
                    f"{key}: {item_text}"
                )

        return " | ".join(parts)

    return str(value)


def normalize_list(value):
    """
    Convert a field into a clean list of strings.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return [
            clean_text(item)
            for item in value
            if clean_text(item)
        ]

    if isinstance(value, str):
        text = value.strip()

        if not text:
            return []

        return [text]

    return [clean_text(value)]


def make_record_digest(record):
    """
    Create a compact but information-rich representation
    of a master database record.
    """

    return {
        "record_id": record.get("record_id", ""),
        "newspaper": record.get("newspaper", ""),
        "date": record.get("date", ""),
        "page": record.get("page", ""),
        "headline": record.get("headline", ""),
        "content_type": record.get("content_type", ""),
        "primary_category": record.get(
            "primary_category", ""
        ),
        "secondary_categories": normalize_list(
            record.get("secondary_categories")
        ),
        "intelligence_type": record.get(
            "intelligence_type", ""
        ),
        "agriculture_connection": record.get(
            "agriculture_connection", ""
        ),
        "agriculture_relevance": record.get(
            "agriculture_relevance", ""
        ),
        "placement_relevance": record.get(
            "placement_relevance", ""
        ),
        "summary": clean_text(
            record.get("summary")
        ),
        "topics": normalize_list(
            record.get("topics")
        ),
        "reported_facts": normalize_list(
            record.get("reported_facts")
        ),
        "interpretations": normalize_list(
            record.get("interpretations")
        ),
        "key_facts": normalize_list(
            record.get("key_facts")
        ),
        "key_numbers": normalize_list(
            record.get("key_numbers")
        ),
        "agriculture_impact": clean_text(
            record.get("agriculture_impact")
        ),
        "why_it_matters": clean_text(
            record.get("why_it_matters")
        ),
        "connections": normalize_list(
            record.get("connections")
        ),
        "government_schemes": normalize_list(
            record.get("government_schemes")
        ),
        "placement_questions": normalize_list(
            record.get("placement_questions")
        ),
    }


def call_gemini(prompt):
    """
    Call Gemini with retry handling for temporary failures.
    """

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            return response.text

        except Exception as e:

            error_text = str(e)

            print(
                f"Gemini attempt {attempt}/{MAX_RETRIES} failed:"
            )

            print(error_text[:500])

            if attempt < MAX_RETRIES:

                wait_time = 20 * attempt

                print(
                    f"Waiting {wait_time} seconds before retry..."
                )

                time.sleep(wait_time)

            else:
                raise


def parse_json_response(text):
    """
    Safely parse Gemini JSON output.
    """

    text = text.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return json.loads(text)


# ============================================================
# GEMINI CONNECTION PROMPT
# ============================================================

def build_connection_prompt(records):
    """
    Build the relationship-identification prompt.
    """

    records_json = json.dumps(
        records,
        ensure_ascii=False,
        indent=2
    )

    return f"""
You are the relationship-intelligence engine of an
Agriculture Intelligence and Placement Preparation System.

You are given a set of newspaper intelligence records from
Business Standard and Economic Times.

Your task is to identify meaningful relationships BETWEEN
THESE RECORDS.

IMPORTANT RULES:

1. Do not invent facts.
2. Use only information contained in the supplied records.
3. Do not use outside knowledge.
4. Do not assume two records are connected merely because
   they belong to the same broad category.
5. Prefer strong, explainable relationships.
6. A relationship may connect two or more records.
7. Duplicate coverage of the same event should NOT be treated
   as a new substantive relationship.
8. Every connection must cite its source record_id values.
9. Keep the relationship useful for agriculture intelligence,
   business analysis, banking/finance understanding,
   international trade, policy understanding, or placement/GD.
10. If there is no meaningful relationship, return an empty
    connections list.

CONNECTION TYPES:

DIRECT:
The supplied records explicitly establish or strongly indicate
the relationship.

DERIVED:
The relationship is a reasonable inference from facts present
across the supplied records.

CONTEXTUAL:
The relationship is useful for understanding the broader issue,
but the supplied records do not directly establish it.

Do NOT create a connection simply because two articles share a
keyword.

For each meaningful connection return:

- connection_id
- source_record_ids
- connection_type
- entities
- relationship
- chain
- explanation
- agriculture_relevance
- placement_relevance
- placement_questions
- confidence
- source_evidence

Definitions:

entities:
Important entities/concepts involved.

relationship:
One concise statement describing how the records connect.

chain:
A short causal or thematic chain, for example:
["Drought", "crop production risk", "food prices"]

explanation:
Explain the relationship using only the supplied records.

agriculture_relevance:
DIRECT / INDIRECT / CONTEXTUAL / NONE

placement_relevance:
HIGH / MEDIUM / LOW

confidence:
HIGH / MEDIUM / LOW

source_evidence:
Short factual evidence from the supplied records.
Do not fabricate quotations.

placement_questions:
Questions that could be useful for MBA/ABM placement,
interviews or group discussions.

Return ONLY valid JSON in this exact structure:

{{
  "connections": [
    {{
      "connection_id": "",
      "source_record_ids": [],
      "connection_type": "DIRECT",
      "entities": [],
      "relationship": "",
      "chain": [],
      "explanation": "",
      "agriculture_relevance": "DIRECT",
      "placement_relevance": "HIGH",
      "placement_questions": [],
      "confidence": "HIGH",
      "source_evidence": []
    }}
  ]
}}

NEWSPAPER RECORDS:

{records_json}
"""


# ============================================================
# EXISTING CONNECTION IDS
# ============================================================

def load_existing_bank():
    """
    Load the existing Connections Bank if present.
    """

    if not OUTPUT_JSON.exists():
        return {
            "connections": []
        }

    try:

        with open(
            OUTPUT_JSON,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, dict):
            return data

    except Exception as e:

        print(
            "Warning: Existing Connections Bank could not "
            f"be loaded: {e}"
        )

    return {
        "connections": []
    }


def connection_signature(connection):
    """
    Create a stable duplicate signature.

    Order of record IDs does not matter.
    """

    ids = connection.get(
        "source_record_ids",
        []
    )

    ids = sorted(
        str(x)
        for x in ids
    )

    relationship = clean_text(
        connection.get("relationship")
    ).lower()

    return (
        tuple(ids),
        relationship
    )


# ============================================================
# NORMALIZATION
# ============================================================

VALID_CONNECTION_TYPES = {
    "DIRECT",
    "DERIVED",
    "CONTEXTUAL"
}

VALID_AGRI = {
    "DIRECT",
    "INDIRECT",
    "CONTEXTUAL",
    "NONE"
}

VALID_PLACEMENT = {
    "HIGH",
    "MEDIUM",
    "LOW"
}

VALID_CONFIDENCE = {
    "HIGH",
    "MEDIUM",
    "LOW"
}


def normalize_connection(connection):

    if not isinstance(connection, dict):
        return None

    source_ids = normalize_list(
        connection.get("source_record_ids")
    )

    if len(source_ids) < 2:
        return None

    connection_type = clean_text(
        connection.get("connection_type")
    ).upper()

    if connection_type not in VALID_CONNECTION_TYPES:
        connection_type = "CONTEXTUAL"

    agriculture_relevance = clean_text(
        connection.get("agriculture_relevance")
    ).upper()

    if agriculture_relevance not in VALID_AGRI:
        agriculture_relevance = "NONE"

    placement_relevance = clean_text(
        connection.get("placement_relevance")
    ).upper()

    if placement_relevance not in VALID_PLACEMENT:
        placement_relevance = "LOW"

    confidence = clean_text(
        connection.get("confidence")
    ).upper()

    if confidence not in VALID_CONFIDENCE:
        confidence = "LOW"

    normalized = {
        "connection_id": clean_text(
            connection.get("connection_id")
        ),
        "source_record_ids": source_ids,
        "connection_type": connection_type,
        "entities": normalize_list(
            connection.get("entities")
        ),
        "relationship": clean_text(
            connection.get("relationship")
        ),
        "chain": normalize_list(
            connection.get("chain")
        ),
        "explanation": clean_text(
            connection.get("explanation")
        ),
        "agriculture_relevance": agriculture_relevance,
        "placement_relevance": placement_relevance,
        "placement_questions": normalize_list(
            connection.get("placement_questions")
        ),
        "confidence": confidence,
        "source_evidence": normalize_list(
            connection.get("source_evidence")
        )
    }

    if not normalized["relationship"]:
        return None

    return normalized


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("AGRICULTURE INTELLIGENCE SYSTEM")
    print("CONNECTIONS / RELATIONSHIP INTELLIGENCE BANK v1")
    print("=" * 80)

    # --------------------------------------------------------
    # Load master database
    # --------------------------------------------------------

    if not MASTER_DB.exists():

        raise FileNotFoundError(
            f"Master database not found:\n{MASTER_DB.resolve()}"
        )

    print()
    print("Loading master database...")

    with open(
        MASTER_DB,
        "r",
        encoding="utf-8"
    ) as f:

        master_data = json.load(f)

    if isinstance(master_data, dict):

        records = master_data.get(
            "records",
            []
        )

    else:

        records = master_data

    if not isinstance(records, list):

        raise ValueError(
            "Master database records are not stored as a list."
        )

    print(
        f"Master records loaded: {len(records)}"
    )

    if len(records) < 2:

        print(
            "Not enough records to identify relationships."
        )

        return

    # --------------------------------------------------------
    # Prepare record digests
    # --------------------------------------------------------

    print()
    print("Preparing record intelligence...")

    digests = [
        make_record_digest(record)
        for record in records
    ]

    # --------------------------------------------------------
    # Load existing bank
    # --------------------------------------------------------

    existing_bank = load_existing_bank()

    existing_connections = existing_bank.get(
        "connections",
        []
    )

    if not isinstance(existing_connections, list):
        existing_connections = []

    print(
        f"Existing connections: "
        f"{len(existing_connections)}"
    )

    # --------------------------------------------------------
    # For v1, analyze all records together.
    # --------------------------------------------------------

    print()
    print("Sending records to Gemini for relationship analysis...")
    print(
        "This may take some time because relationship "
        "identification requires cross-story comparison."
    )

    prompt = build_connection_prompt(
        digests
    )

    response_text = call_gemini(
        prompt
    )

    time.sleep(REQUEST_DELAY)

    result = parse_json_response(
        response_text
    )

    raw_connections = result.get(
        "connections",
        []
    )

    if not isinstance(raw_connections, list):
        raw_connections = []

    print()
    print(
        f"Gemini returned "
        f"{len(raw_connections)} candidate connections."
    )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    new_connections = []

    for raw in raw_connections:

        normalized = normalize_connection(
            raw
        )

        if normalized is None:
            continue

        new_connections.append(
            normalized
        )

    # --------------------------------------------------------
    # Existing signatures
    # --------------------------------------------------------

    existing_signatures = {
        connection_signature(connection)
        for connection in existing_connections
    }

    # --------------------------------------------------------
    # Assign stable IDs and append only new connections
    # --------------------------------------------------------

    next_number = 1

    for connection in existing_connections:

        cid = clean_text(
            connection.get("connection_id")
        )

        if cid.startswith("CONN_"):

            try:

                number = int(
                    cid.replace(
                        "CONN_",
                        ""
                    )
                )

                next_number = max(
                    next_number,
                    number + 1
                )

            except ValueError:
                pass

    added = 0
    skipped_duplicates = 0

    for connection in new_connections:

        signature = connection_signature(
            connection
        )

        if signature in existing_signatures:

            skipped_duplicates += 1
            continue

        connection["connection_id"] = (
            f"CONN_{next_number:04d}"
        )

        next_number += 1

        existing_connections.append(
            connection
        )

        existing_signatures.add(
            signature
        )

        added += 1

    # --------------------------------------------------------
    # Ensure source provenance
    # --------------------------------------------------------

    valid_record_ids = {
        str(record.get("record_id"))
        for record in records
        if record.get("record_id")
    }

    orphan_connections = 0

    for connection in existing_connections:

        source_ids = set(
            str(x)
            for x in connection.get(
                "source_record_ids",
                []
            )
        )

        if not source_ids.issubset(
            valid_record_ids
        ):

            orphan_connections += 1

    # --------------------------------------------------------
    # Build output database
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    now = datetime.now().isoformat(
        timespec="seconds"
    )

    output_data = {
        "database_name":
            "Connections / Relationship Intelligence Bank",

        "database_version":
            "v1",

        "created_at":
            existing_bank.get(
                "created_at",
                now
            ),

        "last_updated":
            now,

        "source_master_database":
            str(MASTER_DB),

        "record_count_analyzed":
            len(records),

        "connection_count":
            len(existing_connections),

        "connections":
            existing_connections
    }

    # --------------------------------------------------------
    # Save JSON
    # --------------------------------------------------------

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
        newline="\n"
    ) as f:

        json.dump(
            output_data,
            f,
            ensure_ascii=False,
            indent=2
        )

        f.write("\n")

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    type_counts = {}

    agriculture_counts = {}

    placement_counts = {}

    confidence_counts = {}

    for connection in existing_connections:

        ctype = connection.get(
            "connection_type",
            "UNKNOWN"
        )

        type_counts[ctype] = (
            type_counts.get(
                ctype,
                0
            ) + 1
        )

        agri = connection.get(
            "agriculture_relevance",
            "UNKNOWN"
        )

        agriculture_counts[agri] = (
            agriculture_counts.get(
                agri,
                0
            ) + 1
        )

        placement = connection.get(
            "placement_relevance",
            "UNKNOWN"
        )

        placement_counts[placement] = (
            placement_counts.get(
                placement,
                0
            ) + 1
        )

        confidence = connection.get(
            "confidence",
            "UNKNOWN"
        )

        confidence_counts[confidence] = (
            confidence_counts.get(
                confidence,
                0
            ) + 1
        )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    report_lines = [

        "=" * 80,

        "AGRICULTURE INTELLIGENCE SYSTEM",

        "CONNECTIONS / RELATIONSHIP INTELLIGENCE BANK v1",

        "=" * 80,

        "",

        f"Master records analyzed: {len(records)}",

        f"Existing connections before run: "
        f"{len(existing_connections) - added}",

        f"Gemini candidate connections: "
        f"{len(raw_connections)}",

        f"Normalized new connections: "
        f"{len(new_connections)}",

        f"New connections added: {added}",

        f"Duplicate connections skipped: "
        f"{skipped_duplicates}",

        f"Total connections: "
        f"{len(existing_connections)}",

        f"Connections with orphan source IDs: "
        f"{orphan_connections}",

        "",

        "CONNECTION TYPES",

        "-" * 80,

    ]

    for key, value in sorted(
        type_counts.items()
    ):

        report_lines.append(
            f"{key}: {value}"
        )

    report_lines.extend([

        "",

        "AGRICULTURE RELEVANCE",

        "-" * 80,

    ])

    for key, value in sorted(
        agriculture_counts.items()
    ):

        report_lines.append(
            f"{key}: {value}"
        )

    report_lines.extend([

        "",

        "PLACEMENT RELEVANCE",

        "-" * 80,

    ])

    for key, value in sorted(
        placement_counts.items()
    ):

        report_lines.append(
            f"{key}: {value}"
        )

    report_lines.extend([

        "",

        "CONFIDENCE",

        "-" * 80,

    ])

    for key, value in sorted(
        confidence_counts.items()
    ):

        report_lines.append(
            f"{key}: {value}"
        )

    report_lines.extend([

        "",

        "OUTPUT",

        "-" * 80,

        str(OUTPUT_JSON.resolve()),

        str(OUTPUT_REPORT.resolve()),

        "",

        "The Master Intelligence Database was not modified.",

        "Connections are stored separately and retain source_record_ids.",

        "The bank is append-first and designed for future newspaper editions.",

        "",

        "=" * 80,

    ])

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8",
        newline="\n"
    ) as f:

        f.write(
            "\n".join(report_lines)
        )

    # --------------------------------------------------------
    # Final console output
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("CONNECTION BANK BUILD COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Master records analyzed: {len(records)}"
    )

    print(
        f"Gemini candidates: {len(raw_connections)}"
    )

    print(
        f"New connections added: {added}"
    )

    print(
        f"Duplicates skipped: {skipped_duplicates}"
    )

    print(
        f"Total connections: {len(existing_connections)}"
    )

    print()
    print(
        f"Output JSON:\n{OUTPUT_JSON.resolve()}"
    )

    print()
    print(
        f"Report:\n{OUTPUT_REPORT.resolve()}"
    )

    print()
    print(
        "The Master Intelligence Database was not modified."
    )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()