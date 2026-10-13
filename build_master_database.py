import json
import hashlib
from pathlib import Path
from datetime import datetime


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# MASTER DATABASE BUILDER v2
#
# Input:
#   CURATED_INTELLIGENCE_v23.json
#
# This version explicitly handles the real V2.3 structure:
#
# record
# ├── metadata
# ├── final_analysis
# ├── source_record
# └── curation
#
# IMPORTANT:
#   - Existing master records are preserved
#   - New records are appended
#   - Duplicate records are skipped
#   - Source/provenance is preserved
#   - Analytical information is retained
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "curated_intelligence_v23"
    / "CURATED_INTELLIGENCE_v23.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "master_database_v1"
)

MASTER_FILE = (
    OUTPUT_DIR
    / "MASTER_INTELLIGENCE_DATABASE_v1.json"
)

REPORT_FILE = (
    OUTPUT_DIR
    / "MASTER_DATABASE_REPORT_v1.txt"
)


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def clean_text(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def clean_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def normalize_text(text):
    text = clean_text(text).lower()

    replacements = {
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def make_hash(text, length=16):
    normalized = normalize_text(text)

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:length]


def load_json(path):

    if not path.exists():
        raise FileNotFoundError(
            f"\nInput file not found:\n{path}\n\n"
            "Run the V2.3 curation step first."
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ------------------------------------------------------------
# NEWSPAPER NORMALIZATION
# ------------------------------------------------------------

def normalize_newspaper(value):

    newspaper = clean_text(value)

    lower = newspaper.lower()

    if (
        "bs mumbai" in lower
        or "business standard" in lower
    ):
        return "Business Standard"

    if (
        "et mumbai" in lower
        or "economic times" in lower
    ):
        return "Economic Times"

    return newspaper


# ------------------------------------------------------------
# RECORD ID
# ------------------------------------------------------------

def generate_record_id(
    original_record_id,
    newspaper,
    date,
    page,
    story_id
):
    """
    Prefer the stable V2.3 record ID.

    This means re-running the builder will not create
    a different ID for the same story.
    """

    if original_record_id:
        return clean_text(original_record_id)

    fingerprint = make_hash(
        f"{newspaper}|{date}|{page}|{story_id}",
        length=12
    ).upper()

    newspaper_code = "UNK"

    if newspaper == "Business Standard":
        newspaper_code = "BS"

    elif newspaper == "Economic Times":
        newspaper_code = "ET"

    date_clean = date.replace("-", "")

    return (
        f"{newspaper_code}_"
        f"{date_clean}_"
        f"P{page}_"
        f"{fingerprint}"
    )


# ------------------------------------------------------------
# DUPLICATE KEY
# ------------------------------------------------------------

def generate_duplicate_key(
    headline
):
    """
    Headline-based fingerprint.

    This is used for identifying possible cross-newspaper
    duplicates, but stories are NOT automatically deleted.
    """

    return make_hash(
        normalize_text(headline),
        length=16
    )


# ------------------------------------------------------------
# BUILD ONE MASTER RECORD
# ------------------------------------------------------------

def build_master_record(record, index):

    # --------------------------------------------------------
    # Top-level metadata
    # --------------------------------------------------------

    original_record_id = clean_text(
        record.get("record_id", "")
    )

    newspaper = normalize_newspaper(
        record.get("newspaper", "")
    )

    date = clean_text(
        record.get("date", "")
    )

    page = record.get(
        "page",
        ""
    )

    story_id = clean_text(
        record.get("story_id", "")
    )

    source_headline = clean_text(
        record.get(
            "source_headline",
            ""
        )
    )

    # --------------------------------------------------------
    # Nested V2.3 structures
    # --------------------------------------------------------

    final_analysis = record.get(
        "final_analysis",
        {}
    )

    if not isinstance(final_analysis, dict):
        final_analysis = {}

    curation = record.get(
        "curation",
        {}
    )

    if not isinstance(curation, dict):
        curation = {}

    source_record = record.get(
        "source_record",
        {}
    )

    if not isinstance(source_record, dict):
        source_record = {}

    # --------------------------------------------------------
    # Final analysis fields
    # --------------------------------------------------------

    keep = final_analysis.get(
        "keep",
        True
    )

    content_type = clean_text(
        final_analysis.get(
            "content_type",
            ""
        )
    )

    headline = clean_text(
        final_analysis.get(
            "headline",
            ""
        )
    )

    if not headline:
        headline = source_headline

    summary = clean_text(
        final_analysis.get(
            "summary",
            ""
        )
    )

    article_text = clean_text(
        final_analysis.get(
            "article_text",
            ""
        )
    )

    source_quality = clean_text(
        final_analysis.get(
            "source_quality",
            ""
        )
    )

    needs_review = bool(
        final_analysis.get(
            "needs_review",
            False
        )
    )

    topics = clean_list(
        final_analysis.get(
            "topics",
            []
        )
    )

    agriculture_relevance = clean_text(
        final_analysis.get(
            "agriculture_relevance",
            ""
        )
    )

    agriculture_relevance_reason = clean_text(
        final_analysis.get(
            "agriculture_relevance_reason",
            ""
        )
    )

    reported_facts = clean_list(
        final_analysis.get(
            "reported_facts",
            []
        )
    )

    interpretations = clean_list(
        final_analysis.get(
            "interpretations",
            []
        )
    )

    key_facts = clean_list(
        final_analysis.get(
            "key_facts",
            []
        )
    )

    key_numbers = clean_list(
        final_analysis.get(
            "key_numbers",
            []
        )
    )

    agriculture_impact = clean_text(
        final_analysis.get(
            "agriculture_impact",
            ""
        )
    )

    why_it_matters = clean_text(
        final_analysis.get(
            "why_it_matters",
            ""
        )
    )

    connections = clean_list(
        final_analysis.get(
            "connections",
            []
        )
    )

    government_schemes = clean_list(
        final_analysis.get(
            "government_schemes",
            []
        )
    )

    placement_questions = clean_list(
        final_analysis.get(
            "placement_questions",
            []
        )
    )

    # --------------------------------------------------------
    # Curation fields
    # --------------------------------------------------------

    primary_category = clean_text(
        curation.get(
            "primary_category",
            ""
        )
    )

    secondary_categories = clean_list(
        curation.get(
            "secondary_categories",
            []
        )
    )

    agriculture_connection = clean_text(
        curation.get(
            "agriculture_connection",
            ""
        )
    )

    intelligence_type = clean_text(
        curation.get(
            "intelligence_type",
            ""
        )
    )

    placement_relevance = clean_text(
        curation.get(
            "placement_relevance",
            ""
        )
    )

    curation_status = clean_text(
        curation.get(
            "status",
            ""
        )
    )

    curation_reason = clean_text(
        curation.get(
            "reason",
            ""
        )
    )

    duplicate_of = clean_text(
        curation.get(
            "duplicate_of",
            ""
        )
    )

    primary_record = clean_text(
        curation.get(
            "primary_record",
            ""
        )
    )

    # --------------------------------------------------------
    # Source information
    # --------------------------------------------------------

    source_pdf = ""

    if newspaper == "Business Standard":
        source_pdf = (
            "Newspapers/Raw/"
            "BS Mumbai 16-09-2026.pdf"
        )

    elif newspaper == "Economic Times":
        source_pdf = (
            "Newspapers/Raw/"
            "ET Mumbai 16-09-2026.pdf"
        )

    # Preserve source record summary
    source_record_summary = {
        "story_id": source_record.get(
            "story_id",
            ""
        ),

        "primary_headline": source_record.get(
            "primary_headline",
            ""
        ),

        "merged_headline": source_record.get(
            "merged_headline",
            ""
        ),

        "candidate_ids": source_record.get(
            "candidate_ids",
            []
        ),

        "supporting_candidate_ids": source_record.get(
            "supporting_candidate_ids",
            []
        ),

        "duplicate_candidate_ids": source_record.get(
            "duplicate_candidate_ids",
            []
        ),

        "reason": source_record.get(
            "reason",
            ""
        )
    }

    # --------------------------------------------------------
    # Stable IDs
    # --------------------------------------------------------

    record_id = generate_record_id(
        original_record_id,
        newspaper,
        date,
        page,
        story_id
    )

    duplicate_key = generate_duplicate_key(
        headline
    )

    # --------------------------------------------------------
    # MASTER RECORD
    # --------------------------------------------------------

    master_record = {

        # ----------------------------------------------------
        # Identity
        # ----------------------------------------------------

        "record_id": record_id,

        "newspaper": newspaper,

        "date": date,

        "page": page,

        "story_id": story_id,

        "headline": headline,

        # ----------------------------------------------------
        # Classification
        # ----------------------------------------------------

        "content_type": content_type,

        "source_quality": source_quality,

        "primary_category": primary_category,

        "secondary_categories":
            secondary_categories,

        "intelligence_type":
            intelligence_type,

        "agriculture_connection":
            agriculture_connection,

        "agriculture_relevance":
            agriculture_relevance,

        "agriculture_relevance_reason":
            agriculture_relevance_reason,

        "placement_relevance":
            placement_relevance,

        # ----------------------------------------------------
        # Intelligence
        # ----------------------------------------------------

        "summary": summary,

        "article_text": article_text,

        "topics": topics,

        "reported_facts": reported_facts,

        "interpretations": interpretations,

        "key_facts": key_facts,

        "key_numbers": key_numbers,

        "agriculture_impact":
            agriculture_impact,

        "why_it_matters":
            why_it_matters,

        "connections":
            connections,

        # ----------------------------------------------------
        # Government schemes
        # ----------------------------------------------------

        "government_schemes":
            government_schemes,

        # ----------------------------------------------------
        # Placement preparation
        # ----------------------------------------------------

        "placement_questions":
            placement_questions,

        # ----------------------------------------------------
        # Source / provenance
        # ----------------------------------------------------

        "source": {

            "source_pdf":
                source_pdf,

            "source_headline":
                source_headline,

            "source_record":
                source_record_summary
        },

        # ----------------------------------------------------
        # Curation metadata
        # ----------------------------------------------------

        "curation": {

            "status":
                curation_status,

            "reason":
                curation_reason,

            "duplicate_of":
                duplicate_of,

            "primary_record":
                primary_record
        },

        # ----------------------------------------------------
        # Processing metadata
        # ----------------------------------------------------

        "processing": {

            "curation_version":
                "v2.3",

            "database_version":
                "v1",

            "source_record_index":
                index,

            "keep":
                keep,

            "needs_review":
                needs_review,

            "duplicate_key":
                duplicate_key
        }
    }

    return master_record


# ------------------------------------------------------------
# EXISTING DATABASE
# ------------------------------------------------------------

def load_existing_master():

    if not MASTER_FILE.exists():

        return {
            "database_name":
                "Agriculture Intelligence Master Database",

            "database_version":
                "v1",

            "created_at":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "last_updated":
                datetime.now().isoformat(
                    timespec="seconds"
                ),

            "record_count":
                0,

            "newspaper_count":
                0,

            "date_count":
                0,

            "records":
                []
        }

    with open(
        MASTER_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    if "records" not in data:
        data["records"] = []

    return data


# ------------------------------------------------------------
# APPEND LOGIC
# ------------------------------------------------------------

def append_new_records(
    master_data,
    new_records
):

    existing_ids = {
        record.get("record_id")
        for record in master_data["records"]
    }

    added = []
    skipped = []

    for record in new_records:

        record_id = record.get(
            "record_id"
        )

        if record_id in existing_ids:

            skipped.append({
                "record_id":
                    record_id,

                "reason":
                    "record_id_already_exists",

                "headline":
                    record.get(
                        "headline",
                        ""
                    )
            })

            continue

        master_data["records"].append(
            record
        )

        existing_ids.add(
            record_id
        )

        added.append(
            record
        )

    return added, skipped


# ------------------------------------------------------------
# CROSS-NEWSPAPER DUPLICATES
# ------------------------------------------------------------

def detect_cross_newspaper_duplicates(
    records
):

    groups = {}

    for record in records:

        duplicate_key = (
            record
            .get("processing", {})
            .get("duplicate_key", "")
        )

        if not duplicate_key:
            continue

        groups.setdefault(
            duplicate_key,
            []
        ).append(record)

    duplicate_groups = []

    for duplicate_key, group in groups.items():

        newspapers = {
            record.get(
                "newspaper",
                ""
            )
            for record in group
        }

        if (
            len(group) > 1
            and len(newspapers) > 1
        ):

            duplicate_groups.append({

                "duplicate_key":
                    duplicate_key,

                "stories": [

                    {
                        "record_id":
                            record.get(
                                "record_id"
                            ),

                        "newspaper":
                            record.get(
                                "newspaper"
                            ),

                        "date":
                            record.get(
                                "date"
                            ),

                        "page":
                            record.get(
                                "page"
                            ),

                        "headline":
                            record.get(
                                "headline"
                            )
                    }

                    for record in group
                ]
            })

    return duplicate_groups


# ------------------------------------------------------------
# STATISTICS
# ------------------------------------------------------------

def calculate_statistics(records):

    statistics = {

        "primary_categories": {},

        "intelligence_types": {},

        "agriculture_connections": {},

        "placement_relevance": {},

        "content_types": {},

        "newspapers": {},

        "dates": {}
    }

    fields = {
        "primary_categories":
            "primary_category",

        "intelligence_types":
            "intelligence_type",

        "agriculture_connections":
            "agriculture_connection",

        "placement_relevance":
            "placement_relevance",

        "content_types":
            "content_type",

        "newspapers":
            "newspaper",

        "dates":
            "date"
    }

    for record in records:

        for stat_name, field in fields.items():

            value = record.get(
                field,
                "UNKNOWN"
            )

            if not value:
                value = "UNKNOWN"

            statistics[
                stat_name
            ][value] = (
                statistics[
                    stat_name
                ].get(
                    value,
                    0
                )
                + 1
            )

    return statistics


# ------------------------------------------------------------
# REPORT
# ------------------------------------------------------------

def write_report(
    master_data,
    added,
    skipped,
    cross_duplicates
):

    records = master_data["records"]

    stats = calculate_statistics(
        records
    )

    lines = []

    lines.append("=" * 70)
    lines.append(
        "AGRICULTURE INTELLIGENCE SYSTEM"
    )
    lines.append(
        "MASTER DATABASE REPORT v1"
    )
    lines.append("=" * 70)

    lines.append("")

    lines.append(
        f"Total records: {len(records)}"
    )

    lines.append(
        f"Records added this run: "
        f"{len(added)}"
    )

    lines.append(
        f"Records skipped this run: "
        f"{len(skipped)}"
    )

    lines.append(
        f"Cross-newspaper duplicate groups: "
        f"{len(cross_duplicates)}"
    )

    sections = [
        (
            "NEWSPAPERS",
            "newspapers"
        ),
        (
            "DATES",
            "dates"
        ),
        (
            "PRIMARY CATEGORIES",
            "primary_categories"
        ),
        (
            "INTELLIGENCE TYPES",
            "intelligence_types"
        ),
        (
            "AGRICULTURE CONNECTION",
            "agriculture_connections"
        ),
        (
            "PLACEMENT RELEVANCE",
            "placement_relevance"
        ),
        (
            "CONTENT TYPES",
            "content_types"
        )
    ]

    for title, key in sections:

        lines.append("")
        lines.append("-" * 70)
        lines.append(title)
        lines.append("-" * 70)

        for name, count in sorted(
            stats[key].items()
        ):

            lines.append(
                f"{name}: {count}"
            )

    if added:

        lines.append("")
        lines.append("-" * 70)
        lines.append("RECORDS ADDED THIS RUN")
        lines.append("-" * 70)

        for record in added:

            lines.append(
                f"{record['record_id']} | "
                f"{record['newspaper']} | "
                f"{record['date']} | "
                f"P{record['page']} | "
                f"{record['headline']}"
            )

    if skipped:

        lines.append("")
        lines.append("-" * 70)
        lines.append("RECORDS SKIPPED")
        lines.append("-" * 70)

        for item in skipped:

            lines.append(
                f"{item['record_id']} | "
                f"{item['reason']} | "
                f"{item['headline']}"
            )

    if cross_duplicates:

        lines.append("")
        lines.append("-" * 70)
        lines.append(
            "CROSS-NEWSPAPER DUPLICATES"
        )
        lines.append("-" * 70)

        for group in cross_duplicates:

            lines.append(
                f"Duplicate key: "
                f"{group['duplicate_key']}"
            )

            for story in group["stories"]:

                lines.append(
                    f"  {story['record_id']} | "
                    f"{story['newspaper']} | "
                    f"{story['date']} | "
                    f"P{story['page']} | "
                    f"{story['headline']}"
                )

    lines.append("")
    lines.append("=" * 70)
    lines.append(
        "END OF MASTER DATABASE REPORT"
    )
    lines.append("=" * 70)

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(lines)
        )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print()
    print("=" * 70)
    print(
        "AGRICULTURE INTELLIGENCE SYSTEM"
    )
    print(
        "MASTER DATABASE BUILDER v2"
    )
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load V2.3
    # --------------------------------------------------------

    print()
    print(
        "Loading curated intelligence V2.3..."
    )

    data = load_json(
        INPUT_FILE
    )

    if not isinstance(data, list):

        raise ValueError(
            "Expected V2.3 curated file "
            "to contain a list of records."
        )

    print(
        f"Curated records found: "
        f"{len(data)}"
    )

    # --------------------------------------------------------
    # Build records
    # --------------------------------------------------------

    print()
    print(
        "Building master records..."
    )

    new_records = []

    for index, record in enumerate(
        data,
        start=1
    ):

        master_record = build_master_record(
            record,
            index
        )

        new_records.append(
            master_record
        )

    print(
        f"Master records prepared: "
        f"{len(new_records)}"
    )

    # --------------------------------------------------------
    # Existing database
    # --------------------------------------------------------

    print()
    print(
        "Loading existing master database..."
    )

    master_data = load_existing_master()

    existing_count = len(
        master_data["records"]
    )

    print(
        f"Existing records: "
        f"{existing_count}"
    )

    # --------------------------------------------------------
    # Append
    # --------------------------------------------------------

    added, skipped = append_new_records(
        master_data,
        new_records
    )

    print(
        f"Records added: "
        f"{len(added)}"
    )

    print(
        f"Records skipped: "
        f"{len(skipped)}"
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    master_data["database_name"] = (
        "Agriculture Intelligence Master Database"
    )

    master_data["database_version"] = "v1"

    master_data["last_updated"] = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    master_data["record_count"] = (
        len(master_data["records"])
    )

    master_data["newspaper_count"] = len({
        record.get("newspaper")
        for record in master_data["records"]
    })

    master_data["date_count"] = len({
        record.get("date")
        for record in master_data["records"]
    })

    # --------------------------------------------------------
    # Duplicate report
    # --------------------------------------------------------

    cross_duplicates = (
        detect_cross_newspaper_duplicates(
            master_data["records"]
        )
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    with open(
        MASTER_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            master_data,
            f,
            indent=2,
            ensure_ascii=False
        )

    write_report(
        master_data,
        added,
        skipped,
        cross_duplicates
    )

    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "MASTER DATABASE BUILD COMPLETE"
    )
    print("=" * 70)

    print(
        f"Total records: "
        f"{master_data['record_count']}"
    )

    print(
        f"Newspapers: "
        f"{master_data['newspaper_count']}"
    )

    print(
        f"Dates: "
        f"{master_data['date_count']}"
    )

    print()
    print(
        "Master database:"
    )

    print(MASTER_FILE)

    print()
    print(
        "Report:"
    )

    print(REPORT_FILE)

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()