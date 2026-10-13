from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from difflib import SequenceMatcher

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MASTER_FILE = (
    BASE_DIR
    / "data"
    / "master_database_v1"
    / "MASTER_INTELLIGENCE_DATABASE_v1.json"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "connections_bank_v1_1"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "CONNECTIONS_BANK_v1_1.json"
)

REPORT_FILE = (
    OUTPUT_DIR
    / "CONNECTIONS_BANK_REPORT_v1_1.txt"
)

MODEL_NAME = "gemini-3.1-flash-lite"

REQUEST_INTERVAL_SECONDS = 4.5
MAX_RETRIES = 4

EVENT_BATCH_SIZE = 12
RELATIONSHIP_BATCH_SIZE = 10

MAX_RELATIONSHIP_CANDIDATES = 150


# ============================================================
# GEMINI SETUP
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY was not found in .env"
    )

client = genai.Client(
    api_key=API_KEY
)

GEMINI_CALLS = 0


# ============================================================
# HELPERS
# ============================================================

def now_iso() -> str:
    return datetime.now().isoformat(
        timespec="seconds"
    )


def clean(value: Any) -> str:

    if value is None:
        return ""

    return (
        " ".join(
            str(value)
            .replace("\n", " ")
            .replace("\r", " ")
            .split()
        )
        .strip()
    )


