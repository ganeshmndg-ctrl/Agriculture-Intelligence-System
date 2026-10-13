import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "grouped_all_articles_v4"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "hybrid_articles_v3"
)

MODEL_NAME = "gemini-3.1-flash-lite"

# None = process every candidate
MAX_ARTICLES_PER_NEWSPAPER = None

# Gemini free-tier safety margin.
# 6 seconds = 10 requests/minute.
REQUEST_INTERVAL_SECONDS = 6

MAX_RETRIES = 4

RETRY_DELAYS = [
    15,
    30,
    60,
    120
]


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
        "GEMINI_API_KEY was not found.\n"
        "Make sure .env exists in the project root."
    )


client = genai.Client(
    api_key=API_KEY
)


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(data, path):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with open(
        temporary_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    # Atomic replacement.
    temporary_path.replace(
        path
    )


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(text):

    if text is None:
        return ""

    return " ".join(
        str(text).split()
    )


def looks_like_garbage(text):

    text = clean_text(
        text
    )

    if not text:
        return True

    simplified = "".join(
        ch.lower()
        for ch in text
        if ch.isalnum()
    )

    if len(simplified) >= 20:

        unique_chars = set(
            simplified
        )

        if len(unique_chars) <= 2:
            return True

        most_common = max(
            simplified.count(ch)
            for ch in unique_chars
        )

        if (
            most_common
            / len(simplified)
            >= 0.95
        ):

            return True

    return False


def safe_float(
    value,
    default=0.0
):

    try:
        return float(value)

    except Exception:
        return default


# ============================================================
# ARTICLE IDENTIFICATION
# ============================================================

def candidate_key(
    newspaper_name,
    candidate
):

    page = candidate.get(
        "page",
        ""
    )

    headline = clean_text(
        candidate.get(
            "headline",
            ""
        )
    ).lower()

    headline_block = candidate.get(
        "headline_block",
        ""
    )

    # Prefer stable source identifiers.
    if headline_block is not None:

        headline_block = str(
            headline_block
        )

    return (
        f"{newspaper_name}"
        f"__PAGE_{page}"
        f"__BLOCK_{headline_block}"
        f"__HEADLINE_{headline}"
    )


# ============================================================
# FLATTEN V4 STRUCTURE
# ============================================================

def flatten_v4_articles(data):

    flattened = []

    if not isinstance(
        data,
        list
    ):

        return flattened

    for page_record in data:

        if not isinstance(
            page_record,
            dict
        ):

            continue

        page_number = page_record.get(
            "page"
        )

        articles = page_record.get(
            "articles",
            []
        )

        if not isinstance(
            articles,
            list
        ):

            continue

        for article in articles:

            if not isinstance(
                article,
                dict
            ):

                continue

            article_copy = dict(
                article
            )

            if not article_copy.get(
                "page"
            ):

                article_copy[
                    "page"
                ] = page_number

            flattened.append(
                article_copy
            )

    return flattened


# ============================================================
# RESPONSE SCHEMA
# ============================================================

RESPONSE_SCHEMA = {

    "type": "OBJECT",

    "properties": {

        "keep": {
            "type": "BOOLEAN"
        },

        "content_type": {
            "type": "STRING",

            "enum": [
                "ARTICLE",
                "SNIPPET",
                "FACT_BOX",
                "TABLE",
                "ADVERTISEMENT",
                "PAGE_FURNITURE",
                "CAPTION",
                "DUPLICATE",
                "UNCLEAR"
            ]
        },

        "clean_headline": {
            "type": "STRING"
        },

        "subheadline": {
            "type": "STRING"
        },

        "article_text": {
            "type": "STRING"
        },

        "source_quality": {
            "type": "STRING",

            "enum": [
                "GOOD",
                "PARTIAL",
                "INSUFFICIENT",
                "UNCLEAR"
            ]
        },

        "needs_review": {
            "type": "BOOLEAN"
        },

        "topics": {
            "type": "ARRAY",

            "items": {
                "type": "STRING",

                "enum": [
                    "AGRICULTURE",
                    "BANKING_FINANCE",
                    "ECONOMY_BUSINESS",
                    "INTERNATIONAL",
                    "GOVERNMENT_POLICY",
                    "COMMODITIES",
                    "TRADE",
                    "MARKETS",
                    "AGRI_TECH",
                    "FOOD_PROCESSING",
                    "SUPPLY_CHAIN",
                    "RURAL_DEVELOPMENT",
                    "SCIENCE_TECH",
                    "ENERGY",
                    "EMPLOYMENT",
                    "ENVIRONMENT",
                    "OTHER_RELEVANT",
                    "NONE"
                ]
            }
        },

        "agriculture_relevance": {
            "type": "STRING",

            "enum": [
                "HIGH",
                "MEDIUM",
                "LOW",
                "NONE"
            ]
        },

        "agriculture_relevance_reason": {
            "type": "STRING"
        },

        "reported_facts": {
            "type": "ARRAY",

            "items": {
                "type": "STRING"
            }
        },

        "interpretations": {
            "type": "ARRAY",

            "items": {
                "type": "STRING"
            }
        },

        "key_facts": {
            "type": "ARRAY",

            "items": {
                "type": "STRING"
            }
        },

        "key_numbers": {
            "type": "ARRAY",

            "items": {
                "type": "STRING"
            }
        },

        "agriculture_impact": {
            "type": "STRING"
        },

        "why_it_matters": {
            "type": "STRING"
        },

        "connections": {
            "type": "ARRAY",

            "items": {
                "type": "STRING"
            }
        },

        "government_schemes": {

            "type": "ARRAY",

            "items": {

                "type": "OBJECT",

                "properties": {

                    "scheme_name": {
                        "type": "STRING"
                    },

                    "event_type": {

                        "type": "STRING",

                        "enum": [
                            "NEW_SCHEME",
                            "UPDATE",
                            "FUNDING",
                            "BENEFICIARY_UPDATE",
                            "PERFORMANCE",
                            "ELIGIBILITY",
                            "STATE_IMPLEMENTATION",
                            "IMPLEMENTATION",
                            "ANNOUNCEMENT",
                            "OTHER"
                        ]
                    },

                    "details": {
                        "type": "STRING"
                    }
                },

                "required": [
                    "scheme_name",
                    "event_type",
                    "details"
                ]
            }
        }
    },

    "required": [
        "keep",
        "content_type",
        "clean_headline",
        "subheadline",
        "article_text",
        "source_quality",
        "needs_review",
        "topics",
        "agriculture_relevance",
        "agriculture_relevance_reason",
        "reported_facts",
        "interpretations",
        "key_facts",
        "key_numbers",
        "agriculture_impact",
        "why_it_matters",
        "connections",
        "government_schemes"
    ]
}


# ============================================================
# GEMINI SYSTEM INSTRUCTION
# ============================================================

SYSTEM_INSTRUCTION = """

You are the editorial intelligence engine for a newspaper-based
Agriculture, Business and Placement Preparation system.

The input is ONE PRELIMINARY NEWS CANDIDATE extracted from a
newspaper PDF.

Your task is to determine what this candidate actually represents
and extract useful intelligence from it.

============================================================
CONTENT TYPES
============================================================

ARTICLE:
A meaningful news article with enough body text.

SNIPPET:
A legitimate short news item where the extracted text is incomplete.

FACT_BOX:
Supporting facts or claims presented separately from the main article.

TABLE:
Primarily numerical/table content.

ADVERTISEMENT:
Commercial or promotional material.

PAGE_FURNITURE:
Page navigation, section labels, page numbers, repeated headers,
newspaper branding, etc.

CAPTION:
Image/photo caption.

DUPLICATE:
A repeated representation of another story.

UNCLEAR:
Cannot determine reliably.

============================================================
SOURCE FIDELITY
============================================================

Use ONLY the supplied candidate.

Do not use outside knowledge to reconstruct missing text.

Never invent:

- facts
- statistics
- names
- dates
- causes
- quotes
- schemes
- policy details

If information is incomplete, classify it as SNIPPET or UNCLEAR.

============================================================
PDF EXTRACTION
============================================================

The source may contain PDF extraction artifacts.

Ignore meaningless repeated characters or obvious garbage.

Do not use extraction garbage as article text.

Do not combine this candidate with a neighbouring story.

============================================================
HEADLINE
============================================================

The clean_headline must correspond to the SAME story as the
source headline.

Do not replace the headline with a neighbouring story.

Clean only obvious OCR/PDF errors.

============================================================
ARTICLE TEXT
============================================================

Use only genuine text belonging to this candidate.

If only a headline is available, preserve the headline and classify
as SNIPPET if it is clearly a legitimate news item.

Do not invent missing body text.

============================================================
TOPICS
============================================================

Use all relevant topics.

Possible topics:

AGRICULTURE
BANKING_FINANCE
ECONOMY_BUSINESS
INTERNATIONAL
GOVERNMENT_POLICY
COMMODITIES
TRADE
MARKETS
AGRI_TECH
FOOD_PROCESSING
SUPPLY_CHAIN
RURAL_DEVELOPMENT
SCIENCE_TECH
ENERGY
EMPLOYMENT
ENVIRONMENT
OTHER_RELEVANT

An article may have several topics.

============================================================
AGRICULTURE RELEVANCE
============================================================

HIGH:
Direct agriculture/farmer/crop/food/agricultural-policy relevance.

MEDIUM:
Meaningful indirect agricultural or rural-economy connection.

LOW:
General economy, banking, currency, oil, trade, logistics etc.
that may indirectly affect agriculture.

NONE:
No meaningful agriculture connection.

Do not force agricultural relevance.

============================================================
GOVERNMENT INTELLIGENCE
============================================================

Extract schemes, programmes, policies, regulations or government
initiatives only when explicitly mentioned in the candidate.

A mention of an existing scheme is NOT automatically a new scheme.

Use:

NEW_SCHEME
UPDATE
FUNDING
BENEFICIARY_UPDATE
PERFORMANCE
ELIGIBILITY
STATE_IMPLEMENTATION
IMPLEMENTATION
ANNOUNCEMENT
OTHER

If no relevant government initiative is mentioned, return [].

============================================================
INTERPRETATIONS
============================================================

Interpretations must be clearly distinguishable from reported facts.

Do not invent causal relationships that are not supported by the
article.

Use cautious language where the article itself is uncertain.

============================================================
CONNECTIONS
============================================================

Record useful connections stated or reasonably supported by THIS
candidate.

Do not create connections using outside information.

These are not placement questions.

============================================================
IMPORTANT
============================================================

DO NOT GENERATE GD QUESTIONS.

DO NOT GENERATE INTERVIEW QUESTIONS.

DO NOT GENERATE PLACEMENT QUESTIONS.

The system will use the information itself for later revision.

============================================================
QUALITY RULE
============================================================

Be conservative.

If the candidate is a legitimate useful news snippet, keep it.

If it is clearly advertisement/page furniture/table/caption,
discard it.

If uncertain, set needs_review = true.

Do not manufacture completeness.
"""


# ============================================================
# PREPARE CANDIDATE
# ============================================================

def prepare_candidate(article):

    blocks = article.get(
        "blocks",
        []
    )

    prepared_blocks = []

    if not isinstance(
        blocks,
        list
    ):

        return prepared_blocks

    for block in blocks:

        if not isinstance(
            block,
            dict
        ):

            continue

        text = clean_text(
            block.get(
                "text",
                ""
            )
        )

        if looks_like_garbage(
            text
        ):

            continue

        prepared_blocks.append({

            "block_id": block.get(
                "block_id"
            ),

            "role": block.get(
                "role",
                ""
            ),

            "x0": safe_float(
                block.get(
                    "x0",
                    0
                )
            ),

            "y0": safe_float(
                block.get(
                    "y0",
                    0
                )
            ),

            "x1": safe_float(
                block.get(
                    "x1",
                    0
                )
            ),

            "y1": safe_float(
                block.get(
                    "y1",
                    0
                )
            ),

            "text": text
        })

    return prepared_blocks


# ============================================================
# GEMINI ANALYSIS
# ============================================================

def analyze_candidate(
    candidate,
    newspaper_name
):

    source_headline = clean_text(
        candidate.get(
            "headline",
            ""
        )
    )

    page = candidate.get(
        "page"
    )

    blocks = prepare_candidate(
        candidate
    )

    prompt = f"""

NEWSPAPER:
{newspaper_name}

PAGE:
{page}

SOURCE HEADLINE:
{source_headline}

SOURCE ARTICLE TEXT:
{clean_text(
    candidate.get(
        "full_article_text",
        ""
    )
)}

SOURCE BLOCK COUNT:
{candidate.get(
    "block_count",
    0
)}

SOURCE BODY BLOCK COUNT:
{candidate.get(
    "body_block_count",
    0
)}

PRELIMINARY BLOCKS:
"""

    for index, block in enumerate(
        blocks,
        start=1
    ):

        prompt += f"""

--- BLOCK {index} ---

BLOCK ID:
{block["block_id"]}

ROLE:
{block["role"]}

X0:
{block["x0"]}

Y0:
{block["y0"]}

X1:
{block["x1"]}

Y1:
{block["y1"]}

TEXT:
{block["text"]}
"""

    prompt += """

Analyse this candidate now.

IMPORTANT:

The source headline and source article text belong to this
candidate, but PDF extraction can be incomplete or contain
artifacts.

Do not replace this story with a neighbouring story.

Do not use outside knowledge.

Do not generate questions.

Return the structured JSON response.
"""

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
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        temperature=0.1
                    )
                )
            )

            if not response.text:

                raise ValueError(
                    "Empty Gemini response."
                )

            return json.loads(
                response.text
            )

        except Exception as error:

            last_error = error

            print()
            print(
                f"Gemini attempt "
                f"{attempt}/"
                f"{MAX_RETRIES} failed:"
            )

            print(
                str(error)
            )

            if attempt < MAX_RETRIES:

                delay = RETRY_DELAYS[
                    min(
                        attempt - 1,
                        len(
                            RETRY_DELAYS
                        ) - 1
                    )
                ]

                print(
                    f"Waiting "
                    f"{delay} seconds "
                    f"before retry..."
                )

                time.sleep(
                    delay
                )

    # --------------------------------------------------------
    # Failed candidate fallback
    # --------------------------------------------------------

    return {

        "keep": True,

        "content_type": "UNCLEAR",

        "clean_headline": source_headline,

        "subheadline": "",

        "article_text": clean_text(
            candidate.get(
                "full_article_text",
                ""
            )
        ),

        "source_quality": "UNCLEAR",

        "needs_review": True,

        "topics": [
            "NONE"
        ],

        "agriculture_relevance": "NONE",

        "agriculture_relevance_reason": "",

        "reported_facts": [],

        "interpretations": [],

        "key_facts": [],

        "key_numbers": [],

        "agriculture_impact": "",

        "why_it_matters": "",

        "connections": [],

        "government_schemes": [],

        "_analysis_error": str(
            last_error
        )
    }


