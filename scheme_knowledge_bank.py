import json
import re
from pathlib import Path
from datetime import datetime


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# GOVERNMENT INTELLIGENCE BANK v2.1
#
# Purpose:
#   Maintain a cumulative database of government schemes,
#   programmes, policies, regulations and related initiatives
#   identified from newspaper-derived intelligence records.
#
# v2.1 improvements:
#   - Repairs common UTF-8/Windows mojibake
#   - Preserves newspaper provenance
#   - Prevents duplicate newspaper events
#   - Maintains cumulative initiative profiles
#   - Distinguishes schemes from policies/regulations
#   - Does not invent missing information
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parent


# ------------------------------------------------------------
# INPUT
# ------------------------------------------------------------

MASTER_FILE = (
    PROJECT_ROOT
    / "data"
    / "master_database_v1"
    / "MASTER_INTELLIGENCE_DATABASE_v1.json"
)


# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "government_intelligence_bank_v2"
)

BANK_FILE = (
    OUTPUT_DIR
    / "GOVERNMENT_INTELLIGENCE_BANK_v2.json"
)

REVIEW_FILE = (
    OUTPUT_DIR
    / "GOVERNMENT_INTELLIGENCE_REVIEW_QUEUE_v2.json"
)

REPORT_FILE = (
    OUTPUT_DIR
    / "GOVERNMENT_INTELLIGENCE_BANK_REPORT_v2.txt"
)


# ------------------------------------------------------------
# VALID INITIATIVE TYPES
# ------------------------------------------------------------

VALID_INITIATIVE_TYPES = {
    "GOVERNMENT_SCHEME",
    "GOVERNMENT_PROGRAMME",
    "POLICY_REGULATION",
    "REGULATORY_MECHANISM",
    "INTERNATIONAL_POLICY",
}


# ------------------------------------------------------------
# VALID EVENT TYPES
# ------------------------------------------------------------

VALID_EVENT_TYPES = {
    "new_scheme",
    "update",
    "funding",
    "beneficiary_update",
    "performance",
    "eligibility",
    "state_implementation",
    "implementation",
    "announcement",
    "mention_only",
    "not_applicable",
}


# ------------------------------------------------------------
# TEXT / ENCODING HELPERS
# ------------------------------------------------------------

def repair_mojibake(text):
    """
    Repair common UTF-8 text that has accidentally been decoded
    using a Windows/Latin-1 style encoding.

    Example:
        â‚¹  -> ₹
        â€“  -> –
        â€”  -> —
        â€œ  -> “
        â€  -> ”
        â€™  -> ’
    """

    if not isinstance(text, str):
        return text

    replacements = {
        "â‚¹": "₹",
        "â€“": "–",
        "â€”": "—",
        "â€œ": "“",
        "â€": "”",
        "â€˜": "‘",
        "â€™": "’",
        "â€¦": "…",
        "Â₹": "₹",
        "Â°": "°",
        "Â": "",
    }

    for bad, good in replacements.items():

        text = text.replace(
            bad,
            good
        )

    return text


def clean_text(value):

    if value is None:
        return ""

    if isinstance(value, str):

        value = repair_mojibake(
            value
        )

        return " ".join(
            value.strip().split()
        )

    return str(value).strip()


def clean_list(value):

    if value is None:
        return []

    if isinstance(value, list):

        output = []

        for item in value:

            if isinstance(item, str):

                item = clean_text(
                    item
                )

                if item:
                    output.append(
                        item
                    )

            elif item is not None:

                output.append(item)

        return output

    if isinstance(value, str):

        value = clean_text(
            value
        )

        if value:
            return [value]

        return []

    return [value]


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