def norm(value: Any) -> str:

    text = clean(value).lower()

    text = re.sub(
        r"[^a-z0-9₹$% ]+",
        " ",
        text
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def tokens(value: Any) -> set[str]:

    text = norm(value)

    if not text:
        return set()

    return set(
        x
        for x in text.split()
        if len(x) >= 3
    )


def as_list(value: Any) -> list:

    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def load_json(
    path: Path
) -> Any:

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(
    data: Any,
    path: Path
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp = path.with_suffix(
        path.suffix + ".tmp"
    )

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp.replace(path)


def extract_json(
    text: str
) -> Any:

    text = (
        text or ""
    ).strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    try:

        return json.loads(text)

    except Exception:
        pass

    for opening, closing in [
        ("{", "}"),
        ("[", "]")
    ]:

        start = text.find(opening)
        end = text.rfind(closing)

        if (
            start >= 0
            and end > start
        ):

            try:

                return json.loads(
                    text[
                        start:end + 1
                    ]
                )

            except Exception:
                pass

    raise ValueError(
        "Gemini did not return valid JSON."
    )


# ============================================================
# GEMINI CALL
# ============================================================

def gemini_call(
    prompt: str,
    schema: dict
) -> Any:

    global GEMINI_CALLS

    if GEMINI_CALLS > 0:

        time.sleep(
            REQUEST_INTERVAL_SECONDS
        )

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            response = (
                client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=(
                        types.GenerateContentConfig(
                            temperature=0.2,
                            response_mime_type="application/json",
                            response_schema=schema,
                        )
                    ),
                )
            )

            GEMINI_CALLS += 1

            return extract_json(
                response.text or ""
            )

        except Exception as exc:

            print(
                f"  Gemini attempt "
                f"{attempt}/{MAX_RETRIES} failed: "
                f"{str(exc)[:250]}"
            )

            if attempt == MAX_RETRIES:
                raise

            time.sleep(
                min(
                    20 * attempt,
                    90
                )
            )


# ============================================================
# TOPIC GROUPS
# ============================================================

TOPIC_GROUPS = {

    "MONSOON_WATER": {
        "monsoon",
        "rainfall",
        "rain",
        "drought",
        "deficit",
        "el nino",
        "water",
        "irrigation",
        "kharif",
        "rabi",
    },

    "AGRICULTURE": {
        "agriculture",
        "farmer",
        "farmers",
        "crop",
        "crops",
        "farming",
        "yield",
        "harvest",
        "fertilizer",
        "fertiliser",
        "foodgrain",
        "food grains",
        "farm",
        "production",
    },

    "PULSES": {
        "pulses",
        "pulse",
        "chana",
        "gram",
        "peas",
        "tur",
        "urad",
        "dal",
    },

    "MSP_SUPPORT": {
        "msp",
        "minimum support price",
        "procurement",
        "support price",
        "subsidy",
        "subsidies",
    },

    "IMPORT_EXPORT": {
        "import",
        "imports",
        "export",
        "exports",
        "duty",
        "duties",
        "trade",
        "tariff",
        "tariffs",
        "shipment",
        "shipments",
        "customs",
    },

    "PRICES_INFLATION": {
        "inflation",
        "prices",
        "price",
        "cost",
        "costs",
        "food inflation",
        "consumer",
        "cpi",
        "wpi",
    },

    "FISCAL_POLICY": {
        "fiscal",
        "deficit",
        "capex",
        "capital expenditure",
        "government",
        "budget",
        "gst",
        "tax",
        "spending",
    },

    "BANKING_CREDIT": {
        "bank",
        "banks",
        "banking",
        "credit",
        "loan",
        "loans",
        "lending",
        "nbfc",
        "deposit",
        "deposits",
        "interest",
        "rbi",
        "repo",
    },

    "DIGITAL_PAYMENTS": {
        "upi",
        "mdr",
        "payments",
        "payment",
        "digital payment",
        "transaction",
        "transactions",
        "fintech",
    },

    "CURRENCY": {
        "rupee",
        "rupees",
        "dollar",
        "currency",
        "exchange",
        "forex",
        "depreciated",
        "depreciation",
    },

    "RATES_BONDS": {
        "bond",
        "bonds",
        "yield",
        "yields",
        "gsec",
        "securities",
        "rate",
        "rates",
        "repo",
    },

    "INVESTMENT": {
        "ipo",
        "drhp",
        "investment",
        "investments",
        "investor",
        "investors",
        "capital",
        "funding",
        "capex",
    },

    "SUPPLY_CHAIN": {
        "supply",
        "chain",
        "logistics",
        "warehouse",
        "warehousing",
        "transport",
        "storage",
        "processing",
        "manufacturing",
        "distribution",
    },

    "ENERGY": {
        "energy",
        "power",
        "renewable",
        "renewables",
        "green",
        "electricity",
        "wind",
        "solar",
        "oil",
        "crude",
        "fuel",
    },

    "INTERNATIONAL": {
        "eu",
        "europe",
        "european",
        "us",
        "usa",
        "america",
        "china",
        "global",
        "international",
        "foreign",
        "geopolitical",
    },
}


# ============================================================
# RELATED TOPICS
# ============================================================

RELATED_TOPIC_PAIRS = {

    frozenset({
        "MONSOON_WATER",
        "AGRICULTURE"
    }),

    frozenset({
        "AGRICULTURE",
        "PULSES"
    }),

    frozenset({
        "AGRICULTURE",
        "MSP_SUPPORT"
    }),

    frozenset({
        "AGRICULTURE",
        "IMPORT_EXPORT"
    }),

    frozenset({
        "AGRICULTURE",
        "PRICES_INFLATION"
    }),

    frozenset({
        "AGRICULTURE",
        "FISCAL_POLICY"
    }),

    frozenset({
        "AGRICULTURE",
        "BANKING_CREDIT"
    }),

    frozenset({
        "AGRICULTURE",
        "SUPPLY_CHAIN"
    }),

    frozenset({
        "AGRICULTURE",
        "ENERGY"
    }),

    frozenset({
        "PULSES",
        "IMPORT_EXPORT"
    }),

    frozenset({
        "PULSES",
        "PRICES_INFLATION"
    }),

    frozenset({
        "MSP_SUPPORT",
        "FISCAL_POLICY"
    }),

    frozenset({
        "IMPORT_EXPORT",
        "CURRENCY"
    }),

    frozenset({
        "IMPORT_EXPORT",
        "PRICES_INFLATION"
    }),

    frozenset({
        "IMPORT_EXPORT",
        "INTERNATIONAL"
    }),

    frozenset({
        "BANKING_CREDIT",
        "DIGITAL_PAYMENTS"
    }),

    frozenset({
        "BANKING_CREDIT",
        "FISCAL_POLICY"
    }),

    frozenset({
        "BANKING_CREDIT",
        "MACRO_ECONOMY"
    }),

    frozenset({
        "CURRENCY",
        "INTERNATIONAL"
    }),

    frozenset({
        "ENERGY",
        "PRICES_INFLATION"
    }),

    frozenset({
        "ENERGY",
        "IMPORT_EXPORT"
    }),

    frozenset({
        "SUPPLY_CHAIN",
        "IMPORT_EXPORT"
    }),

    frozenset({
        "SUPPLY_CHAIN",
        "PRICES_INFLATION"
    }),
}


# ============================================================
# CATEGORY BRIDGES
# ============================================================

CATEGORY_BRIDGES = {

    frozenset({
        "CORE_AGRICULTURE",
        "INTERNATIONAL_TRADE"
    }),

    frozenset({
        "CORE_AGRICULTURE",
        "MACRO_ECONOMY"
    }),

    frozenset({
        "CORE_AGRICULTURE",
        "BANKING_FINANCE"
    }),

    frozenset({
        "CORE_AGRICULTURE",
        "GENERAL_BUSINESS"
    }),

    frozenset({
        "INTERNATIONAL_TRADE",
        "MACRO_ECONOMY"
    }),

    frozenset({
        "BANKING_FINANCE",
        "MACRO_ECONOMY"
    }),

    frozenset({
        "BANKING_FINANCE",
        "GENERAL_BUSINESS"
    }),

    frozenset({
        "INTERNATIONAL_TRADE",
        "GENERAL_BUSINESS"
    }),

    frozenset({
        "MACRO_ECONOMY",
        "GENERAL_BUSINESS"
    }),
}


# ============================================================
# RECORD TEXT
# ============================================================

def record_text(
    record: dict
) -> str:

    final_analysis = (
        record.get(
            "final_analysis"
        )
        or {}
    )

    parts = [

        record.get(
            "source_headline"
        ),

        final_analysis.get(
            "headline"
        ),

        final_analysis.get(
            "summary"
        ),

        final_analysis.get(
            "what_happened"
        ),

        final_analysis.get(
            "why_it_matters"
        ),

        final_analysis.get(
            "agriculture_impact"
        ),

        final_analysis.get(
            "agriculture_relevance_reason"
        ),
    ]

    for field in [
        "topics",
        "key_facts",
        "reported_facts",
        "interpretations",
        "connections",
        "government_schemes",
    ]:

        parts.extend(
            as_list(
                final_analysis.get(
                    field
                )
            )
        )

    return norm(
        " ".join(
            clean(x)
            for x in parts
            if x
        )
    )


def topic_groups(
    text: str
) -> list[str]:

    groups = []

    for group, keywords in TOPIC_GROUPS.items():

        for keyword in keywords:

            if keyword in text:

                groups.append(group)

                break

    return groups


# ============================================================
# COMPACT RECORD
# ============================================================

def compact_record(
    record: dict
) -> dict:

    final_analysis = (
        record.get(
            "final_analysis"
        )
        or {}
    )

    curation = (
        record.get(
            "curation"
        )
        or {}
    )

    text = record_text(
        record
    )

    headline = clean(
        final_analysis.get(
            "headline"
        )
        or record.get(
            "source_headline"
        )
    )

    summary = clean(
        final_analysis.get(
            "summary"
        )
        or final_analysis.get(
            "what_happened"
        )
    )

    facts = [
        clean(x)
        for x in as_list(
            final_analysis.get(
                "key_facts"
            )
        )
        if clean(x)
    ][:6]

    reported = [
        clean(x)
        for x in as_list(
            final_analysis.get(
                "reported_facts"
            )
        )
        if clean(x)
    ][:6]

    return {

        "record_id":
            clean(
                record.get(
                    "record_id"
                )
            ),

        "headline":
            headline,

        "summary":
            summary[:1000],

        "key_facts":
            [
                x[:300]
                for x in facts
            ],

        "reported_facts":
            [
                x[:300]
                for x in reported
            ],

        "agriculture_impact":
            clean(
                final_analysis.get(
                    "agriculture_impact"
                )
            )[:700],

        "why_it_matters":
            clean(
                final_analysis.get(
                    "why_it_matters"
                )
            )[:700],

        "topics":
            topic_groups(
                text
            ),

        "category":
            clean(
                curation.get(
                    "primary_category"
                )
                or record.get(
                    "primary_category"
                )
                or final_analysis.get(
                    "primary_category"
                )
            ).upper(),

        "agriculture_relevance":
            clean(
                curation.get(
                    "agriculture_connection"
                )
                or final_analysis.get(
                    "agriculture_relevance"
                )
            ).upper(),

        "placement_relevance":
            clean(
                curation.get(
                    "placement_relevance"
                )
                or final_analysis.get(
                    "placement_relevance"
                )
            ).upper(),

        "newspaper":
            clean(
                record.get(
                    "newspaper"
                )
            ),

        "date":
            clean(
                record.get(
                    "date"
                )
            ),

        "page":
            record.get(
                "page"
            ),
    }


# ============================================================
# GEMINI EVENT GROUPING
# ============================================================

EVENT_SCHEMA = {

    "type": "OBJECT",

    "properties": {

        "events": {

            "type": "ARRAY",

            "items": {

                "type": "OBJECT",

                "properties": {

                    "record_id": {
                        "type": "STRING"
                    },

                    "event_id": {
                        "type": "STRING"
                    },

                    "event_label": {
                        "type": "STRING"
                    },

                    "confidence": {
                        "type": "STRING"
                    },
                },

                "required": [
                    "record_id",
                    "event_id",
                    "event_label",
                    "confidence",
                ],
            },
        }
    },

    "required": [
        "events"
    ],
}


def identify_events(
    records: list[dict]
) -> dict[str, dict]:

    event_map = {}

    total_batches = (
        len(records)
        + EVENT_BATCH_SIZE
        - 1
    ) // EVENT_BATCH_SIZE

    print()
    print(
        "STAGE 1: Identifying underlying events with Gemini..."
    )

    print(
        f"Records: {len(records)}"
    )

    print(
        f"Gemini batches: {total_batches}"
    )

    for start in range(
        0,
        len(records),
        EVENT_BATCH_SIZE
    ):

        batch = records[
            start:start + EVENT_BATCH_SIZE
        ]

        batch_number = (
            start // EVENT_BATCH_SIZE
        ) + 1

        print(
            f"  Event batch "
            f"{batch_number}/{total_batches}"
        )

        prompt = f"""
Identify the underlying real-world EVENT represented by
each newspaper record.

The purpose is to distinguish:
A) multiple newspaper reports of the SAME event
from
B) genuinely DIFFERENT developments.

Rules:

1. Same underlying development = same event_id.
2. Different development = different event_id.
3. Do not group stories merely because they concern the same
   broad sector.
4. Two stories about the same announcement, regulation,
   dispute, market move, or incident should normally share
   an event_id.
5. Do not use outside knowledge.
6. Do not invent facts.
7. Return exactly one mapping for every record.

Records:

{json.dumps(
    batch,
    ensure_ascii=False,
    indent=2
)}
"""

        result = gemini_call(
            prompt,
            EVENT_SCHEMA
        )

        returned = {}

        for item in result.get(
            "events",
            []
        ):

            record_id = clean(
                item.get(
                    "record_id"
                )
            )

            if record_id:

                returned[
                    record_id
                ] = item

        for record in batch:

            record_id = record[
                "record_id"
            ]

            item = returned.get(
                record_id
            )

            if item:

                event_id = clean(
                    item.get(
                        "event_id"
                    )
                )

                if event_id:

                    event_map[
                        record_id
                    ] = {

                        "event_id":
                            event_id,

                        "event_label":
                            clean(
                                item.get(
                                    "event_label"
                                )
                            ),

                        "confidence":
                            clean(
                                item.get(
                                    "confidence"
                                )
                            ),
                    }

                    continue

            event_map[
                record_id
            ] = {

                "event_id":
                    "EVENT_" + record_id,

                "event_label":
                    record[
                        "headline"
                    ],

                "confidence":
                    "LOW",
            }

    return event_map


# ============================================================
# DETERMINISTIC SAME-EVENT SAFETY LAYER
# ============================================================

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "will",
    "has",
    "have",
    "into",
    "over",
    "under",
    "after",
    "before",
    "about",
    "india",
    "indian",
    "more",
    "than",
    "their",
    "they",
    "its",
    "are",
    "was",
    "were",
    "been",
    "being",
    "may",
    "can",
    "could",
    "would",
    "should",
    "amid",
    "amidst",
    "says",
    "said",
    "report",
    "reports",
    "new",
}