# ============================================================
# NORMALIZE RESULT
# ============================================================

def normalize_result(
    result
):

    if not isinstance(
        result,
        dict
    ):

        result = {}

    array_fields = [

        "topics",

        "reported_facts",

        "interpretations",

        "key_facts",

        "key_numbers",

        "connections",

        "government_schemes"
    ]

    for field in array_fields:

        if not isinstance(
            result.get(field),
            list
        ):

            result[field] = []

    if not result.get(
        "topics"
    ):

        result[
            "topics"
        ] = [
            "NONE"
        ]

    if not result.get(
        "content_type"
    ):

        result[
            "content_type"
        ] = "UNCLEAR"

    if not result.get(
        "source_quality"
    ):

        result[
            "source_quality"
        ] = "UNCLEAR"

    if not result.get(
        "agriculture_relevance"
    ):

        result[
            "agriculture_relevance"
        ] = "NONE"

    result[
        "keep"
    ] = bool(
        result.get(
            "keep",
            False
        )
    )

    result[
        "needs_review"
    ] = bool(
        result.get(
            "needs_review",
            True
        )
    )

    return result


# ============================================================
# LOAD EXISTING RESULTS FOR RESUME
# ============================================================

def load_existing_results(
    output_file
):

    if not output_file.exists():

        return []

    try:

        data = load_json(
            output_file
        )

        if not isinstance(
            data,
            list
        ):

            print(
                "WARNING: Existing output "
                "is not a list."
            )

            return []

        return data

    except Exception as error:

        print(
            "WARNING: Could not load "
            "existing output:"
        )

        print(
            str(error)
        )

        return []


