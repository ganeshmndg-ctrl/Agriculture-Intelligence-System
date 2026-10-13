import json
from pathlib import Path
from collections import Counter


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# MASTER DATABASE INSPECTOR v2
#
# Purpose:
#   Quality-control inspection of the master database.
#
# Important design principle:
#
#   NOT EVERY FIELD MUST CONTAIN DATA.
#
#   Some fields are conditionally optional:
#       - key_numbers
#       - government_schemes
#       - connections
#       - interpretations
#
#   An article with no scheme should NOT be considered faulty.
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parent

MASTER_FILE = (
    PROJECT_ROOT
    / "data"
    / "master_database_v1"
    / "MASTER_INTELLIGENCE_DATABASE_v1.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "master_database_v1"
)

REPORT_FILE = (
    OUTPUT_DIR
    / "MASTER_DATABASE_INSPECTION_v2.txt"
)


# ------------------------------------------------------------
# REQUIRED FIELDS
# ------------------------------------------------------------

REQUIRED_FIELDS = [
    "record_id",
    "newspaper",
    "date",
    "page",
    "headline",
    "content_type",
    "primary_category",
    "intelligence_type",
    "agriculture_connection",
    "placement_relevance",
    "summary",
    "article_text",
]


# ------------------------------------------------------------
# OPTIONAL / CONDITIONAL FIELDS
# ------------------------------------------------------------

OPTIONAL_FIELDS = [
    "key_numbers",
    "government_schemes",
    "connections",
    "interpretations",
    "reported_facts",
    "key_facts",
    "agriculture_impact",
    "why_it_matters",
    "placement_questions",
]


# ------------------------------------------------------------
# VALID VALUES
# ------------------------------------------------------------

VALID_PRIMARY_CATEGORIES = {
    "BANKING_FINANCE",
    "CORE_AGRICULTURE",
    "GENERAL_BUSINESS",
    "INTERNATIONAL_TRADE",
    "MACRO_ECONOMY",
}


VALID_INTELLIGENCE_TYPES = {
    "CORE_INTELLIGENCE",
    "PLACEMENT_INTELLIGENCE",
}


VALID_AGRICULTURE_CONNECTIONS = {
    "DIRECT",
    "INDIRECT",
    "CONTEXTUAL",
    "NONE",
}


VALID_PLACEMENT_RELEVANCE = {
    "HIGH",
    "MEDIUM",
    "LOW",
}


VALID_CONTENT_TYPES = {
    "article",
    "snippet",
}


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def is_empty(value):

    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, list):
        return len(value) == 0

    if isinstance(value, dict):
        return len(value) == 0

    return False


def normalize_headline(text):

    if not isinstance(text, str):
        return ""

    return " ".join(
        text.lower()
        .strip()
        .split()
    )