def important_tokens(
    text: str
) -> set[str]:

    result = set()

    for token in tokens(text):

        if token in STOPWORDS:
            continue

        if len(token) < 4:
            continue

        result.add(token)

    return result


def headline_similarity(
    a: dict,
    b: dict
) -> float:

    ha = norm(
        a.get(
            "headline"
        )
    )

    hb = norm(
        b.get(
            "headline"
        )
    )

    if not ha or not hb:
        return 0.0

    return SequenceMatcher(
        None,
        ha,
        hb
    ).ratio()


def token_overlap(
    a: set[str],
    b: set[str]
) -> float:

    if not a or not b:
        return 0.0

    intersection = (
        a & b
    )

    denominator = min(
        len(a),
        len(b)
    )

    if denominator == 0:
        return 0.0

    return (
        len(intersection)
        / denominator
    )


def shared_important_tokens(
    a: dict,
    b: dict
) -> set[str]:

    ta = important_tokens(
        a.get(
            "headline",
            ""
        )
        + " "
        + " ".join(
            a.get(
                "key_facts",
                []
            )
        )
    )

    tb = important_tokens(
        b.get(
            "headline",
            ""
        )
        + " "
        + " ".join(
            b.get(
                "key_facts",
                []
            )
        )
    )

    return ta & tb


