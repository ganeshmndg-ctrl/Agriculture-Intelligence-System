from pathlib import Path
import json
import re
from datetime import datetime


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# CONNECTION VALIDATOR / REFINER v1
# ============================================================

MASTER_DB = Path(
    "data/master_database_v1/"
    "MASTER_INTELLIGENCE_DATABASE_v1.json"
)

CONNECTIONS_DB = Path(
    "data/connections_bank_v1_1/"
    "CONNECTIONS_INTELLIGENCE_BANK_v1_1.json"
)

OUTPUT_DIR = Path(
    "data/connections_bank_v1_1"
)

OUTPUT_JSON = (
    OUTPUT_DIR /
    "VALIDATED_CONNECTIONS_BANK_v1.json"
)

OUTPUT_REPORT = (
    OUTPUT_DIR /
    "CONNECTION_VALIDATION_REPORT_v1.txt"
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value)


def normalize_list(value):

    if value is None:
        return []

    if isinstance(value, list):
        return [
            clean_text(x)
            for x in value
            if clean_text(x)
        ]

    if isinstance(value, str):

        text = value.strip()

        if not text:
            return []

        return [text]

    return [
        clean_text(value)
    ]


def contains_any(text, phrases):

    text = text.lower()

    return any(
        phrase.lower() in text
        for phrase in phrases
    )


# ============================================================
# LOAD DATA
# ============================================================