def normalize_name(name):

    name = clean_text(
        name
    ).lower()

    name = re.sub(
        r"[^a-z0-9\s]",
        " ",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip()


def now_iso():

    return datetime.now().isoformat(
        timespec="seconds"
    )


# ------------------------------------------------------------
# JSON HELPERS
# ------------------------------------------------------------

def load_json(
    path,
    default
):

    if not path.exists():
        return default

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(
    path,
    data
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


# ------------------------------------------------------------
# MASTER DATABASE
# ------------------------------------------------------------

def load_master_database():

    if not MASTER_FILE.exists():

        raise FileNotFoundError(
            f"\nMaster database not found:\n"
            f"{MASTER_FILE}\n\n"
            f"Run build_master_database.py first."
        )

    data = load_json(
        MASTER_FILE,
        {}
    )

    records = data.get(
        "records",
        []
    )

    if not isinstance(
        records,
        list
    ):

        raise ValueError(
            "Master database 'records' must be a list."
        )

    return data, records


# ------------------------------------------------------------
# EXISTING BANK
# ------------------------------------------------------------

def load_existing_bank():

    if not BANK_FILE.exists():

        return {
            "database_version": "v2.1",
            "created_at": now_iso(),
            "last_updated": now_iso(),
            "initiative_count": 0,
            "event_count": 0,
            "initiatives": []
        }

    data = load_json(
        BANK_FILE,
        {}
    )

    if "initiatives" not in data:

        data["initiatives"] = []

    return data


# ------------------------------------------------------------
# REVIEW QUEUE
# ------------------------------------------------------------

def load_review_queue():

    if not REVIEW_FILE.exists():

        return {
            "queue_version": "v2.1",
            "created_at": now_iso(),
            "last_updated": now_iso(),
            "items": []
        }

    data = load_json(
        REVIEW_FILE,
        {}
    )

    if "items" not in data:

        data["items"] = []

    return data


# ------------------------------------------------------------
# EXTRACT INITIATIVE NAME
# ------------------------------------------------------------

def extract_name(raw):

    if isinstance(raw, str):

        return clean_text(raw)

    if not isinstance(
        raw,
        dict
    ):

        return ""

    possible_fields = [
        "scheme_name",
        "name",
        "scheme",
        "title",
        "initiative_name",
    ]

    for field in possible_fields:

        value = raw.get(
            field
        )

        if value:

            value = clean_text(
                value
            )

            if value:
                return value

    return ""


# ------------------------------------------------------------
# CLASSIFY INITIATIVE TYPE
# ------------------------------------------------------------

def classify_initiative_type(
    name,
    raw
):

    details = ""

    if isinstance(
        raw,
        dict
    ):

        details = (
            clean_text(
                raw.get(
                    "details",
                    ""
                )
            )
            + " "
            + clean_text(
                raw.get(
                    "description",
                    ""
                )
            )
        )

    text = (
        clean_text(name)
        + " "
        + details
    ).lower()

    normalized_name = normalize_name(
        name
    )

    # --------------------------------------------------------
    # Explicit classifications
    # --------------------------------------------------------

    if normalized_name in {
        "unified payments interface upi",
        "upi"
    }:

        return "REGULATORY_MECHANISM"

    if normalized_name in {
        "goods and services tax gst",
        "goods and services tax",
        "gst"
    }:

        return "POLICY_REGULATION"

    if (
        "cbam" in normalized_name
        or "carbon border adjustment" in text
    ):

        return "INTERNATIONAL_POLICY"

    if (
        "price support programme"
        in normalized_name
        or "price support program"
        in normalized_name
    ):

        return "GOVERNMENT_PROGRAMME"

    # --------------------------------------------------------
    # Conservative generic classification
    # --------------------------------------------------------

    if (
        "programme" in normalized_name
        or "program" in normalized_name
    ):

        return "GOVERNMENT_PROGRAMME"

    if (
        "scheme" in normalized_name
        or "yojana" in normalized_name
    ):

        return "GOVERNMENT_SCHEME"

    if (
        "regulation" in text
        or "regulatory" in text
        or "tax framework" in text
    ):

        return "POLICY_REGULATION"

    return ""


# ------------------------------------------------------------
# EXTRACT DETAILS
# ------------------------------------------------------------

def extract_details(raw):

    if isinstance(
        raw,
        str
    ):

        return {
            "name":
                clean_text(raw),

            "full_name": "",
            "category": "",
            "ministry": "",
            "target_beneficiaries": [],
            "purpose": "",
            "benefits": "",
            "eligibility": "",
            "financial_outlay": "",
            "latest_update": "",
            "agri_relevance": "",
            "placement_angle": "",
            "official_source": "",
            "event_type": "mention_only",
            "details": ""
        }

    if not isinstance(
        raw,
        dict
    ):

        return {
            "name": "",
            "full_name": "",
            "category": "",
            "ministry": "",
            "target_beneficiaries": [],
            "purpose": "",
            "benefits": "",
            "eligibility": "",
            "financial_outlay": "",
            "latest_update": "",
            "agri_relevance": "",
            "placement_angle": "",
            "official_source": "",
            "event_type": "mention_only",
            "details": ""
        }

    event_type = clean_text(
        raw.get(
            "event_type",
            "mention_only"
        )
    ).lower()

    if event_type not in VALID_EVENT_TYPES:

        event_type = "mention_only"

    return {
        "name":
            extract_name(raw),

        "full_name":
            clean_text(
                raw.get(
                    "full_name",
                    ""
                )
            ),

        "category":
            clean_text(
                raw.get(
                    "category",
                    ""
                )
            ),

        "ministry":
            clean_text(
                raw.get(
                    "ministry",
                    ""
                )
            ),

        "target_beneficiaries":
            clean_list(
                raw.get(
                    "target_beneficiaries",
                    []
                )
            ),

        "purpose":
            clean_text(
                raw.get(
                    "purpose",
                    ""
                )
            ),

        "benefits":
            clean_text(
                raw.get(
                    "benefits",
                    ""
                )
            ),

        "eligibility":
            clean_text(
                raw.get(
                    "eligibility",
                    ""
                )
            ),

        "financial_outlay":
            clean_text(
                raw.get(
                    "financial_outlay",
                    ""
                )
            ),

        "latest_update":
            clean_text(
                raw.get(
                    "latest_update",
                    ""
                )
            ),

        "agri_relevance":
            clean_text(
                raw.get(
                    "agri_relevance",
                    ""
                )
            ),

        "placement_angle":
            clean_text(
                raw.get(
                    "placement_angle",
                    ""
                )
            ),

        "official_source":
            clean_text(
                raw.get(
                    "official_source",
                    ""
                )
            ),

        "event_type":
            event_type,

        "details":
            clean_text(
                raw.get(
                    "details",
                    raw.get(
                        "description",
                        ""
                    )
                )
            )
    }


# ------------------------------------------------------------
# BUILD EVENT
# ------------------------------------------------------------

def build_event(
    record,
    details
):

    source = record.get(
        "source",
        {}
    )

    if not isinstance(
        source,
        dict
    ):

        source = {}

    return {

        "record_id":
            clean_text(
                record.get(
                    "record_id",
                    ""
                )
            ),

        "newspaper":
            clean_text(
                record.get(
                    "newspaper",
                    ""
                )
            ),

        "date":
            clean_text(
                record.get(
                    "date",
                    ""
                )
            ),

        "page":
            record.get(
                "page",
                ""
            ),

        "headline":
            clean_text(
                record.get(
                    "headline",
                    ""
                )
            ),

        "event_type":
            details[
                "event_type"
            ],

        "details":
            details[
                "details"
            ],

        "source_pdf":
            clean_text(
                source.get(
                    "source_pdf",
                    ""
                )
            )
    }


# ------------------------------------------------------------
# REVIEW QUEUE
# ------------------------------------------------------------

def make_review_item(
    record,
    raw,
    name,
    reason
):

    return {

        "review_id":
            "REVIEW_"
            + clean_text(
                record.get(
                    "record_id",
                    "UNKNOWN"
                )
            ),

        "record_id":
            clean_text(
                record.get(
                    "record_id",
                    ""
                )
            ),

        "newspaper":
            clean_text(
                record.get(
                    "newspaper",
                    ""
                )
            ),

        "date":
            clean_text(
                record.get(
                    "date",
                    ""
                )
            ),

        "page":
            record.get(
                "page",
                ""
            ),

        "headline":
            clean_text(
                record.get(
                    "headline",
                    ""
                )
            ),

        "possible_name":
            clean_text(name),

        "raw_data":
            raw,

        "reason":
            reason,

        "created_at":
            now_iso()
    }


def add_review(
    items,
    review
):

    for existing in items:

        if (
            existing.get(
                "record_id"
            )
            == review.get(
                "record_id"
            )
        ):

            return False

    items.append(
        review
    )

    return True


# ------------------------------------------------------------
# CREATE PROFILE
# ------------------------------------------------------------

def create_profile(
    details,
    initiative_type,
    event
):

    latest = (
        details[
            "latest_update"
        ]
        or details[
            "details"
        ]
        or event[
            "headline"
        ]
    )

    normalized = normalize_name(
        details["name"]
    )

    initiative_id = (
        "GI_"
        + normalized.replace(
            " ",
            "_"
        )[:80]
    )

    return {

        "initiative_id":
            initiative_id,

        "initiative_name":
            details[
                "name"
            ],

        "initiative_type":
            initiative_type,

        "full_name":
            details[
                "full_name"
            ],

        "category":
            details[
                "category"
            ],

        "ministry":
            details[
                "ministry"
            ],

        "target_beneficiaries":
            details[
                "target_beneficiaries"
            ],

        "purpose":
            details[
                "purpose"
            ],

        "benefits":
            details[
                "benefits"
            ],

        "eligibility":
            details[
                "eligibility"
            ],

        "financial_outlay":
            details[
                "financial_outlay"
            ],

        "latest_update":
            latest,

        "newspaper_mentions": [
            event
        ],

        "official_source":
            details[
                "official_source"
            ],

        "agri_relevance":
            details[
                "agri_relevance"
            ],

        "placement_angle":
            details[
                "placement_angle"
            ],

        "last_updated":
            event.get(
                "date",
                ""
            )
    }


# ------------------------------------------------------------
# UPDATE PROFILE
# ------------------------------------------------------------

def update_profile(
    profile,
    details,
    event
):

    changed = False

    # --------------------------------------------------------
    # Fill missing descriptive information only
    # --------------------------------------------------------

    fields = [
        "full_name",
        "category",
        "ministry",
        "purpose",
        "benefits",
        "eligibility",
        "financial_outlay",
        "agri_relevance",
        "placement_angle",
        "official_source",
    ]

    for field in fields:

        incoming = details.get(
            field,
            ""
        )

        if (
            is_empty(
                profile.get(
                    field
                )
            )
            and not is_empty(
                incoming
            )
        ):

            profile[
                field
            ] = incoming

            changed = True

    # --------------------------------------------------------
    # Beneficiaries
    # --------------------------------------------------------

    existing = set(
        clean_list(
            profile.get(
                "target_beneficiaries",
                []
            )
        )
    )

    incoming = clean_list(
        details.get(
            "target_beneficiaries",
            []
        )
    )

    old_count = len(existing)

    existing.update(
        incoming
    )

    if len(existing) != old_count:

        profile[
            "target_beneficiaries"
        ] = sorted(
            existing
        )

        changed = True

    # --------------------------------------------------------
    # Event duplication protection
    # --------------------------------------------------------

    mentions = profile.setdefault(
        "newspaper_mentions",
        []
    )

    record_id = event.get(
        "record_id",
        ""
    )

    duplicate = any(
        item.get(
            "record_id",
            ""
        ) == record_id
        for item in mentions
    )

    if not duplicate:

        mentions.append(
            event
        )

        changed = True

    # --------------------------------------------------------
    # Latest update
    # --------------------------------------------------------

    event_date = event.get(
        "date",
        ""
    )

    current_date = profile.get(
        "last_updated",
        ""
    )

    if (
        event_date
        and (
            not current_date
            or event_date >= current_date
        )
    ):

        latest = (
            details.get(
                "latest_update"
            )
            or details.get(
                "details"
            )
            or event.get(
                "headline"
            )
        )

        if latest:

            latest = clean_text(
                latest
            )

            if (
                profile.get(
                    "latest_update"
                )
                != latest
            ):

                profile[
                    "latest_update"
                ] = latest

                changed = True

        if (
            profile.get(
                "last_updated"
            )
            != event_date
        ):

            profile[
                "last_updated"
            ] = event_date

            changed = True

    return changed


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
        "GOVERNMENT INTELLIGENCE BANK v2.1"
    )
    print("=" * 80)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print(
        "Loading Master Intelligence Database..."
    )

    master_data, records = (
        load_master_database()
    )

    print(
        f"Master records loaded: "
        f"{len(records)}"
    )

    print()
    print(
        "Loading existing Government Intelligence Bank..."
    )

    bank = load_existing_bank()

    initiatives = bank.get(
        "initiatives",
        []
    )

    print(
        f"Existing initiative profiles: "
        f"{len(initiatives)}"
    )

    review_data = load_review_queue()

    review_items = review_data.get(
        "items",
        []
    )

    # --------------------------------------------------------
    # Build existing index
    # --------------------------------------------------------

    index = {}

    for position, profile in enumerate(
        initiatives
    ):

        name = normalize_name(
            profile.get(
                "initiative_name",
                ""
            )
        )

        if name:

            index[name] = position

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    new_profiles = 0
    updated_profiles = 0
    new_events = 0
    duplicate_events = 0
    review_added = 0

    event_distribution = {}
    type_distribution = {}

    # --------------------------------------------------------
    # Process records
    # --------------------------------------------------------

    print()
    print(
        "Scanning government-related records..."
    )

    for record in records:

        raw_schemes = record.get(
            "government_schemes",
            []
        )

        if not raw_schemes:
            continue

        if not isinstance(
            raw_schemes,
            list
        ):

            raw_schemes = [
                raw_schemes
            ]

        for raw in raw_schemes:

            details = extract_details(
                raw
            )

            name = details[
                "name"
            ]

            # ------------------------------------------------
            # Missing name
            # ------------------------------------------------

            if not name:

                review = make_review_item(
                    record,
                    raw,
                    "",
                    "Government-related information "
                    "was present but no identifiable "
                    "initiative name was available."
                )

                if add_review(
                    review_items,
                    review
                ):

                    review_added += 1

                continue

            # ------------------------------------------------
            # Classification
            # ------------------------------------------------

            initiative_type = (
                classify_initiative_type(
                    name,
                    raw
                )
            )

            if not initiative_type:

                review = make_review_item(
                    record,
                    raw,
                    name,
                    "Initiative could not be "
                    "classified confidently."
                )

                if add_review(
                    review_items,
                    review
                ):

                    review_added += 1

                continue

            # ------------------------------------------------
            # Event
            # ------------------------------------------------

            event = build_event(
                record,
                details
            )

            event_distribution[
                details["event_type"]
            ] = (
                event_distribution.get(
                    details["event_type"],
                    0
                )
                + 1
            )

            type_distribution[
                initiative_type
            ] = (
                type_distribution.get(
                    initiative_type,
                    0
                )
                + 1
            )

            normalized = normalize_name(
                name
            )

            # ------------------------------------------------
            # Existing profile
            # ------------------------------------------------

            if normalized in index:

                position = index[
                    normalized
                ]

                profile = initiatives[
                    position
                ]

                before_events = len(
                    profile.get(
                        "newspaper_mentions",
                        []
                    )
                )

                changed = update_profile(
                    profile,
                    details,
                    event
                )

                after_events = len(
                    profile.get(
                        "newspaper_mentions",
                        []
                    )
                )

                if after_events > before_events:

                    new_events += 1

                elif changed:

                    updated_profiles += 1

                else:

                    duplicate_events += 1

                continue

            # ------------------------------------------------
            # New profile
            # ------------------------------------------------

            profile = create_profile(
                details,
                initiative_type,
                event
            )

            initiatives.append(
                profile
            )

            index[
                normalized
            ] = len(
                initiatives
            ) - 1

            new_profiles += 1
            new_events += 1

    # --------------------------------------------------------
    # Count events
    # --------------------------------------------------------

    total_events = sum(
        len(
            profile.get(
                "newspaper_mentions",
                []
            )
        )
        for profile in initiatives
    )

    # --------------------------------------------------------
    # Update metadata
    # --------------------------------------------------------

    bank[
        "database_version"
    ] = "v2.1"

    bank[
        "last_updated"
    ] = now_iso()

    bank[
        "initiative_count"
    ] = len(
        initiatives
    )

    bank[
        "event_count"
    ] = total_events

    bank[
        "initiatives"
    ] = initiatives

    review_data[
        "queue_version"
    ] = "v2.1"

    review_data[
        "last_updated"
    ] = now_iso()

    review_data[
        "items"
    ] = review_items

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_json(
        BANK_FILE,
        bank
    )

    save_json(
        REVIEW_FILE,
        review_data
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    report = []

    report.append(
        "=" * 80
    )

    report.append(
        "AGRICULTURE INTELLIGENCE SYSTEM"
    )

    report.append(
        "GOVERNMENT INTELLIGENCE BANK REPORT v2.1"
    )

    report.append(
        "=" * 80
    )

    report.append("")

    report.append(
        f"Master records scanned: "
        f"{len(records)}"
    )

    report.append(
        f"New initiative profiles: "
        f"{new_profiles}"
    )

    report.append(
        f"Existing profiles updated: "
        f"{updated_profiles}"
    )

    report.append(
        f"New newspaper events: "
        f"{new_events}"
    )

    report.append(
        f"Duplicate events skipped: "
        f"{duplicate_events}"
    )

    report.append(
        f"Review queue additions: "
        f"{review_added}"
    )

    report.append(
        f"Total initiative profiles: "
        f"{len(initiatives)}"
    )

    report.append(
        f"Total newspaper events: "
        f"{total_events}"
    )

    report.append("")

    report.append(
        "-" * 80
    )

    report.append(
        "INITIATIVE TYPE DISTRIBUTION"
    )

    report.append(
        "-" * 80
    )

    if type_distribution:

        for key, value in sorted(
            type_distribution.items()
        ):

            report.append(
                f"{key}: {value}"
            )

    else:

        report.append(
            "No initiative events detected."
        )

    report.append("")

    report.append(
        "-" * 80
    )

    report.append(
        "EVENT TYPE DISTRIBUTION"
    )

    report.append(
        "-" * 80
    )

    if event_distribution:

        for key, value in sorted(
            event_distribution.items()
        ):

            report.append(
                f"{key}: {value}"
            )

    else:

        report.append(
            "No events detected."
        )

    report.append("")

    report.append(
        "-" * 80
    )

    report.append(
        "CURRENT GOVERNMENT INTELLIGENCE BANK"
    )

    report.append(
        "-" * 80
    )

    for number, profile in enumerate(
        initiatives,
        start=1
    ):

        report.append("")

        report.append(
            f"{number}. "
            f"{profile.get('initiative_name', '')}"
        )

        report.append(
            f"   Type: "
            f"{profile.get('initiative_type', '')}"
        )

        report.append(
            f"   Category: "
            f"{profile.get('category', '')}"
        )

        report.append(
            f"   Ministry: "
            f"{profile.get('ministry', '')}"
        )

        report.append(
            f"   Latest update: "
            f"{profile.get('latest_update', '')}"
        )

        report.append(
            f"   Newspaper events: "
            f"{len(profile.get('newspaper_mentions', []))}"
        )

    report.append("")

    report.append(
        "-" * 80
    )

    report.append(
        "REVIEW QUEUE"
    )

    report.append(
        "-" * 80
    )

    report.append(
        f"Total review items: "
        f"{len(review_items)}"
    )

    report.append("")

    report.append(
        "UTF-8 text normalization is enabled."
    )

    report.append(
        "Existing profiles are preserved."
    )

    report.append(
        "Duplicate newspaper events are skipped."
    )

    report.append(
        "No external scheme information was invented."
    )

    report.append(
        "The Master Intelligence Database was not modified."
    )

    report.append("")

    report.append(
        "=" * 80
    )

    report.append(
        "END OF REPORT"
    )

    report.append(
        "=" * 80
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(
                report
            )
        )

    # --------------------------------------------------------
    # Terminal output
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print(
        "GOVERNMENT INTELLIGENCE BANK BUILD COMPLETE"
    )
    print("=" * 80)

    print()
    print(
        f"New initiative profiles: "
        f"{new_profiles}"
    )

    print(
        f"Existing profiles updated: "
        f"{updated_profiles}"
    )

    print(
        f"New newspaper events: "
        f"{new_events}"
    )

    print(
        f"Duplicate events skipped: "
        f"{duplicate_events}"
    )

    print(
        f"Review queue additions: "
        f"{review_added}"
    )

    print(
        f"Total initiative profiles: "
        f"{len(initiatives)}"
    )

    print(
        f"Total newspaper events: "
        f"{total_events}"
    )

    print()
    print(
        "Output:"
    )

    print(
        BANK_FILE
    )

    print(
        REVIEW_FILE
    )

    print(
        REPORT_FILE
    )

    print()
    print(
        "The Master Database was NOT modified."
    )

    print()


if __name__ == "__main__":
    main()