def same_event_similarity(
    a: dict,
    b: dict
) -> tuple[bool, str, float]:

    # --------------------------------------------------------
    # 1. Gemini already says same event
    # --------------------------------------------------------

    # This check is handled outside because event IDs are
    # supplied separately.


    # --------------------------------------------------------
    # 2. Headline similarity
    # --------------------------------------------------------

    hs = headline_similarity(
        a,
        b
    )

    # Very similar headlines are strong evidence.
    if hs >= 0.82:

        return (
            True,
            "very_similar_headlines",
            hs
        )


    # --------------------------------------------------------
    # 3. Shared specific entities / event terms
    # --------------------------------------------------------

    shared = (
        shared_important_tokens(
            a,
            b
        )
    )

    # Strong overlap in a short headline.
    headline_a = important_tokens(
        a.get(
            "headline",
            ""
        )
    )

    headline_b = important_tokens(
        b.get(
            "headline",
            ""
        )
    )

    headline_shared = (
        headline_a
        &
        headline_b
    )

    # Three or more important headline terms in common
    # is a strong duplicate signal.
    if len(
        headline_shared
    ) >= 3:

        return (
            True,
            "multiple_shared_headline_entities",
            0.90
        )


    # --------------------------------------------------------
    # 4. Very strong fact overlap
    # --------------------------------------------------------

    fact_a = important_tokens(
        " ".join(
            a.get(
                "key_facts",
                []
            )
        )
    )

    fact_b = important_tokens(
        " ".join(
            b.get(
                "key_facts",
                []
            )
        )
    )

    fact_overlap = token_overlap(
        fact_a,
        fact_b
    )

    if (
        fact_overlap >= 0.72
        and len(shared) >= 4
    ):

        return (
            True,
            "strong_key_fact_overlap",
            fact_overlap
        )


    # --------------------------------------------------------
    # 5. Headline + summary combined
    # --------------------------------------------------------

    combined_a = important_tokens(
        a.get(
            "headline",
            ""
        )
        + " "
        + a.get(
            "summary",
            ""
        )
    )

    combined_b = important_tokens(
        b.get(
            "headline",
            ""
        )
        + " "
        + b.get(
            "summary",
            ""
        )
    )

    combined_overlap = token_overlap(
        combined_a,
        combined_b
    )

    if (
        combined_overlap >= 0.70
        and len(shared) >= 5
    ):

        return (
            True,
            "strong_combined_text_overlap",
            combined_overlap
        )


    return (
        False,
        "",
        0.0
    )


# ============================================================
# CANDIDATE GENERATION
# ============================================================

def common_topics(
    a: dict,
    b: dict
) -> list[str]:

    return sorted(
        set(
            a["topics"]
        )
        &
        set(
            b["topics"]
        )
    )


def candidate_score(
    a: dict,
    b: dict
) -> int:

    shared = set(
        common_topics(
            a,
            b
        )
    )

    score = (
        len(shared)
        * 2
    )

    for topic_a in shared:

        for topic_b in (
            set(a["topics"])
            |
            set(b["topics"])
        ):

            if topic_a == topic_b:
                continue

            if frozenset({
                topic_a,
                topic_b
            }) in RELATED_TOPIC_PAIRS:

                score += 3

    category_pair = frozenset({
        a.get(
            "category"
        ),
        b.get(
            "category"
        )
    })

    if category_pair in CATEGORY_BRIDGES:

        score += 3

    ag_values = {
        a.get(
            "agriculture_relevance"
        ),
        b.get(
            "agriculture_relevance"
        )
    }

    if "DIRECT" in ag_values:

        score += 3

    elif "INDIRECT" in ag_values:

        score += 2

    if (
        a.get(
            "placement_relevance"
        )
        == "HIGH"
        or
        b.get(
            "placement_relevance"
        )
        == "HIGH"
    ):

        score += 1

    return score