def load_database():

    if not MASTER_FILE.exists():

        raise FileNotFoundError(
            f"Master database not found:\n"
            f"{MASTER_FILE}\n\n"
            f"Run build_master_database.py first."
        )

    with open(
        MASTER_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ------------------------------------------------------------
# REQUIRED FIELD CHECK
# ------------------------------------------------------------

def inspect_required_fields(records):

    missing_by_record = {}

    missing_counts = Counter()

    for record in records:

        record_id = record.get(
            "record_id",
            "UNKNOWN"
        )

        missing = []

        for field in REQUIRED_FIELDS:

            if field not in record:

                missing.append(field)
                missing_counts[field] += 1

                continue

            if is_empty(record[field]):

                missing.append(field)
                missing_counts[field] += 1

        if missing:

            missing_by_record[
                record_id
            ] = missing

    return (
        missing_by_record,
        missing_counts
    )


# ------------------------------------------------------------
# RECORD ID CHECK
# ------------------------------------------------------------

def inspect_record_ids(records):

    ids = [
        record.get(
            "record_id",
            ""
        )
        for record in records
    ]

    counts = Counter(ids)

    duplicates = {
        record_id: count
        for record_id, count in counts.items()
        if record_id and count > 1
    }

    missing = [
        index + 1
        for index, record in enumerate(records)
        if not record.get("record_id")
    ]

    return duplicates, missing


# ------------------------------------------------------------
# HEADLINE DUPLICATE CHECK
# ------------------------------------------------------------

def inspect_headline_duplicates(records):

    groups = {}

    for record in records:

        headline = normalize_headline(
            record.get(
                "headline",
                ""
            )
        )

        if not headline:
            continue

        groups.setdefault(
            headline,
            []
        ).append(record)

    duplicates = []

    for headline, group in groups.items():

        if len(group) > 1:

            duplicates.append({
                "headline":
                    headline,

                "records": [
                    {
                        "record_id":
                            r.get("record_id"),

                        "newspaper":
                            r.get("newspaper"),

                        "date":
                            r.get("date"),

                        "page":
                            r.get("page")
                    }

                    for r in group
                ]
            })

    return duplicates


# ------------------------------------------------------------
# CATEGORY VALIDATION
# ------------------------------------------------------------

def inspect_categories(records):

    results = {

        "invalid_primary": [],
        "invalid_intelligence": [],
        "invalid_agriculture": [],
        "invalid_placement": [],
        "invalid_content": []
    }

    for record in records:

        record_id = record.get(
            "record_id",
            "UNKNOWN"
        )

        primary = record.get(
            "primary_category",
            ""
        )

        if primary not in VALID_PRIMARY_CATEGORIES:

            results[
                "invalid_primary"
            ].append({
                "record_id": record_id,
                "value": primary
            })

        intelligence = record.get(
            "intelligence_type",
            ""
        )

        if intelligence not in VALID_INTELLIGENCE_TYPES:

            results[
                "invalid_intelligence"
            ].append({
                "record_id": record_id,
                "value": intelligence
            })

        agriculture = record.get(
            "agriculture_connection",
            ""
        )

        if agriculture not in VALID_AGRICULTURE_CONNECTIONS:

            results[
                "invalid_agriculture"
            ].append({
                "record_id": record_id,
                "value": agriculture
            })

        placement = record.get(
            "placement_relevance",
            ""
        )

        if placement not in VALID_PLACEMENT_RELEVANCE:

            results[
                "invalid_placement"
            ].append({
                "record_id": record_id,
                "value": placement
            })

        content = record.get(
            "content_type",
            ""
        )

        if content not in VALID_CONTENT_TYPES:

            results[
                "invalid_content"
            ].append({
                "record_id": record_id,
                "value": content
            })

    return results


# ------------------------------------------------------------
# SOURCE CHECK
# ------------------------------------------------------------

def inspect_source(records):

    problems = []

    for record in records:

        record_id = record.get(
            "record_id",
            "UNKNOWN"
        )

        source = record.get(
            "source",
            {}
        )

        if not isinstance(source, dict):

            problems.append(record_id)

            continue

        source_pdf = source.get(
            "source_pdf",
            ""
        )

        source_headline = source.get(
            "source_headline",
            ""
        )

        if (
            is_empty(source_pdf)
            or is_empty(source_headline)
        ):

            problems.append(record_id)

    return problems


# ------------------------------------------------------------
# PROCESSING METADATA CHECK
# ------------------------------------------------------------

def inspect_processing(records):

    problems = []

    required_processing_fields = [
        "curation_version",
        "database_version",
        "duplicate_key",
    ]

    for record in records:

        record_id = record.get(
            "record_id",
            "UNKNOWN"
        )

        processing = record.get(
            "processing",
            {}
        )

        if not isinstance(processing, dict):

            problems.append({
                "record_id": record_id,
                "missing": required_processing_fields
            })

            continue

        missing = []

        for field in required_processing_fields:

            if is_empty(
                processing.get(field)
            ):

                missing.append(field)

        if missing:

            problems.append({
                "record_id": record_id,
                "missing": missing
            })

    return problems


# ------------------------------------------------------------
# STATISTICS
# ------------------------------------------------------------

def count_field(records, field):

    return Counter(
        record.get(
            field,
            "UNKNOWN"
        )
        for record in records
    )


# ------------------------------------------------------------
# BUILD REPORT
# ------------------------------------------------------------

def build_report(data):

    records = data.get(
        "records",
        []
    )

    missing_required, missing_counts = (
        inspect_required_fields(records)
    )

    duplicate_ids, missing_ids = (
        inspect_record_ids(records)
    )

    headline_duplicates = (
        inspect_headline_duplicates(records)
    )

    categories = inspect_categories(
        records
    )

    source_problems = inspect_source(
        records
    )

    processing_problems = inspect_processing(
        records
    )

    issue_groups = (
        len(missing_required)
        + len(duplicate_ids)
        + len(missing_ids)
        + len(headline_duplicates)
        + len(source_problems)
        + len(processing_problems)
        + sum(
            len(v)
            for v in categories.values()
        )
    )

    if issue_groups == 0:

        status = "PASS"

    else:

        status = "REVIEW REQUIRED"

    lines = []

    lines.append("=" * 80)
    lines.append(
        "AGRICULTURE INTELLIGENCE SYSTEM"
    )
    lines.append(
        "MASTER DATABASE QUALITY CONTROL REPORT v2"
    )
    lines.append("=" * 80)

    lines.append("")

    lines.append(
        f"Database: {MASTER_FILE.name}"
    )

    lines.append(
        f"Total records: {len(records)}"
    )

    lines.append(
        f"Database version: "
        f"{data.get('database_version', 'UNKNOWN')}"
    )

    lines.append(
        f"Last updated: "
        f"{data.get('last_updated', 'UNKNOWN')}"
    )

    lines.append("")

    lines.append(
        f"OVERALL QC STATUS: {status}"
    )

    lines.append(
        f"Total issue groups detected: "
        f"{issue_groups}"
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    lines.append("")
    lines.append("-" * 80)
    lines.append("DATABASE SUMMARY")
    lines.append("-" * 80)

    lines.append("")

    lines.append("Newspapers:")

    for name, count in sorted(
        count_field(
            records,
            "newspaper"
        ).items()
    ):

        lines.append(
            f"  {name}: {count}"
        )

    lines.append("")

    lines.append("Dates:")

    for date, count in sorted(
        count_field(
            records,
            "date"
        ).items()
    ):

        lines.append(
            f"  {date}: {count}"
        )

    # --------------------------------------------------------
    # Categories
    # --------------------------------------------------------

    sections = [

        (
            "PRIMARY CATEGORY DISTRIBUTION",
            "primary_category"
        ),

        (
            "INTELLIGENCE TYPE DISTRIBUTION",
            "intelligence_type"
        ),

        (
            "AGRICULTURE CONNECTION DISTRIBUTION",
            "agriculture_connection"
        ),

        (
            "PLACEMENT RELEVANCE DISTRIBUTION",
            "placement_relevance"
        ),

        (
            "CONTENT TYPE DISTRIBUTION",
            "content_type"
        )
    ]

    for title, field in sections:

        lines.append("")
        lines.append("-" * 80)
        lines.append(title)
        lines.append("-" * 80)

        for name, count in sorted(
            count_field(
                records,
                field
            ).items()
        ):

            lines.append(
                f"{name}: {count}"
            )

    # --------------------------------------------------------
    # Missing required
    # --------------------------------------------------------

    lines.append("")
    lines.append("-" * 80)
    lines.append(
        "MISSING REQUIRED FIELDS"
    )
    lines.append("-" * 80)

    if not missing_required:

        lines.append(
            "No missing required fields."
        )

    else:

        for field, count in sorted(
            missing_counts.items()
        ):

            lines.append(
                f"{field}: {count}"
            )

        for record_id, fields in (
            missing_required.items()
        ):

            lines.append("")
            lines.append(
                f"{record_id}:"
            )

            lines.append(
                f"  Missing: "
                f"{', '.join(fields)}"
            )

    # --------------------------------------------------------
    # Optional fields
    # --------------------------------------------------------

    lines.append("")
    lines.append("-" * 80)
    lines.append(
        "OPTIONAL FIELD COVERAGE"
    )
    lines.append("-" * 80)

    for field in OPTIONAL_FIELDS:

        populated = sum(
            not is_empty(
                record.get(field)
            )
            for record in records
        )

        empty = (
            len(records)
            - populated
        )

        percentage = (
            populated / len(records) * 100
            if records
            else 0
        )

        lines.append(
            f"{field}: "
            f"{populated}/{len(records)} "
            f"populated "
            f"({percentage:.1f}%)"
        )

    # --------------------------------------------------------
    # IDs
    # --------------------------------------------------------

    lines.append("")
    lines.append("-" * 80)
    lines.append("RECORD ID CHECK")
    lines.append("-" * 80)

    lines.append(
        f"Duplicate IDs: "
        f"{len(duplicate_ids)}"
    )

    lines.append(
        f"Missing IDs: "
        f"{len(missing_ids)}"
    )

    # --------------------------------------------------------
    # Headlines
    # --------------------------------------------------------

    lines.append("")
    lines.append("-" * 80)
    lines.append("HEADLINE DUPLICATE CHECK")
    lines.append("-" * 80)

    lines.append(
        f"Exact duplicate headline groups: "
        f"{len(headline_duplicates)}"
    )

    # --------------------------------------------------------
    # Category validation
    # --------------------------------------------------------

    lines.append("")
    lines.append("-" * 80)
    lines.append("CATEGORY VALIDATION")
    lines.append("-" * 80)

    for key, values in categories.items():

        lines.append(
            f"{key}: {len(values)}"
        )

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    lines.append("")
    lines.append("-" * 80)
    lines.append("SOURCE / PROVENANCE")
    lines.append("-" * 80)

    lines.append(
        f"Records with source problems: "
        f"{len(source_problems)}"
    )

    # --------------------------------------------------------
    # Processing
    # --------------------------------------------------------

    lines.append("")
    lines.append("-" * 80)
    lines.append("PROCESSING METADATA")
    lines.append("-" * 80)

    lines.append(
        f"Records with processing problems: "
        f"{len(processing_problems)}"
    )

    # --------------------------------------------------------
    # Final assessment
    # --------------------------------------------------------

    lines.append("")
    lines.append("=" * 80)
    lines.append("FINAL ASSESSMENT")
    lines.append("=" * 80)

    if issue_groups == 0:

        lines.append(
            "PASS: Master database structure is clean."
        )

        lines.append(
            "Empty optional fields are not treated as errors."
        )

    else:

        lines.append(
            "REVIEW REQUIRED: "
            "Structural issues remain."
        )

    lines.append("")
    lines.append(
        "The master database was NOT modified."
    )

    return "\n".join(lines)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print()
    print("=" * 80)
    print(
        "AGRICULTURE INTELLIGENCE SYSTEM"
    )
    print(
        "MASTER DATABASE INSPECTOR v2"
    )
    print("=" * 80)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print(
        "Loading master database..."
    )

    data = load_database()

    print(
        f"Records loaded: "
        f"{len(data.get('records', []))}"
    )

    print()
    print(
        "Running quality-control checks..."
    )

    report = build_report(
        data
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(report)

    print()
    print("=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)

    print()
    print(
        "Inspection report:"
    )

    print(REPORT_FILE)

    print()
    print(
        "The master database was not modified."
    )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()