def load_json(path):

    if not path.exists():

        raise FileNotFoundError(
            f"File not found:\n{path.resolve()}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# RECORD EVIDENCE INDEX
# ============================================================

def build_record_index(master_data):

    records = (
        master_data.get(
            "records",
            []
        )
        if isinstance(
            master_data,
            dict
        )
        else master_data
    )

    index = {}

    for record in records:

        record_id = clean_text(
            record.get(
                "record_id"
            )
        )

        if not record_id:
            continue

        evidence_parts = [

            record.get(
                "headline",
                ""
            ),

            record.get(
                "summary",
                ""
            ),

            record.get(
                "article_text",
                ""
            ),

            record.get(
                "agriculture_impact",
                ""
            ),

            record.get(
                "why_it_matters",
                ""
            ),

            record.get(
                "reported_facts",
                []
            ),

            record.get(
                "key_facts",
                []
            ),

            record.get(
                "key_numbers",
                []
            ),

            record.get(
                "connections",
                []
            )
        ]

        evidence_text = " ".join(
            clean_text(x)
            for x in evidence_parts
        )

        index[record_id] = {
            "record": record,
            "evidence_text": evidence_text
        }

    return index


# ============================================================
# VALIDATION
# ============================================================

def validate_connection(
    connection,
    record_index
):

    problems = []
    warnings = []

    source_ids = normalize_list(
        connection.get(
            "source_record_ids"
        )
    )

    source_event_ids = normalize_list(
        connection.get(
            "source_event_ids"
        )
    )

    relationship = clean_text(
        connection.get(
            "relationship"
        )
    )

    explanation = clean_text(
        connection.get(
            "explanation"
        )
    )

    evidence = normalize_list(
        connection.get(
            "source_evidence"
        )
    )

    # --------------------------------------------------------
    # 1. Source records
    # --------------------------------------------------------

    if len(source_ids) < 2:

        problems.append(
            "Connection has fewer than two source records."
        )

    missing_records = [
        record_id
        for record_id in source_ids
        if record_id not in record_index
    ]

    if missing_records:

        problems.append(
            "Missing source records: "
            + ", ".join(
                missing_records
            )
        )

    # --------------------------------------------------------
    # 2. Source events
    # --------------------------------------------------------

    if len(
        set(source_event_ids)
    ) < 2:

        problems.append(
            "Connection does not span at least two "
            "different underlying events."
        )

    # --------------------------------------------------------
    # 3. Required text
    # --------------------------------------------------------

    if not relationship:

        problems.append(
            "Relationship statement is empty."
        )

    if not explanation:

        problems.append(
            "Explanation is empty."
        )

    if len(evidence) < 2:

        problems.append(
            "Fewer than two evidence items supplied."
        )

    # --------------------------------------------------------
    # 4. Evidence provenance
    # --------------------------------------------------------

    combined_source_text = ""

    for record_id in source_ids:

        if record_id in record_index:

            combined_source_text += " "

            combined_source_text += (
                record_index[
                    record_id
                ][
                    "evidence_text"
                ]
            )

    # --------------------------------------------------------
    # 5. Unsupported causal language
    # --------------------------------------------------------

    strong_causal_words = [
        "caused",
        "causes",
        "causing",
        "resulted in",
        "results in",
        "resulting in",
        "led to",
        "leads to",
        "driving",
        "drives",
        "because of",
        "due to"
    ]

    if contains_any(
        relationship,
        strong_causal_words
    ):

        warnings.append(
            "Relationship uses strong causal language "
            "and should be checked against source evidence."
        )

    # --------------------------------------------------------
    # 6. Very strong certainty language
    # --------------------------------------------------------

    certainty_words = [
        "definitely",
        "certainly",
        "will",
        "guarantees",
        "guaranteed",
        "proves",
        "always"
    ]

    if contains_any(
        relationship,
        certainty_words
    ):

        warnings.append(
            "Relationship contains strong certainty language."
        )

    # --------------------------------------------------------
    # 7. Agriculture relevance
    # --------------------------------------------------------

    valid_agri = {
        "DIRECT",
        "INDIRECT",
        "CONTEXTUAL",
        "NONE"
    }

    agri = clean_text(
        connection.get(
            "agriculture_relevance"
        )
    ).upper()

    if agri not in valid_agri:

        problems.append(
            "Invalid agriculture relevance value."
        )

    # --------------------------------------------------------
    # 8. Placement relevance
    # --------------------------------------------------------

    valid_placement = {
        "HIGH",
        "MEDIUM",
        "LOW"
    }

    placement = clean_text(
        connection.get(
            "placement_relevance"
        )
    ).upper()

    if placement not in valid_placement:

        problems.append(
            "Invalid placement relevance value."
        )

    # --------------------------------------------------------
    # 9. Confidence
    # --------------------------------------------------------

    valid_confidence = {
        "HIGH",
        "MEDIUM",
        "LOW"
    }

    confidence = clean_text(
        connection.get(
            "confidence"
        )
    ).upper()

    if confidence not in valid_confidence:

        problems.append(
            "Invalid confidence value."
        )

    # --------------------------------------------------------
    # 10. Final status
    # --------------------------------------------------------

    if problems:

        status = "REJECTED"

    elif warnings:

        status = "REVIEW"

    else:

        status = "VALIDATED"

    return {
        "status": status,
        "problems": problems,
        "warnings": warnings
    }


# ============================================================
# SAFE REFINEMENT
# ============================================================

def refine_connection(
    connection,
    validation
):

    refined = dict(
        connection
    )

    relationship = clean_text(
        refined.get(
            "relationship"
        )
    )

    explanation = clean_text(
        refined.get(
            "explanation"
        )
    )

    # --------------------------------------------------------
    # Conservative wording refinement
    #
    # We do NOT invent new facts.
    # We only soften an overly strong causal statement when
    # the connection is DERIVED.
    # --------------------------------------------------------

    if (
        validation["status"] == "REVIEW"
        and
        clean_text(
            refined.get(
                "connection_type"
            )
        ).upper() == "DERIVED"
    ):

        # Specific known pattern from the current bank.
        if (
            "drought-induced domestic production shortfalls"
            in relationship.lower()
            and
            "edible oil imports"
            in relationship.lower()
        ):

            refined["relationship"] = (
                "Drought-related kharif crop stress "
                "can contribute to domestic production "
                "shortfalls, which are identified as a "
                "driver of increased edible-oil import dependence."
            )

            refined["explanation"] = (
                "The drought record reports stress on "
                "kharif crops, while the edible-oil import "
                "record identifies domestic production "
                "shortfalls as a driver of increased imports. "
                "Taken together, the records support a derived "
                "relationship between agricultural production "
                "stress and import dependence, without "
                "attributing the entire import increase to the "
                "reported drought."
            )

            refined["confidence"] = "MEDIUM"

            refined["validation_note"] = (
                "Causal wording was softened because the "
                "source records support a derived relationship "
                "but do not establish that the reported drought "
                "caused the entire import increase."
            )

    return refined


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("AGRICULTURE INTELLIGENCE SYSTEM")
    print("CONNECTION VALIDATOR / REFINER v1")
    print("=" * 80)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print()
    print("Loading Master Intelligence Database...")

    master_data = load_json(
        MASTER_DB
    )

    print(
        "Loading Connections Bank v1.1..."
    )

    connection_data = load_json(
        CONNECTIONS_DB
    )

    connections = connection_data.get(
        "connections",
        []
    )

    print(
        f"Master records: "
        f"{len(master_data.get('records', []))}"
    )

    print(
        f"Connections loaded: "
        f"{len(connections)}"
    )

    # --------------------------------------------------------
    # Build evidence index
    # --------------------------------------------------------

    record_index = build_record_index(
        master_data
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validated = []

    rejected = []

    review = []

    warnings_total = 0

    for connection in connections:

        result = validate_connection(
            connection,
            record_index
        )

        warnings_total += len(
            result["warnings"]
        )

        refined = refine_connection(
            connection,
            result
        )

        refined[
            "validation_status"
        ] = result[
            "status"
        ]

        refined[
            "validation_problems"
        ] = result[
            "problems"
        ]

        refined[
            "validation_warnings"
        ] = result[
            "warnings"
        ]

        if result["status"] == "REJECTED":

            rejected.append(
                refined
            )

        elif result["status"] == "REVIEW":

            review.append(
                refined
            )

            validated.append(
                refined
            )

        else:

            validated.append(
                refined
            )

    # --------------------------------------------------------
    # Build output
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
            "Validated Connections Intelligence Bank",

        "database_version":
            "v1",

        "created_at":
            now,

        "last_updated":
            now,

        "source_connections_bank":
            str(
                CONNECTIONS_DB
            ),

        "source_master_database":
            str(
                MASTER_DB
            ),

        "input_connection_count":
            len(connections),

        "validated_connection_count":
            len(validated),

        "review_connection_count":
            len(review),

        "rejected_connection_count":
            len(rejected),

        "connections":
            validated,

        "rejected_connections":
            rejected
    }

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
    # Report
    # --------------------------------------------------------

    report_lines = [

        "=" * 80,

        "AGRICULTURE INTELLIGENCE SYSTEM",

        "CONNECTION VALIDATION / REFINEMENT REPORT v1",

        "=" * 80,

        "",

        f"Input connections: {len(connections)}",

        f"Validated connections: {len(validated)}",

        f"Connections requiring review: {len(review)}",

        f"Rejected connections: {len(rejected)}",

        f"Warnings generated: {warnings_total}",

        "",

        "VALIDATED CONNECTIONS",

        "-" * 80
    ]

    for connection in validated:

        report_lines.append(
            f"{connection.get('connection_id', '')} | "
            f"{connection.get('validation_status', '')} | "
            f"{connection.get('relationship', '')}"
        )

        if connection.get(
            "validation_warnings"
        ):

            for warning in connection[
                "validation_warnings"
            ]:

                report_lines.append(
                    f"  WARNING: {warning}"
                )

        if connection.get(
            "validation_note"
        ):

            report_lines.append(
                "  REFINEMENT: "
                + connection[
                    "validation_note"
                ]
            )

    report_lines.extend([

        "",

        "REJECTED CONNECTIONS",

        "-" * 80
    ])

    for connection in rejected:

        report_lines.append(
            f"{connection.get('connection_id', '')}"
        )

        for problem in connection.get(
            "validation_problems",
            []
        ):

            report_lines.append(
                f"  - {problem}"
            )

    report_lines.extend([

        "",

        "VALIDATION RULES",

        "-" * 80,

        "• At least two source records required.",

        "• At least two different underlying events required.",

        "• All source record IDs must exist in the Master Database.",

        "• Relationship and explanation must be present.",

        "• At least two evidence items required.",

        "• Strong causal wording is flagged for review.",

        "• Strong certainty wording is flagged for review.",

        "• No external facts are introduced.",

        "",

        "OUTPUT",

        "-" * 80,

        str(
            OUTPUT_JSON.resolve()
        ),

        str(
            OUTPUT_REPORT.resolve()
        ),

        "",

        "The Master Intelligence Database was not modified.",

        "",

        "=" * 80
    ])

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8",
        newline="\n"
    ) as f:

        f.write(
            "\n".join(
                report_lines
            )
        )

    # --------------------------------------------------------
    # Console
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("CONNECTION VALIDATION COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Input connections: "
        f"{len(connections)}"
    )

    print(
        f"Validated connections: "
        f"{len(validated)}"
    )

    print(
        f"Review connections: "
        f"{len(review)}"
    )

    print(
        f"Rejected connections: "
        f"{len(rejected)}"
    )

    print(
        f"Warnings: "
        f"{warnings_total}"
    )

    print()
    print(
        f"Validated bank:\n"
        f"{OUTPUT_JSON.resolve()}"
    )

    print()
    print(
        f"Report:\n"
        f"{OUTPUT_REPORT.resolve()}"
    )

    print()
    print(
        "The Master Intelligence Database was not modified."
    )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()