def build_existing_keys(
    results,
    newspaper_name
):

    keys = set()

    for record in results:

        if not isinstance(
            record,
            dict
        ):

            continue

        page = record.get(
            "page",
            ""
        )

        headline = clean_text(
            record.get(
                "source_headline",
                ""
            )
        ).lower()

        headline_block = record.get(
            "source_headline_block",
            ""
        )

        key = (
            f"{newspaper_name}"
            f"__PAGE_{page}"
            f"__BLOCK_{headline_block}"
            f"__HEADLINE_{headline}"
        )

        keys.add(
            key
        )

    return keys


# ============================================================
# PROCESS NEWSPAPER
# ============================================================

def process_newspaper(
    input_file
):

    print()
    print("=" * 90)

    print(
        input_file.stem
    )

    print("=" * 90)

    raw_data = load_json(
        input_file
    )

    candidates = (
        flatten_v4_articles(
            raw_data
        )
    )

    newspaper_name = (
        input_file.stem
    )

    output_file = (
        OUTPUT_DIR
        / (
            input_file.stem
            + "_hybrid_v3.json"
        )
    )

    existing_results = (
        load_existing_results(
            output_file
        )
    )

    existing_keys = (
        build_existing_keys(
            existing_results,
            newspaper_name
        )
    )

    print(
        f"Flattened candidates : "
        f"{len(candidates)}"
    )

    print(
        f"Existing results     : "
        f"{len(existing_results)}"
    )

    remaining = []

    for candidate in candidates:

        key = candidate_key(
            newspaper_name,
            candidate
        )

        if key in existing_keys:

            continue

        remaining.append(
            candidate
        )

    if (
        MAX_ARTICLES_PER_NEWSPAPER
        is not None
    ):

        remaining = remaining[
            :MAX_ARTICLES_PER_NEWSPAPER
        ]

    print(
        f"Already analyzed     : "
        f"{len(candidates) - len(remaining)}"
    )

    print(
        f"Remaining to analyze : "
        f"{len(remaining)}"
    )

    if not remaining:

        print(
            "Nothing new to analyze."
        )

        return existing_results

    results = list(
        existing_results
    )

    total = len(
        remaining
    )

    for index, candidate in enumerate(
        remaining,
        start=1
    ):

        page = candidate.get(
            "page"
        )

        headline = clean_text(
            candidate.get(
                "headline",
                ""
            )
        )

        print()
        print("-" * 90)

        print(
            f"[{index}/{total}]"
        )

        print(
            f"Page: {page}"
        )

        print(
            f"Headline: {headline}"
        )

        # ----------------------------------------------------
        # Rate limiting
        # ----------------------------------------------------

        print(
            f"Waiting "
            f"{REQUEST_INTERVAL_SECONDS} "
            f"seconds before Gemini request..."
        )

        time.sleep(
            REQUEST_INTERVAL_SECONDS
        )

        # ----------------------------------------------------
        # Gemini
        # ----------------------------------------------------

        analysis = analyze_candidate(
            candidate,
            newspaper_name
        )

        analysis = normalize_result(
            analysis
        )

        # ----------------------------------------------------
        # Headline safety check
        # ----------------------------------------------------

        clean_headline = clean_text(
            analysis.get(
                "clean_headline",
                ""
            )
        )

        if (
            headline
            and clean_headline
            and (
                clean_headline.lower()
                != headline.lower()
            )
        ):

            analysis[
                "needs_review"
            ] = True

        # ----------------------------------------------------
        # FINAL RECORD
        # ----------------------------------------------------

        record = {

            "newspaper":
                newspaper_name,

            "page":
                page,

            "source_headline":
                headline,

            "source_headline_block":
                candidate.get(
                    "headline_block"
                ),

            "source_headline_score":
                candidate.get(
                    "headline_score"
                ),

            "source_block_count":
                candidate.get(
                    "block_count"
                ),

            "source_body_block_count":
                candidate.get(
                    "body_block_count"
                ),

            "source_needs_review":
                candidate.get(
                    "needs_review",
                    False
                ),

            "source_article_text":
                clean_text(
                    candidate.get(
                        "full_article_text",
                        ""
                    )
                ),

            "source_blocks":
                candidate.get(
                    "blocks",
                    []
                ),

            "hybrid_analysis":
                analysis
        }

        results.append(
            record
        )

        # ----------------------------------------------------
        # SAVE IMMEDIATELY
        # ----------------------------------------------------

        save_json(
            results,
            output_file
        )

        print()
        print(
            "Saved progress."
        )

        print(
            f"Keep: "
            f"{analysis.get('keep')}"
        )

        print(
            f"Type: "
            f"{analysis.get('content_type')}"
        )

        print(
            f"Agriculture relevance: "
            f"{analysis.get('agriculture_relevance')}"
        )

        print(
            f"Topics: "
            f"{analysis.get('topics')}"
        )

        print(
            f"Needs review: "
            f"{analysis.get('needs_review')}"
        )

        print(
            f"Clean headline: "
            f"{analysis.get('clean_headline')}"
        )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        print()
        print(
            f"Progress: "
            f"{len(results)} total saved"
        )

    return results


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    input_files = sorted(
        INPUT_DIR.glob(
            "*.json"
        )
    )

    if not input_files:

        print(
            "No V4 JSON files found."
        )

        print(
            f"Expected directory:"
        )

        print(
            INPUT_DIR
        )

        return

    print()
    print("=" * 90)
    print(
        "HYBRID ARTICLE ANALYSIS V4"
    )
    print("=" * 90)

    print(
        f"Model: {MODEL_NAME}"
    )

    print(
        f"Request interval: "
        f"{REQUEST_INTERVAL_SECONDS} seconds"
    )

    print(
        "Resume mode: ENABLED"
    )

    print(
        "Placement questions: DISABLED"
    )

    print(
        f"Found {len(input_files)} "
        f"V4 file(s)."
    )

    print("=" * 90)

    total_processed = 0

    for input_file in input_files:

        results = process_newspaper(
            input_file
        )

        output_file = (
            OUTPUT_DIR
            / (
                input_file.stem
                + "_hybrid_v3.json"
            )
        )

        # Ensure output exists even if
        # everything was already processed.
        save_json(
            results,
            output_file
        )

        print()
        print("=" * 90)

        print(
            "Saved:"
        )

        print(
            output_file
        )

        print(
            f"Records in output: "
            f"{len(results)}"
        )

        print("=" * 90)

        total_processed += len(
            results
        )

    print()
    print("=" * 90)

    print(
        "HYBRID ARTICLE ANALYSIS V4 COMPLETE"
    )

    print("=" * 90)

    print(
        f"Total records saved: "
        f"{total_processed}"
    )

    print()
    print(
        "If the process is interrupted,"
    )

    print(
        "simply run the same command again."
    )

    print(
        "Previously completed candidates "
        "will be skipped automatically."
    )

    print("=" * 90)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()