def build_candidates(
    records: list[dict],
    events: dict[str, dict]
) -> tuple[
    list[dict],
    int,
    int,
    int,
    list[dict]
]:

    candidates = []

    same_event_rejected = 0
    duplicate_rejected = 0
    unrelated_rejected = 0

    duplicate_examples = []

    for i in range(
        len(records)
    ):

        for j in range(
            i + 1,
            len(records)
        ):

            a = records[i]
            b = records[j]

            event_a = events[
                a["record_id"]
            ][
                "event_id"
            ]

            event_b = events[
                b["record_id"]
            ][
                "event_id"
            ]

            # ------------------------------------------------
            # FIRST SAFETY CHECK:
            # GEMINI EVENT ID
            # ------------------------------------------------

            if event_a == event_b:

                same_event_rejected += 1

                continue

            # ------------------------------------------------
            # SECOND SAFETY CHECK:
            # DETERMINISTIC CONTENT SIMILARITY
            # ------------------------------------------------

            (
                is_duplicate,
                duplicate_reason,
                duplicate_score
            ) = same_event_similarity(
                a,
                b
            )

            if is_duplicate:

                duplicate_rejected += 1

                if len(
                    duplicate_examples
                ) < 10:

                    duplicate_examples.append({

                        "record_a":
                            a["record_id"],

                        "record_b":
                            b["record_id"],

                        "headline_a":
                            a["headline"],

                        "headline_b":
                            b["headline"],

                        "reason":
                            duplicate_reason,

                        "score":
                            round(
                                duplicate_score,
                                3
                            ),
                    })

                continue

            # ------------------------------------------------
            # TOPIC / CATEGORY FILTER
            # ------------------------------------------------

            shared = common_topics(
                a,
                b
            )

            category_pair = frozenset({
                a.get(
                    "category"
                ),
                b.get(
                    "category"
                )
            })

            has_bridge = (
                category_pair
                in CATEGORY_BRIDGES
            )

            if (
                not shared
                and not has_bridge
            ):

                unrelated_rejected += 1

                continue

            candidates.append({

                "a":
                    a,

                "b":
                    b,

                "shared_topics":
                    shared,

                "score":
                    candidate_score(
                        a,
                        b
                    ),
            })

    candidates.sort(
        key=lambda x: (
            x["score"],
            len(
                x["shared_topics"]
            )
        ),
        reverse=True
    )

    candidates = candidates[
        :MAX_RELATIONSHIP_CANDIDATES
    ]

    return (
        candidates,
        same_event_rejected,
        duplicate_rejected,
        unrelated_rejected,
        duplicate_examples
    )


# ============================================================
# GEMINI RELATIONSHIP REVIEW
# ============================================================

REL_SCHEMA = {

    "type": "OBJECT",

    "properties": {

        "connections": {

            "type": "ARRAY",

            "items": {

                "type": "OBJECT",

                "properties": {

                    "record_id_a": {
                        "type": "STRING"
                    },

                    "record_id_b": {
                        "type": "STRING"
                    },

                    "accepted": {
                        "type": "BOOLEAN"
                    },

                    "connection_type": {
                        "type": "STRING"
                    },

                    "relationship_type": {
                        "type": "STRING"
                    },

                    "entities": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        }
                    },

                    "relationship": {
                        "type": "STRING"
                    },

                    "chain": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        }
                    },

                    "evidence": {
                        "type": "ARRAY",
                        "items": {
                            "type": "STRING"
                        }
                    },

                    "explanation": {
                        "type": "STRING"
                    },

                    "agriculture_relevance": {
                        "type": "STRING"
                    },

                    "placement_relevance": {
                        "type": "STRING"
                    },

                    "confidence": {
                        "type": "STRING"
                    },

                    "rejection_reason": {
                        "type": "STRING"
                    },
                },

                "required": [
                    "record_id_a",
                    "record_id_b",
                    "accepted",
                    "connection_type",
                    "relationship_type",
                    "entities",
                    "relationship",
                    "chain",
                    "evidence",
                    "explanation",
                    "agriculture_relevance",
                    "placement_relevance",
                    "confidence",
                    "rejection_reason",
                ],
            },
        }
    },

    "required": [
        "connections"
    ],
}


