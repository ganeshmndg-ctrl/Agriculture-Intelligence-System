import json
import re
from pathlib import Path
from collections import Counter


# ================================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# CURATION + DEDUPLICATION V2.3
#
# V2.3 changes from V2.2:
#   1. Keeps V2.2 conservative duplicate engine unchanged
#   2. Correctly classifies oil-price stories as MACRO_ECONOMY
#   3. Removes duplicate primary/secondary categories
#   4. Adds intelligence_type:
#        CORE_INTELLIGENCE
#        PLACEMENT_INTELLIGENCE
#   5. Preserves provenance and final_analysis
#   6. Creates a separate V2.3 output directory
# ================================================================


BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "final_intelligence_v1"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "curated_intelligence_v23"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ================================================================
# BASIC HELPERS
# ================================================================

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for",
    "in", "on", "at", "by", "with", "from", "as", "into",
    "over", "under", "after", "before", "amid", "near",
    "up", "down", "new", "india", "indias", "indian",
    "this", "that", "its", "their", "more", "than"
}


def clean_text(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return " ".join(
            clean_text(x)
            for x in value
        )

    if isinstance(value, dict):
        return " ".join(
            clean_text(v)
            for v in value.values()
        )

    return str(value)


def normalize_text(value):

    text = clean_text(value).lower()

    text = text.replace("₹", " rupee ")

    text = re.sub(
        r"[^a-z0-9%]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def get_analysis(record):

    value = record.get(
        "final_analysis",
        {}
    )

    return value if isinstance(value, dict) else {}


def get_headline(record):

    analysis = get_analysis(record)

    return (
        analysis.get("headline")
        or record.get("headline")
        or record.get("source_headline")
        or ""
    ).strip()


def get_source_headline(record):

    return clean_text(
        record.get(
            "source_headline",
            ""
        )
    )


def get_summary(record):

    return clean_text(
        get_analysis(record).get(
            "summary",
            ""
        )
    )


def get_article_text(record):

    return clean_text(
        get_analysis(record).get(
            "article_text",
            ""
        )
    )


def get_content_type(record):

    return str(
        get_analysis(record).get(
            "content_type",
            "UNKNOWN"
        )
    ).upper()


def get_source_quality(record):

    return str(
        get_analysis(record).get(
            "source_quality",
            "UNKNOWN"
        )
    ).upper()


def get_agri_relevance(record):

    return str(
        get_analysis(record).get(
            "agriculture_relevance",
            "UNKNOWN"
        )
    ).upper()


def get_topics(record):

    topics = get_analysis(record).get(
        "topics",
        []
    )

    if not isinstance(topics, list):
        return []

    return [
        clean_text(x)
        for x in topics
        if clean_text(x)
    ]


def get_key_facts(record):

    facts = get_analysis(record).get(
        "key_facts",
        []
    )

    if not isinstance(facts, list):
        return []

    return [
        clean_text(x)
        for x in facts
        if clean_text(x)
    ]


def headline_tokens(record):

    text = normalize_text(
        get_headline(record)
    )

    return {
        token
        for token in text.split()
        if (
            len(token) >= 4
            and token not in STOPWORDS
        )
    }


# ================================================================
# SUBJECT TEXT
# ================================================================

def get_subject_text(record):

    parts = [

        get_headline(record),

        get_source_headline(record),

        get_summary(record),

        get_article_text(record),

        " ".join(
            get_topics(record)
        ),

        " ".join(
            get_key_facts(record)
        ),
    ]

    return normalize_text(
        " ".join(parts)
    )


# ================================================================
# PACKAGE HEADLINES
# ================================================================

PACKAGE_HEADLINES = {
    "stocks in the news",
    "market index update",
}


def is_package(record):

    headline = normalize_text(
        get_headline(record)
    )

    return headline in {
        normalize_text(x)
        for x in PACKAGE_HEADLINES
    }


# ================================================================
# OBVIOUSLY IRRELEVANT
# ================================================================

IRRELEVANT_PHRASES = [

    "child abuse",
    "csam",
    "hindi diwas",
    "formula 1",
    "revive f1",
    "luxury growth",
    "hilton",
    "peptide manufacturing",
    "project nanda fellowship",
]


def is_obviously_irrelevant(record):

    text = get_subject_text(
        record
    )

    return any(
        normalize_text(term) in text
        for term in IRRELEVANT_PHRASES
    )


# ================================================================
# PRIMARY CATEGORY
# ================================================================

def classify_primary_category(record):

    headline = normalize_text(
        get_headline(record)
    )

    source_headline = normalize_text(
        get_source_headline(record)
    )

    summary = normalize_text(
        get_summary(record)
    )

    article = normalize_text(
        get_article_text(record)
    )

    topics = normalize_text(
        " ".join(get_topics(record))
    )

    agri = get_agri_relevance(
        record
    )


    # ------------------------------------------------------------
    # PACKAGE
    # ------------------------------------------------------------

    if is_package(record):
        return "GENERAL_BUSINESS"


    # ------------------------------------------------------------
    # CORE AGRICULTURE
    # ------------------------------------------------------------

    core_agri_headline = [

        "agriculture",
        "agricultural",
        "farmer",
        "farmers",
        "farming",
        "crop",
        "crops",
        "kharif",
        "rabi",
        "rice",
        "wheat",
        "maize",
        "soybean",
        "oilseed",
        "oilseeds",
        "fertilizer",
        "fertiliser",
        "irrigation",
        "drought",
        "food security",
        "foodgrain",
        "food grains",
        "edible oil",
        "ethanol",
        "procurement",
        "farm output",
        "farm production",
        "agricultural commodity",
        "agricultural commodities",
        "cooking oil",
    ]


    if any(
        term in headline
        for term in core_agri_headline
    ):

        # IMPORTANT:
        # Oil-price headlines are macro, not agriculture.
        if any(
            term in headline
            for term in [
                "oil prices",
                "oil price",
                "crude oil",
                "oil spike",
            ]
        ) and not any(
            term in headline
            for term in [
                "cooking oil",
                "edible oil",
            ]
        ):

            pass

        else:

            return "CORE_AGRICULTURE"


    if (
        agri == "HIGH"
        and
        any(
            term in source_headline
            for term in core_agri_headline
        )
    ):

        return "CORE_AGRICULTURE"


    # ------------------------------------------------------------
    # AGRI TECH
    # ------------------------------------------------------------

    agri_tech_terms = [

        "agritech",
        "agri tech",
        "agtech",
        "precision agriculture",
        "digital agriculture",
        "farm technology",
        "agricultural technology",
    ]


    if any(
        term in headline
        for term in agri_tech_terms
    ):

        return "AGRI_TECH"


    # ------------------------------------------------------------
    # AGRIBUSINESS
    # ------------------------------------------------------------

    agribusiness_terms = [

        "agribusiness",
        "agri business",
        "agri input",
        "agri inputs",
        "farm machinery",
        "farm equipment",
        "tractor",
        "tractors",
        "food processing",
        "agricultural supply chain",
        "agri supply chain",
    ]


    if any(
        term in headline
        for term in agribusiness_terms
    ):

        return "AGRIBUSINESS"


    # ------------------------------------------------------------
    # RURAL ECONOMY
    # ------------------------------------------------------------

    rural_terms = [

        "rural economy",
        "rural demand",
        "rural market",
        "rural income",
        "rural employment",
        "rural unemployment",
        "rural consumption",
        "rural households",
        "village economy",
        "rural growth",
    ]


    if any(
        term in headline
        for term in rural_terms
    ):

        return "RURAL_ECONOMY"


    # ------------------------------------------------------------
    # BANKING / FINANCE
    # ------------------------------------------------------------

    finance_terms = [

        "rbi",
        "reserve bank",
        "banking",
        "bank",
        "npci",
        "upi",
        "merchant discount rate",
        "mdr",
        "credit",
        "loan",
        "interest rate",
        "monetary policy",
        "financial regulation",
        "financial market",
        "capital market",
        "ipo",
        "nifty",
        "sensex",
        "securities",
        "stock market",
        "bofa",
        "bofa securities",
    ]


    # Oil + Nifty is primarily macro, not banking.
    oil_macro_headline = (
        any(
            term in headline
            for term in [
                "oil prices",
                "oil price",
                "crude oil",
                "oil spike",
            ]
        )
        and
        any(
            term in headline
            for term in [
                "rupee",
                "nifty",
                "currency",
            ]
        )
    )


    if oil_macro_headline:

        return "MACRO_ECONOMY"


    if any(
        term in headline
        for term in finance_terms
    ):

        return "BANKING_FINANCE"


    # ------------------------------------------------------------
    # INTERNATIONAL TRADE
    # ------------------------------------------------------------

    trade_terms = [

        "wto",
        "world trade organization",
        "trade deficit",
        "trade imbalance",
        "bilateral trade",
        "trade pact",
        "trade agreement",
        "trade talks",
        "exports",
        "export growth",
        "imports",
        "import growth",
        "tariff",
        "india china",
        "india us trade",
        "india usa trade",
        "international trade",
    ]


    if any(
        term in headline
        for term in trade_terms
    ):

        return "INTERNATIONAL_TRADE"


    # ------------------------------------------------------------
    # MACRO ECONOMY
    # ------------------------------------------------------------

    macro_terms = [

        "inflation",
        "crude oil",
        "oil prices",
        "oil price",
        "oil spike",
        "rupee",
        "currency",
        "unemployment",
        "jobless rate",
        "employment data",
        "gdp",
        "economic growth",
        "economic activity",
        "economy",
    ]


    if any(
        term in headline
        for term in macro_terms
    ):

        return "MACRO_ECONOMY"


    # ------------------------------------------------------------
    # GOVERNMENT POLICY
    # ------------------------------------------------------------

    policy_terms = [

        "government policy",
        "government scheme",
        "government programme",
        "government program",
        "ministry",
        "subsidy",
        "regulation",
        "regulatory",
        "mandate",
        "policy reform",
        "policy change",
        "policy changes",
    ]


    if any(
        term in headline
        for term in policy_terms
    ):

        return "GOVERNMENT_POLICY"


    # ------------------------------------------------------------
    # GENERAL BUSINESS
    # ------------------------------------------------------------

    business_terms = [

        "company",
        "companies",
        "investment",
        "invest",
        "manufacturing",
        "industry",
        "industrial",
        "automobile",
        "automotive",
        "infrastructure",
        "real estate",
        "pharma",
        "technology",
        "defence",
        "defense",
        "aerospace",
        "hospitality",
        "dealer",
        "dealers",
        "order",
        "programme",
        "program",
        "developments",
    ]


    if any(
        term in headline
        for term in business_terms
    ):

        return "GENERAL_BUSINESS"


    # ------------------------------------------------------------
    # BODY FALLBACK
    # ------------------------------------------------------------

    combined = " ".join([
        summary,
        article,
        topics,
    ])


    if (
        agri == "HIGH"
        and
        any(
            term in combined
            for term in core_agri_headline
        )
    ):

        return "CORE_AGRICULTURE"


    if any(
        term in combined
        for term in agri_tech_terms
    ):

        return "AGRI_TECH"


    if any(
        term in combined
        for term in rural_terms
    ):

        return "RURAL_ECONOMY"


    if any(
        term in combined
        for term in trade_terms
    ):

        return "INTERNATIONAL_TRADE"


    if any(
        term in combined
        for term in macro_terms
    ):

        return "MACRO_ECONOMY"


    if any(
        term in combined
        for term in finance_terms
    ):

        return "BANKING_FINANCE"


    if any(
        term in combined
        for term in policy_terms
    ):

        return "GOVERNMENT_POLICY"


    if any(
        term in combined
        for term in agribusiness_terms
    ):

        return "AGRIBUSINESS"


    return "GENERAL_BUSINESS"


# ================================================================
# SECONDARY CATEGORIES
# ================================================================

def determine_secondary_categories(
    record,
    primary_category
):

    headline = normalize_text(
        get_headline(record)
    )

    text = get_subject_text(
        record
    )

    categories = []


    # ------------------------------------------------------------
    # Agriculture
    # ------------------------------------------------------------

    agriculture_terms = [

        "agriculture",
        "agricultural",
        "farmer",
        "farmers",
        "farming",
        "crop",
        "crops",
        "kharif",
        "rabi",
        "rice",
        "wheat",
        "maize",
        "soybean",
        "oilseed",
        "fertilizer",
        "fertiliser",
        "drought",
        "ethanol",
        "edible oil",
        "cooking oil",
    ]


    if any(
        term in text
        for term in agriculture_terms
    ):

        categories.append(
            "CORE_AGRICULTURE"
        )


    # ------------------------------------------------------------
    # Banking
    # ------------------------------------------------------------

    finance_terms = [

        "rbi",
        "npci",
        "upi",
        "mdr",
        "ipo",
        "nifty",
        "sensex",
        "banking",
        "bank",
        "financial market",
        "capital market",
        "bofa",
    ]


    if any(
        term in headline
        for term in finance_terms
    ):

        categories.append(
            "BANKING_FINANCE"
        )


    # ------------------------------------------------------------
    # Trade
    # ------------------------------------------------------------

    trade_terms = [

        "wto",
        "trade deficit",
        "trade imbalance",
        "exports",
        "imports",
        "tariff",
        "trade pact",
        "trade agreement",
        "india china",
        "bilateral trade",
    ]


    if any(
        term in headline
        for term in trade_terms
    ):

        categories.append(
            "INTERNATIONAL_TRADE"
        )


    # ------------------------------------------------------------
    # Macro
    # ------------------------------------------------------------

    macro_terms = [

        "crude oil",
        "oil price",
        "oil prices",
        "oil spike",
        "rupee",
        "inflation",
        "unemployment",
        "jobless rate",
        "gdp",
        "economic growth",
    ]


    if any(
        term in headline
        for term in macro_terms
    ):

        categories.append(
            "MACRO_ECONOMY"
        )


    # ------------------------------------------------------------
    # Government policy
    # ------------------------------------------------------------

    policy_terms = [

        "government",
        "ministry",
        "scheme",
        "policy",
        "regulation",
        "subsidy",
    ]


    if any(
        term in headline
        for term in policy_terms
    ):

        categories.append(
            "GOVERNMENT_POLICY"
        )


    # ------------------------------------------------------------
    # Remove primary category.
    # A category cannot be both primary and secondary.
    # ------------------------------------------------------------

    categories = [
        category
        for category in categories
        if category != primary_category
    ]


    # Remove duplicates while preserving order.

    result = []

    for category in categories:

        if category not in result:

            result.append(
                category
            )

    return result


# ================================================================
# AGRICULTURE CONNECTION
# ================================================================

def agriculture_connection(record):

    relevance = get_agri_relevance(
        record
    )

    if relevance == "HIGH":
        return "DIRECT"

    if relevance == "MEDIUM":
        return "INDIRECT"

    if relevance == "LOW":
        return "CONTEXTUAL"

    return "NONE"


# ================================================================
# INTELLIGENCE TYPE
# ================================================================

def intelligence_type(
    record,
    primary_category
):

    agri = agriculture_connection(
        record
    )


    core_categories = {

        "CORE_AGRICULTURE",
        "AGRIBUSINESS",
        "RURAL_ECONOMY",
        "AGRI_TECH",
        "BANKING_FINANCE",
        "INTERNATIONAL_TRADE",
        "MACRO_ECONOMY",
        "GOVERNMENT_POLICY",
    }


    if (
        primary_category
        in core_categories
    ):

        return "CORE_INTELLIGENCE"


    if agri in [
        "DIRECT",
        "INDIRECT",
    ]:

        return "CORE_INTELLIGENCE"


    return "PLACEMENT_INTELLIGENCE"


# ================================================================
# PLACEMENT RELEVANCE
# ================================================================

def placement_relevance(
    record,
    primary_category
):

    content_type = get_content_type(
        record
    )

    quality = get_source_quality(
        record
    )


    if primary_category in [

        "CORE_AGRICULTURE",
        "AGRIBUSINESS",
        "RURAL_ECONOMY",
        "BANKING_FINANCE",
        "INTERNATIONAL_TRADE",
        "MACRO_ECONOMY",
        "GOVERNMENT_POLICY",
        "AGRI_TECH",

    ]:

        return "HIGH"


    if primary_category == "GENERAL_BUSINESS":

        if (
            content_type == "ARTICLE"
            and
            quality == "HIGH"
        ):

            return "MEDIUM"

        return "LOW"


    return "NONE"


# ================================================================
# DUPLICATE ENGINE
#
# V2.2 engine retained intentionally.
# ================================================================

EVENT_SIGNATURES = [

    (
        "TATA_SONS_RBI_LISTING",
        [
            {"tata sons", "rbi"},
            {"tata sons", "listing"},
            {"rbi", "listing"},
        ]
    ),

    (
        "UPI_MDR",
        [
            {"upi", "mdr"},
            {"upi", "merchant discount rate"},
            {"upi", "person to merchant"},
        ]
    ),

    (
        "OIL_RUPEE_NIFTY",
        [
            {"oil spike", "rupee"},
            {"crude oil", "rupee"},
            {"crude oil", "nifty"},
            {"oil prices", "rupee"},
        ]
    ),

    (
        "RICE_ETHANOL_WTO",
        [
            {"rice", "ethanol"},
            {"rice", "wto", "ethanol"},
        ]
    ),

    (
        "DROUGHT_KHARIF",
        [
            {"drought", "kharif"},
            {"drought", "crops"},
        ]
    ),

    (
        "COOKING_OIL_IMPORTS",
        [
            {"cooking oil", "imports"},
            {"edible oil", "imports"},
        ]
    ),

]


def headline_contains_all(
    headline,
    terms
):

    normalized = normalize_text(
        headline
    )

    return all(
        normalize_text(term)
        in normalized
        for term in terms
    )


def get_event_signature(record):

    headline = get_headline(
        record
    )


    for signature_name, patterns in EVENT_SIGNATURES:

        for pattern in patterns:

            if headline_contains_all(
                headline,
                pattern
            ):

                return signature_name


    return None


def duplicate_match(
    record_a,
    record_b
):

    if (
        record_a.get("newspaper")
        !=
        record_b.get("newspaper")
    ):

        return False, ""


    if (
        is_package(record_a)
        or
        is_package(record_b)
    ):

        return False, ""


    headline_a = normalize_text(
        get_headline(record_a)
    )

    headline_b = normalize_text(
        get_headline(record_b)
    )


    if headline_a == headline_b:

        return (
            True,
            "Exact normalized headline."
        )


    event_a = get_event_signature(
        record_a
    )

    event_b = get_event_signature(
        record_b
    )


    if (
        event_a is not None
        and
        event_a == event_b
    ):

        return (
            True,
            f"Same specific event signature: "
            f"{event_a}"
        )


    tokens_a = headline_tokens(
        record_a
    )

    tokens_b = headline_tokens(
        record_b
    )


    if not tokens_a or not tokens_b:

        return False, ""


    intersection = (
        tokens_a
        &
        tokens_b
    )

    union = (
        tokens_a
        |
        tokens_b
    )


    jaccard = (
        len(intersection)
        /
        len(union)
    )


    smaller = min(
        len(tokens_a),
        len(tokens_b)
    )


    containment = (
        len(intersection)
        /
        smaller
    )


    if (
        jaccard >= 0.78
        and
        containment >= 0.90
    ):

        return (
            True,
            "Very high headline similarity."
        )


    return False, ""


# ================================================================
# CHOOSE PRIMARY DUPLICATE RECORD
# ================================================================

def choose_primary(
    record_a,
    record_b
):

    score_a = 0
    score_b = 0


    type_a = get_content_type(
        record_a
    )

    type_b = get_content_type(
        record_b
    )


    quality_a = get_source_quality(
        record_a
    )

    quality_b = get_source_quality(
        record_b
    )


    if type_a == "ARTICLE":
        score_a += 100

    elif type_a == "SNIPPET":
        score_a += 20


    if type_b == "ARTICLE":
        score_b += 100

    elif type_b == "SNIPPET":
        score_b += 20


    quality_scores = {
        "HIGH": 30,
        "MEDIUM": 15,
        "LOW": 0,
    }


    score_a += quality_scores.get(
        quality_a,
        0
    )

    score_b += quality_scores.get(
        quality_b,
        0
    )


    score_a += min(
        len(
            get_article_text(record_a)
        ) / 1000,
        10
    )

    score_b += min(
        len(
            get_article_text(record_b)
        ) / 1000,
        10
    )


    if score_a >= score_b:

        return (
            record_a,
            record_b
        )

    return (
        record_b,
        record_a
    )


# ================================================================
# LOAD INPUT
# ================================================================

print("=" * 78)
print("AGRICULTURE INTELLIGENCE SYSTEM")
print("CURATION + DEDUPLICATION V2.3")
print("=" * 78)

print(
    f"Input directory : {INPUT_DIR}"
)

print(
    f"Output directory: {OUTPUT_DIR}"
)

print()


input_files = sorted(
    INPUT_DIR.glob(
        "*_final.json"
    )
)

input_files = [
    path
    for path in input_files
    if path.name
    !=
    "ALL_FINAL_INTELLIGENCE_v1.json"
]


if not input_files:

    print(
        "ERROR: No final intelligence "
        "files found."
    )

    raise SystemExit(1)


all_records = []


for file_path in input_files:

    print(
        f"Loading: {file_path.name}"
    )


    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    if isinstance(
        data,
        list
    ):

        records = data

    elif isinstance(
        data,
        dict
    ):

        records = data.get(
            "records",
            []
        )

    else:

        records = []


    for record in records:

        record[
            "_input_file"
        ] = file_path.name

        all_records.append(
            record
        )


print()

print(
    f"Total input records: "
    f"{len(all_records)}"
)

print()


# ================================================================
# STEP 1
# ================================================================

print("=" * 78)
print("STEP 1: SUBJECT + RELEVANCE CLASSIFICATION")
print("=" * 78)


for record in all_records:

    primary = classify_primary_category(
        record
    )

    secondary = determine_secondary_categories(
        record,
        primary
    )

    agri = agriculture_connection(
        record
    )

    placement = placement_relevance(
        record,
        primary
    )

    intel_type = intelligence_type(
        record,
        primary
    )


    record[
        "_curation"
    ] = {

        "primary_category":
            primary,

        "secondary_categories":
            secondary,

        "agriculture_connection":
            agri,

        "placement_relevance":
            placement,

        "intelligence_type":
            intel_type,

        "status":
            "PENDING",

        "reason":
            "",

        "duplicate_of":
            None,

        "primary_record":
            True,
    }


    print(
        get_headline(record)
    )

    print(
        f"  Primary       : {primary}"
    )

    print(
        f"  Secondary     : "
        f"{', '.join(secondary) if secondary else 'NONE'}"
    )

    print(
        f"  Agriculture   : {agri}"
    )

    print(
        f"  Intelligence  : {intel_type}"
    )

    print(
        f"  Placement     : {placement}"
    )

    print()


# ================================================================
# STEP 2: SCOPE FILTER
# ================================================================

print("=" * 78)
print("STEP 2: SCOPE FILTER")
print("=" * 78)


for record in all_records:

    headline = get_headline(
        record
    )


    if is_obviously_irrelevant(
        record
    ):

        record[
            "_curation"
        ][
            "primary_category"
        ] = "IRRELEVANT"


        record[
            "_curation"
        ][
            "status"
        ] = "REMOVE"


        record[
            "_curation"
        ][
            "reason"
        ] = (
            "Clearly outside the defined "
            "agriculture, rural economy, "
            "business, finance and placement "
            "intelligence scope."
        )


        print(
            f"REMOVE | {headline}"
        )

        continue


    if is_package(record):

        record[
            "_curation"
        ][
            "status"
        ] = "REVIEW"


        record[
            "_curation"
        ][
            "reason"
        ] = (
            "Newspaper package/section headline. "
            "Requires manual review."
        )


        print(
            f"REVIEW | PACKAGE | {headline}"
        )


print()


# ================================================================
# STEP 3: DUPLICATES
# ================================================================

print("=" * 78)
print("STEP 3: CONSERVATIVE DUPLICATE DETECTION")
print("=" * 78)


duplicate_count = 0


for i in range(
    len(all_records)
):

    record_a = all_records[i]


    if record_a[
        "_curation"
    ][
        "status"
    ] in [
        "REMOVE",
        "DUPLICATE",
    ]:

        continue


    for j in range(
        i + 1,
        len(all_records)
    ):

        record_b = all_records[j]


        if record_b[
            "_curation"
        ][
            "status"
        ] in [
            "REMOVE",
            "DUPLICATE",
        ]:

            continue


        matched, reason = duplicate_match(
            record_a,
            record_b
        )


        if not matched:

            continue


        primary, duplicate = (
            choose_primary(
                record_a,
                record_b
            )
        )


        primary_id = (
            primary.get(
                "record_id",
                get_headline(primary)
            )
        )


        duplicate[
            "_curation"
        ][
            "status"
        ] = "DUPLICATE"


        duplicate[
            "_curation"
        ][
            "primary_record"
        ] = False


        duplicate[
            "_curation"
        ][
            "duplicate_of"
        ] = primary_id


        duplicate[
            "_curation"
        ][
            "reason"
        ] = reason


        duplicate_count += 1


        print(
            "DUPLICATE:"
        )

        print(
            f"  PRIMARY   : "
            f"{get_headline(primary)}"
        )

        print(
            f"  DUPLICATE : "
            f"{get_headline(duplicate)}"
        )

        print(
            f"  REASON    : "
            f"{reason}"
        )

        print()


print(
    f"Strict duplicates found: "
    f"{duplicate_count}"
)

print()


# ================================================================
# STEP 4: FINAL CURATION
# ================================================================

print("=" * 78)
print("STEP 4: FINAL CURATION")
print("=" * 78)


for record in all_records:

    curation = record[
        "_curation"
    ]

    status = curation[
        "status"
    ]


    if status in [
        "REMOVE",
        "DUPLICATE",
    ]:

        continue


    category = curation[
        "primary_category"
    ]

    agri = curation[
        "agriculture_connection"
    ]

    content_type = get_content_type(
        record
    )

    quality = get_source_quality(
        record
    )


    # ------------------------------------------------------------
    # PACKAGE
    # ------------------------------------------------------------

    if is_package(record):

        status = "REVIEW"

        reason = (
            "Package/section headline; "
            "not treated as a standalone story."
        )


    # ------------------------------------------------------------
    # CORE AGRICULTURE
    # ------------------------------------------------------------

    elif category == "CORE_AGRICULTURE":

        status = "KEEP"

        reason = (
            "Direct agriculture-related story."
        )


    elif category == "AGRIBUSINESS":

        status = "KEEP"

        reason = (
            "Direct agribusiness/agricultural "
            "supply-chain story."
        )


    elif category == "AGRI_TECH":

        status = "KEEP"

        reason = (
            "Direct agricultural technology story."
        )


    elif category == "RURAL_ECONOMY":

        status = "KEEP"

        reason = (
            "Relevant rural-economy development."
        )


    # ------------------------------------------------------------
    # BANKING
    # ------------------------------------------------------------

    elif category == "BANKING_FINANCE":

        if (
            content_type == "ARTICLE"
            and
            quality in [
                "HIGH",
                "MEDIUM",
            ]
        ):

            status = "KEEP"

            reason = (
                "Meaningful banking/finance "
                "story useful for placement/GD."
            )

        elif agri in [
            "DIRECT",
            "INDIRECT",
        ]:

            status = "KEEP"

            reason = (
                "Finance story with meaningful "
                "agriculture/rural relevance."
            )

        else:

            status = "REVIEW"

            reason = (
                "Finance story needs manual "
                "assessment."
            )


    # ------------------------------------------------------------
    # INTERNATIONAL TRADE
    # ------------------------------------------------------------

    elif category == "INTERNATIONAL_TRADE":

        if agri in [
            "DIRECT",
            "INDIRECT",
        ]:

            status = "KEEP"

            reason = (
                "Trade development with meaningful "
                "agriculture/rural relevance."
            )

        elif (
            content_type == "ARTICLE"
            and
            quality == "HIGH"
        ):

            status = "KEEP"

            reason = (
                "High-quality international trade "
                "story useful for placement/GD."
            )

        else:

            status = "REVIEW"

            reason = (
                "Trade story requires manual "
                "placement relevance review."
            )


    # ------------------------------------------------------------
    # MACRO
    # ------------------------------------------------------------

    elif category == "MACRO_ECONOMY":

        if agri in [
            "DIRECT",
            "INDIRECT",
        ]:

            status = "KEEP"

            reason = (
                "Macro development with meaningful "
                "agriculture/rural implications."
            )

        elif (
            content_type == "ARTICLE"
            and
            quality == "HIGH"
        ):

            status = "KEEP"

            reason = (
                "High-quality macro-economic story "
                "useful for placement/GD."
            )

        else:

            status = "REVIEW"

            reason = (
                "Macro story requires manual review."
            )


    # ------------------------------------------------------------
    # GOVERNMENT POLICY
    # ------------------------------------------------------------

    elif category == "GOVERNMENT_POLICY":

        if agri in [
            "DIRECT",
            "INDIRECT",
        ]:

            status = "KEEP"

            reason = (
                "Government policy with meaningful "
                "agriculture/rural relevance."
            )

        else:

            status = "REVIEW"

            reason = (
                "Policy story requires relevance review."
            )


    # ------------------------------------------------------------
    # GENERAL BUSINESS
    # ------------------------------------------------------------

    elif category == "GENERAL_BUSINESS":

        if agri in [
            "DIRECT",
            "INDIRECT",
        ]:

            status = "KEEP"

            reason = (
                "Business development with meaningful "
                "agriculture/rural relevance."
            )

        elif (
            content_type == "ARTICLE"
            and
            quality == "HIGH"
        ):

            status = "KEEP"

            reason = (
                "High-quality business story with "
                "potential placement/GD value."
            )

        else:

            status = "REVIEW"

            reason = (
                "General business story requires "
                "manual review."
            )


    else:

        status = "REVIEW"

        reason = (
            "Relevance could not be established "
            "with sufficient confidence."
        )


    curation[
        "status"
    ] = status

    curation[
        "reason"
    ] = reason


    print(
        f"{status:<9} | "
        f"{get_headline(record)}"
    )


print()


# ================================================================
# PREPARE OUTPUT
# ================================================================

def prepare_output(record):

    output = dict(
        record
    )


    curation = record[
        "_curation"
    ]


    output[
        "curation"
    ] = {

        "primary_category":
            curation[
                "primary_category"
            ],

        "secondary_categories":
            curation[
                "secondary_categories"
            ],

        "agriculture_connection":
            curation[
                "agriculture_connection"
            ],

        "intelligence_type":
            curation[
                "intelligence_type"
            ],

        "placement_relevance":
            curation[
                "placement_relevance"
            ],

        "status":
            curation[
                "status"
            ],

        "reason":
            curation[
                "reason"
            ],

        "duplicate_of":
            curation[
                "duplicate_of"
            ],

        "primary_record":
            curation[
                "primary_record"
            ],
    }


    output.pop(
        "_curation",
        None
    )

    output.pop(
        "_input_file",
        None
    )


    return output


curated_records = []
review_records = []
removed_records = []
duplicate_records = []


for record in all_records:

    prepared = prepare_output(
        record
    )


    status = prepared[
        "curation"
    ][
        "status"
    ]


    if status == "KEEP":

        curated_records.append(
            prepared
        )

    elif status == "REVIEW":

        review_records.append(
            prepared
        )

    elif status == "REMOVE":

        removed_records.append(
            prepared
        )

    elif status == "DUPLICATE":

        duplicate_records.append(
            prepared
        )


# ================================================================
# SAVE FILES
# ================================================================

curated_path = (
    OUTPUT_DIR
    / "CURATED_INTELLIGENCE_v23.json"
)

review_path = (
    OUTPUT_DIR
    / "CURATION_REVIEW_QUEUE_v23.json"
)

removed_path = (
    OUTPUT_DIR
    / "REMOVED_RECORDS_v23.json"
)

duplicate_path = (
    OUTPUT_DIR
    / "DUPLICATE_RECORDS_v23.json"
)

report_path = (
    OUTPUT_DIR
    / "CURATION_REPORT_v23.txt"
)


with open(
    curated_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        curated_records,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    review_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        review_records,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    removed_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        removed_records,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    duplicate_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        duplicate_records,
        f,
        ensure_ascii=False,
        indent=2
    )


# ================================================================
# COUNTS
# ================================================================

category_counts = Counter()
agri_counts = Counter()
placement_counts = Counter()
intelligence_counts = Counter()


for record in curated_records:

    curation = record[
        "curation"
    ]


    category_counts[
        curation[
            "primary_category"
        ]
    ] += 1


    agri_counts[
        curation[
            "agriculture_connection"
        ]
    ] += 1


    placement_counts[
        curation[
            "placement_relevance"
        ]
    ] += 1


    intelligence_counts[
        curation[
            "intelligence_type"
        ]
    ] += 1


# ================================================================
# REPORT
# ================================================================

with open(
    report_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "AGRICULTURE INTELLIGENCE SYSTEM\n"
    )

    f.write(
        "CURATION + DEDUPLICATION V2.3\n"
    )

    f.write(
        "=" * 78
        + "\n\n"
    )


    f.write(
        "RECORD SUMMARY\n"
    )

    f.write(
        "-" * 78
        + "\n"
    )

    f.write(
        f"Input records : "
        f"{len(all_records)}\n"
    )

    f.write(
        f"Curated       : "
        f"{len(curated_records)}\n"
    )

    f.write(
        f"Review        : "
        f"{len(review_records)}\n"
    )

    f.write(
        f"Removed       : "
        f"{len(removed_records)}\n"
    )

    f.write(
        f"Duplicates    : "
        f"{len(duplicate_records)}\n\n"
    )


    f.write(
        "PRIMARY CATEGORIES\n"
    )

    f.write(
        "-" * 78
        + "\n"
    )


    for category, count in sorted(
        category_counts.items()
    ):

        f.write(
            f"{category:<25}"
            f"{count}\n"
        )


    f.write("\n")


    f.write(
        "INTELLIGENCE TYPE\n"
    )

    f.write(
        "-" * 78
        + "\n"
    )


    for category, count in sorted(
        intelligence_counts.items()
    ):

        f.write(
            f"{category:<25}"
            f"{count}\n"
        )


    f.write("\n")


    f.write(
        "AGRICULTURE CONNECTION\n"
    )

    f.write(
        "-" * 78
        + "\n"
    )


    for category, count in sorted(
        agri_counts.items()
    ):

        f.write(
            f"{category:<25}"
            f"{count}\n"
        )


    f.write("\n")


    f.write(
        "PLACEMENT RELEVANCE\n"
    )

    f.write(
        "-" * 78
        + "\n"
    )


    for category, count in sorted(
        placement_counts.items()
    ):

        f.write(
            f"{category:<25}"
            f"{count}\n"
        )


    # ============================================================
    # CURATED
    # ============================================================

    f.write(
        "\n"
        + "=" * 78
        + "\n"
    )

    f.write(
        "CURATED STORIES\n"
    )

    f.write(
        "=" * 78
        + "\n\n"
    )


    for i, record in enumerate(
        curated_records,
        1
    ):

        curation = record[
            "curation"
        ]


        f.write(
            f"[{i:02d}] "
            f"{get_headline(record)}\n"
        )

        f.write(
            f"     Newspaper    : "
            f"{record.get('newspaper', '')}\n"
        )

        f.write(
            f"     Page         : "
            f"{record.get('page', '')}\n"
        )

        f.write(
            f"     Primary      : "
            f"{curation['primary_category']}\n"
        )

        f.write(
            f"     Secondary    : "
            f"{', '.join(curation['secondary_categories']) or 'NONE'}\n"
        )

        f.write(
            f"     Intelligence : "
            f"{curation['intelligence_type']}\n"
        )

        f.write(
            f"     Agriculture  : "
            f"{curation['agriculture_connection']}\n"
        )

        f.write(
            f"     Placement    : "
            f"{curation['placement_relevance']}\n"
        )

        f.write(
            f"     Type         : "
            f"{get_content_type(record)}\n"
        )

        f.write(
            f"     Quality      : "
            f"{get_source_quality(record)}\n"
        )

        f.write(
            f"     Reason       : "
            f"{curation['reason']}\n"
        )

        f.write("\n")


    # ============================================================
    # REVIEW
    # ============================================================

    f.write(
        "=" * 78
        + "\n"
    )

    f.write(
        "MANUAL REVIEW QUEUE\n"
    )

    f.write(
        "=" * 78
        + "\n\n"
    )


    for i, record in enumerate(
        review_records,
        1
    ):

        curation = record[
            "curation"
        ]


        f.write(
            f"[{i:02d}] "
            f"{get_headline(record)}\n"
        )

        f.write(
            f"     Primary      : "
            f"{curation['primary_category']}\n"
        )

        f.write(
            f"     Intelligence : "
            f"{curation['intelligence_type']}\n"
        )

        f.write(
            f"     Agriculture  : "
            f"{curation['agriculture_connection']}\n"
        )

        f.write(
            f"     Placement    : "
            f"{curation['placement_relevance']}\n"
        )

        f.write(
            f"     Reason       : "
            f"{curation['reason']}\n"
        )

        f.write("\n")


    # ============================================================
    # DUPLICATES
    # ============================================================

    f.write(
        "=" * 78
        + "\n"
    )

    f.write(
        "DUPLICATES\n"
    )

    f.write(
        "=" * 78
        + "\n\n"
    )


    for i, record in enumerate(
        duplicate_records,
        1
    ):

        curation = record[
            "curation"
        ]


        f.write(
            f"[{i:02d}] "
            f"{get_headline(record)}\n"
        )

        f.write(
            f"     Duplicate of : "
            f"{curation['duplicate_of']}\n"
        )

        f.write(
            f"     Reason       : "
            f"{curation['reason']}\n"
        )

        f.write("\n")


# ================================================================
# FINAL OUTPUT
# ================================================================

print("=" * 78)
print("CURATION V2.3 COMPLETE")
print("=" * 78)

print(
    f"Input records       : "
    f"{len(all_records)}"
)

print(
    f"Curated records     : "
    f"{len(curated_records)}"
)

print(
    f"Manual review       : "
    f"{len(review_records)}"
)

print(
    f"Removed             : "
    f"{len(removed_records)}"
)

print(
    f"Duplicates          : "
    f"{len(duplicate_records)}"
)

print()

print(
    "Primary categories:"
)

for category, count in sorted(
    category_counts.items()
):

    print(
        f"  {category:<25}: "
        f"{count}"
    )


print()

print(
    "Intelligence type:"
)

for category, count in sorted(
    intelligence_counts.items()
):

    print(
        f"  {category:<25}: "
        f"{count}"
    )


print()

print(
    "Agriculture connection:"
)

for category, count in sorted(
    agri_counts.items()
):

    print(
        f"  {category:<25}: "
        f"{count}"
    )


print()

print(
    "Placement relevance:"
)

for category, count in sorted(
    placement_counts.items()
):

    print(
        f"  {category:<25}: "
        f"{count}"
    )


print()

print(
    "Output files:"
)

print(
    f"  {curated_path}"
)

print(
    f"  {review_path}"
)

print(
    f"  {removed_path}"
)

print(
    f"  {duplicate_path}"
)

print(
    f"  {report_path}"
)

print()

print("=" * 78)
print(
    "Inspect V2.3 before building "
    "the master database."
)
print("=" * 78)