def review_relationships(
    candidates: list[dict]
) -> list[dict]:

    accepted = []

    if not candidates:

        return accepted

    total_batches = (
        len(candidates)
        + RELATIONSHIP_BATCH_SIZE
        - 1
    ) // RELATIONSHIP_BATCH_SIZE

    print()
    print(
        "STAGE 3: Gemini semantic relationship review..."
    )

    print(
        f"Candidates sent to Gemini: "
        f"{len(candidates)}"
    )

    print(
        f"Relationship batches: "
        f"{total_batches}"
    )

    for start in range(
        0,
        len(candidates),
        RELATIONSHIP_BATCH_SIZE
    ):

        batch = candidates[
            start:start
            + RELATIONSHIP_BATCH_SIZE
        ]

        batch_number = (
            start // RELATIONSHIP_BATCH_SIZE
        ) + 1

        print(
            f"  Relationship batch "
            f"{batch_number}/{total_batches}"
        )

        payload = []

        for candidate in batch:

            payload.append({

                "record_a":
                    candidate["a"],

                "record_b":
                    candidate["b"],

                "shared_topics":
                    candidate[
                        "shared_topics"
                    ],

                "local_score":
                    candidate[
                        "score"
                    ],
            })

        prompt = f"""
You are the RELATIONSHIP INTELLIGENCE ANALYST for an
Agriculture Intelligence System.

You are reviewing pairs of newspaper records that have already
passed a preliminary same-event and relevance filter.

The two records should represent DIFFERENT underlying events.

Your task is to determine whether they form a meaningful
cross-event intelligence connection.

============================================================
WHAT COUNTS AS A CONNECTION
============================================================

A connection does NOT need to be explicitly stated in either
article.

A connection can be DERIVED when facts from the two different
events logically fit together.

Examples:

Event A:
Drought conditions are affecting kharif crops.

Event B:
Domestic production shortfalls are contributing to higher
edible-oil imports.

Potential derived connection:

Drought / crop stress
→ production conditions
→ domestic supply
→ import dependence

This is valid only if the supplied records support the relevant
steps.

The explanation must NOT claim that the drought caused the
entire import increase unless the records establish that.

============================================================
CONNECTION TYPES
============================================================

DIRECT:
The records explicitly establish the relationship.

DERIVED:
The relationship follows reasonably from facts in the two
records.

CONTEXTUAL:
The two developments provide useful context for understanding
each other, but causality is not established.

============================================================
RELATIONSHIP TYPES
============================================================

Choose one:

CAUSE_EFFECT
SUPPLY_DEMAND
POLICY_IMPACT
MARKET_TRADE
MACRO_SECTOR
FINANCIAL_REAL_ECONOMY
SUPPLY_CHAIN
PRICE_TRANSMISSION
INTERNATIONAL_TRADE
CONTEXTUAL

============================================================
ACCEPT IF
============================================================

Accept when the two DIFFERENT events create a meaningful
relationship such as:

- agriculture and trade
- agriculture and imports
- agriculture and prices
- agriculture and weather
- agriculture and government policy
- agriculture and banking/credit
- agriculture and supply chains
- agriculture and energy
- agriculture and macroeconomics
- banking and business
- banking and digital payments
- banking and macroeconomics
- currency and imports/exports
- energy and prices
- energy and imports
- international developments and Indian trade
- fiscal policy and sectoral support
- investment and business
- supply chain and trade
- supply chain and agriculture

============================================================
REJECT IF
============================================================

Reject when:

1. The records describe the same underlying event.
2. The relationship is only broad thematic similarity.
3. The connection requires outside information.
4. The connection requires unsupported causality.
5. The relationship is merely coincidental.
6. The two events do not provide useful information for
   understanding each other.

============================================================
EVIDENCE RULE
============================================================

Every accepted connection MUST contain:

- at least two evidence statements
- evidence from BOTH records
- a logical relationship
- a short explanation

Do not invent facts, numbers, dates, entities or mechanisms.

============================================================
CAUSALITY RULE
============================================================

Do not overstate.

Prefer:

"can contribute to"
"can affect"
"provides a channel through which"
"is linked with"
"provides context for"
"is consistent with"
"may influence"

when the records do not prove direct causality.

============================================================
AGRICULTURE RELEVANCE
============================================================

Use:

DIRECT
INDIRECT
CONTEXTUAL
NONE

============================================================
PLACEMENT RELEVANCE
============================================================

Use:

HIGH
MEDIUM
LOW
NONE

============================================================
NO QUESTIONS
============================================================

Do NOT generate:

- GD questions
- interview questions
- quiz questions
- recommendations
- investment advice
- predictions

Return JSON only.

Candidates:

{json.dumps(
    payload,
    ensure_ascii=False,
    indent=2
)}
"""

        result = gemini_call(
            prompt,
            REL_SCHEMA
        )

        for item in result.get(
            "connections",
            []
        ):

            if (
                item.get(
                    "accepted"
                )
                is True
            ):

                accepted.append(
                    item
                )

    return accepted


# ============================================================
# MAKE CONNECTION RECORD
# ============================================================

def make_connection(
    item: dict,
    events: dict[str, dict],
    number: int
) -> dict:

    record_a = clean(
        item.get(
            "record_id_a"
        )
    )

    record_b = clean(
        item.get(
            "record_id_b"
        )
    )

    connection_type = (
        clean(
            item.get(
                "connection_type"
            )
        )
        .upper()
    )

    if connection_type not in {
        "DIRECT",
        "DERIVED",
        "CONTEXTUAL"
    }:

        connection_type = (
            "CONTEXTUAL"
        )

    relationship_type = (
        clean(
            item.get(
                "relationship_type"
            )
        )
        .upper()
    )

    allowed_relationship_types = {

        "CAUSE_EFFECT",
        "SUPPLY_DEMAND",
        "POLICY_IMPACT",
        "MARKET_TRADE",
        "MACRO_SECTOR",
        "FINANCIAL_REAL_ECONOMY",
        "SUPPLY_CHAIN",
        "PRICE_TRANSMISSION",
        "INTERNATIONAL_TRADE",
        "CONTEXTUAL",
    }

    if (
        relationship_type
        not in allowed_relationship_types
    ):

        relationship_type = (
            "CONTEXTUAL"
        )

    agriculture = (
        clean(
            item.get(
                "agriculture_relevance"
            )
        )
        .upper()
    )

    if agriculture not in {
        "DIRECT",
        "INDIRECT",
        "CONTEXTUAL",
        "NONE"
    }:

        agriculture = (
            "CONTEXTUAL"
        )

    placement = (
        clean(
            item.get(
                "placement_relevance"
            )
        )
        .upper()
    )

    if placement not in {
        "HIGH",
        "MEDIUM",
        "LOW",
        "NONE"
    }:

        placement = (
            "MEDIUM"
        )

    confidence = (
        clean(
            item.get(
                "confidence"
            )
        )
        .upper()
    )

    if confidence not in {
        "HIGH",
        "MEDIUM",
        "LOW"
    }:

        confidence = (
            "MEDIUM"
        )

    return {

        "connection_id":
            f"CONN_{number:04d}",

        "source_record_ids": [
            record_a,
            record_b
        ],

        "source_event_ids": [
            events[
                record_a
            ][
                "event_id"
            ],

            events[
                record_b
            ][
                "event_id"
            ]
        ],

        "connection_type":
            connection_type,

        "relationship_type":
            relationship_type,

        "entities": [
            clean(x)
            for x in as_list(
                item.get(
                    "entities"
                )
            )
            if clean(x)
        ],

        "relationship":
            clean(
                item.get(
                    "relationship"
                )
            ),

        "chain": [
            clean(x)
            for x in as_list(
                item.get(
                    "chain"
                )
            )
            if clean(x)
        ],

        "evidence": [
            clean(x)
            for x in as_list(
                item.get(
                    "evidence"
                )
            )
            if clean(x)
        ],

        "explanation":
            clean(
                item.get(
                    "explanation"
                )
            ),

        "agriculture_relevance":
            agriculture,

        "placement_relevance":
            placement,

        "confidence":
            confidence,

        "validation_status":
            "REVIEW",

        "created_at":
            now_iso(),

        "source":
            "GEMINI_SEMANTIC_REVIEW",
    }


# ============================================================
# SAVE CLEAN CONNECTION BANK
# ============================================================

def save_output(
    records: list[dict],
    events: dict[str, dict],
    candidates: int,
    same_event_rejected: int,
    duplicate_rejected: int,
    unrelated_rejected: int,
    new_connections: list[dict],
    duplicate_examples: list[dict]
) -> list[dict]:

    merged = []

    seen = set()

    for connection in new_connections:

        key = tuple(
            sorted(
                connection.get(
                    "source_record_ids",
                    []
                )
            )
        )

        if (
            len(key) != 2
            or key in seen
        ):

            continue

        seen.add(key)

        merged.append(
            connection
        )

    for index, connection in enumerate(
        merged,
        start=1
    ):

        connection[
            "connection_id"
        ] = f"CONN_{index:04d}"

    unique_events = len(
        {
            x[
                "event_id"
            ]
            for x in events.values()
        }
    )

    output = {

        "database_version":
            "v1.1",

        "generated_at":
            now_iso(),

        "method":
            (
                "Gemini event grouping + deterministic "
                "same-event safety layer + broad candidate "
                "filtering + Gemini semantic relationship review"
            ),

        "gemini_calls":
            GEMINI_CALLS,

        "placement_questions_generated":
            False,

        "master_database_modified":
            False,

        "clean_rebuild":
            True,

        "record_count":
            len(records),

        "unique_underlying_events":
            unique_events,

        "connection_count":
            len(merged),

        "connections":
            merged,

        "statistics": {

            "candidate_pairs_after_local_filter":
                candidates,

            "same_event_rejected":
                same_event_rejected,

            "duplicate_similarity_rejected":
                duplicate_rejected,

            "unrelated_pairs_rejected":
                unrelated_rejected,

            "new_connections":
                len(merged),

            "existing_connections_preserved":
                0,

            "final_connections":
                len(merged),
        },

        "duplicate_detection_examples":
            duplicate_examples,
    }

    save_json(
        output,
        OUTPUT_FILE
    )

    lines = [

        "=" * 78,

        "AGRICULTURE INTELLIGENCE SYSTEM",

        "CONNECTIONS / RELATIONSHIP "
        "INTELLIGENCE BANK v1.1",

        "=" * 78,

        "",

        f"Generated: {now_iso()}",

        "",

        "CLEAN REBUILD: YES",

        "Existing connections preserved: 0",

        "Master database modified: NO",

        "",

        f"Master records: "
        f"{len(records)}",

        f"Unique underlying events: "
        f"{unique_events}",

        f"Same-event pairs rejected: "
        f"{same_event_rejected}",

        f"Duplicate-similarity pairs rejected: "
        f"{duplicate_rejected}",

        f"Unrelated pairs rejected: "
        f"{unrelated_rejected}",

        f"Candidates sent to Gemini: "
        f"{candidates}",

        f"New connections: "
        f"{len(merged)}",

        f"Final connections: "
        f"{len(merged)}",

        f"Gemini/API calls: "
        f"{GEMINI_CALLS}",

        "",

        "Placement questions generated: 0",

        "",
    ]

    if duplicate_examples:

        lines.extend([
            "SAME-EVENT DUPLICATE EXAMPLES",
            "-" * 78,
            "",
        ])

        for example in duplicate_examples:

            lines.extend([
                f"Reason: "
                f"{example['reason']}",

                f"Score: "
                f"{example['score']}",

                f"A: "
                f"{example['headline_a']}",

                f"B: "
                f"{example['headline_b']}",

                "",
            ])

    lines.extend([
        "Output:",
        str(OUTPUT_FILE),
        "",
        "Master database was NOT modified.",
        "",
    ])

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(lines)
        )

    return merged


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 78
    )

    print(
        "AGRICULTURE INTELLIGENCE SYSTEM"
    )

    print(
        "CONNECTIONS / RELATIONSHIP "
        "INTELLIGENCE BANK v1.1"
    )

    print(
        "=" * 78
    )

    print()
    print(
        "CLEAN REBUILD MODE"
    )

    print(
        "Existing Connections Bank will NOT be preserved."
    )

    print(
        "Master database will NOT be modified."
    )

    # --------------------------------------------------------
    # LOAD MASTER
    # --------------------------------------------------------

    print()
    print(
        "Loading master database..."
    )

    if not MASTER_FILE.exists():

        raise FileNotFoundError(
            f"Master database not found:\n"
            f"{MASTER_FILE}"
        )

    master = load_json(
        MASTER_FILE
    )

    if isinstance(
        master,
        dict
    ):

        records = (
            master.get(
                "records"
            )
            or []
        )

    elif isinstance(
        master,
        list
    ):

        records = master

    else:

        records = []

    print(
        f"Master records loaded: "
        f"{len(records)}"
    )

    # --------------------------------------------------------
    # PREPARE
    # --------------------------------------------------------

    print()
    print(
        "Preparing master intelligence records..."
    )

    prepared = []

    for record in records:

        if not isinstance(
            record,
            dict
        ):

            continue

        compact = compact_record(
            record
        )

        if compact[
            "record_id"
        ]:

            prepared.append(
                compact
            )

    print(
        f"Prepared records: "
        f"{len(prepared)}"
    )

    # --------------------------------------------------------
    # STAGE 1
    # --------------------------------------------------------

    events = identify_events(
        prepared
    )

    unique_events = len(
        {
            x[
                "event_id"
            ]
            for x in events.values()
        }
    )

    print()
    print(
        f"Unique underlying events: "
        f"{unique_events}"
    )

    print(
        f"Gemini/API calls so far: "
        f"{GEMINI_CALLS}"
    )

    # --------------------------------------------------------
    # STAGE 2
    # --------------------------------------------------------

    print()
    print(
        "STAGE 2: Same-event safety + candidate filtering..."
    )

    (
        candidates,
        same_event_rejected,
        duplicate_rejected,
        unrelated_rejected,
        duplicate_examples
    ) = build_candidates(
        prepared,
        events
    )

    print(
        f"Same-event rejected by Gemini event ID: "
        f"{same_event_rejected}"
    )

    print(
        f"Duplicate/same-event rejected by content: "
        f"{duplicate_rejected}"
    )

    print(
        f"Unrelated pairs rejected: "
        f"{unrelated_rejected}"
    )

    print(
        f"Candidates after local filtering: "
        f"{len(candidates)}"
    )

    print(
        f"Maximum sent to Gemini: "
        f"{MAX_RELATIONSHIP_CANDIDATES}"
    )

    # --------------------------------------------------------
    # SHOW DUPLICATE EXAMPLES
    # --------------------------------------------------------

    if duplicate_examples:

        print()
        print(
            "Detected duplicate-event examples:"
        )

        for example in duplicate_examples[:5]:

            print(
                f"  - {example['reason']}: "
                f"{example['headline_a'][:100]} "
                f"<-> "
                f"{example['headline_b'][:100]}"
            )

    # --------------------------------------------------------
    # STAGE 3
    # --------------------------------------------------------

    accepted = review_relationships(
        candidates
    )

    print()
    print(
        f"Gemini accepted candidates: "
        f"{len(accepted)}"
    )

    # --------------------------------------------------------
    # VALIDATE ACCEPTED CONNECTIONS
    # --------------------------------------------------------

    new_connections = []

    record_lookup = {
        r["record_id"]: r
        for r in prepared
    }

    for item in accepted:

        record_a = clean(
            item.get(
                "record_id_a"
            )
        )

        record_b = clean(
            item.get(
                "record_id_b"
            )
        )

        if (
            record_a not in record_lookup
            or record_b not in record_lookup
        ):

            continue

        # Final event-ID safety check.
        if (
            events[
                record_a
            ][
                "event_id"
            ]
            ==
            events[
                record_b
            ][
                "event_id"
            ]
        ):

            continue

        # Final deterministic duplicate check.
        (
            duplicate,
            _,
            _
        ) = same_event_similarity(
            record_lookup[
                record_a
            ],
            record_lookup[
                record_b
            ]
        )

        if duplicate:

            continue

        relationship = clean(
            item.get(
                "relationship"
            )
        )

        explanation = clean(
            item.get(
                "explanation"
            )
        )

        evidence = [
            clean(x)
            for x in as_list(
                item.get(
                    "evidence"
                )
            )
            if clean(x)
        ]

        chain = [
            clean(x)
            for x in as_list(
                item.get(
                    "chain"
                )
            )
            if clean(x)
        ]

        if len(
            relationship
        ) < 20:

            continue

        if len(
            explanation
        ) < 40:

            continue

        if len(
            evidence
        ) < 2:

            continue

        if len(
            chain
        ) < 2:

            continue

        new_connections.append(
            make_connection(
                item,
                events,
                len(new_connections) + 1
            )
        )

    # --------------------------------------------------------
    # SAVE CLEAN DATABASE
    # --------------------------------------------------------

    merged = save_output(
        prepared,
        events,
        len(candidates),
        same_event_rejected,
        duplicate_rejected,
        unrelated_rejected,
        new_connections,
        duplicate_examples
    )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print()
    print(
        "=" * 78
    )

    print(
        "CONNECTIONS BANK BUILD COMPLETE"
    )

    print(
        "=" * 78
    )

    print(
        f"Master records: "
        f"{len(prepared)}"
    )

    print(
        f"Unique underlying events: "
        f"{unique_events}"
    )

    print(
        f"Same-event rejected: "
        f"{same_event_rejected}"
    )

    print(
        f"Duplicate-similarity rejected: "
        f"{duplicate_rejected}"
    )

    print(
        f"Local candidates: "
        f"{len(candidates)}"
    )

    print(
        f"Gemini accepted candidates: "
        f"{len(accepted)}"
    )

    print(
        f"Final validated connections: "
        f"{len(merged)}"
    )

    print(
        f"Gemini/API calls: "
        f"{GEMINI_CALLS}"
    )

    print(
        "Placement questions: 0"
    )

    print()
    print(
        "Output:"
    )

    print(
        OUTPUT_FILE
    )

    print(
        REPORT_FILE
    )

    print()
    print(
        "Master database was NOT modified."
    )


if __name__ == "__main__":

    main()