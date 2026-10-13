import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# 1. SETUP
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found. Make sure your .env file is "
        "in the project root."
    )

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.1-flash-lite"

INPUT_DIR = Path("data/grouped_articles")
OUTPUT_DIR = Path("data/analyzed_articles")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. GEMINI RESPONSE SCHEMA
# ============================================================

response_schema = {
    "type": "OBJECT",
    "properties": {

        "source_quality": {
            "type": "STRING",
            "enum": [
                "GOOD",
                "LIMITED",
                "INSUFFICIENT"
            ]
        },

        "analysis_status": {
            "type": "STRING",
            "enum": [
                "ANALYZED",
                "NEEDS_REVIEW"
            ]
        },

        "needs_review": {
            "type": "BOOLEAN"
        },

        "summary": {
            "type": "STRING"
        },

        "source_basis": {
            "type": "OBJECT",
            "properties": {

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
                }
            },

            "required": [
                "reported_facts",
                "interpretations"
            ]
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
                "type": "STRING"
            }
        },

        "placement_questions": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        }
    },

    "required": [
        "source_quality",
        "analysis_status",
        "needs_review",
        "summary",
        "source_basis",
        "key_facts",
        "key_numbers",
        "agriculture_impact",
        "why_it_matters",
        "connections",
        "government_schemes",
        "placement_questions"
    ]
}


# ============================================================
# 3. ANALYSIS PROMPT
# ============================================================

def build_prompt(article):

    headline = article.get("headline", "")
    article_text = article.get("article_text", "")

    newspaper = article.get("newspaper", "")
    page = article.get("page", "")
    relevance = article.get("agriculture_relevance", "")
    score = article.get("agriculture_score", "")

    prompt = f"""
You are analyzing a newspaper article for an Agriculture Intelligence
and Placement Preparation System.

NEWSPAPER:
{newspaper}

PAGE:
{page}

HEADLINE:
{headline}

AGRICULTURE RELEVANCE:
{relevance}

AGRICULTURE SCORE:
{score}

SOURCE ARTICLE TEXT:
{article_text}


============================================================
SOURCE DISCIPLINE
============================================================

The SOURCE ARTICLE TEXT is the primary source of truth.

Use ONLY information supported by the extracted article.

Do NOT silently add information from your general knowledge.

Do NOT invent:
- facts
- statistics
- causes
- effects
- government schemes
- policy details
- quotations
- events
- organizations
- relationships between events


============================================================
REPORTED FACTS VS INTERPRETATIONS
============================================================

This distinction is extremely important.

"reported_facts" means information explicitly stated in the
newspaper article.

Examples:
- A rainfall deficit reported by the article.
- A government announcement mentioned by the article.
- A company investment figure reported by the article.
- A statement attributed to the US, India, a company, or an expert.

"interpretations" means reasonable conclusions that can be drawn
from the reported facts.

Examples:
- Possible stress on rain-fed agriculture.
- Possible implications for input demand.
- Possible effect on agricultural trade.

Never place an interpretation inside "reported_facts".

Never present an interpretation as though the newspaper explicitly
reported it.

If an interpretation is uncertain, use cautious language such as:
- may
- could
- potentially
- suggests
- is likely to affect

Do NOT convert correlation into causation.

For example:

BAD:
"Low rainfall caused fertilizer sales to fall."

GOOD:
"The article reports lower fertilizer sales alongside a rainfall
deficit."

Only state a causal relationship if the article itself clearly
establishes or attributes that relationship.


============================================================
ATTRIBUTION
============================================================

If the article attributes a claim to a particular source, preserve
that attribution.

For example:

"The US argues that..."

"The ministry said..."

"According to the report..."

Do not convert:

"The US alleges X"

into:

"X happened."

The system must clearly distinguish reported claims from independently
established facts.


============================================================
SOURCE QUALITY
============================================================

Use:

GOOD
------
The article contains enough body text to understand the main story.

LIMITED
--------
Some useful body text exists, but the article appears incomplete,
fragmented, or missing important sections.

INSUFFICIENT
------------
The extracted material contains only a headline, tiny snippet, or
too little information to reliably understand the article.


============================================================
ANALYSIS STATUS
============================================================

GOOD source:
    analysis_status = ANALYZED
    needs_review = false

LIMITED source:
    analysis_status = NEEDS_REVIEW
    needs_review = true

INSUFFICIENT source:
    analysis_status = NEEDS_REVIEW
    needs_review = true


============================================================
INSUFFICIENT SOURCE
============================================================

If the source is insufficient:

Do NOT create a fictional analysis.

Use:

summary:
Explain that the extracted article text is insufficient.

reported_facts:
Only include information directly visible in the source.

interpretations:
Normally leave empty.

key_numbers:
Only include numbers actually present.

agriculture_impact:
Explain that the impact cannot reliably be assessed.

why_it_matters:
Explain that the original newspaper article needs review.

connections:
Leave empty unless explicitly supported.

government_schemes:
Leave empty unless a scheme is explicitly named.

placement_questions:
At most one verification-oriented question.


============================================================
GOVERNMENT SCHEMES
============================================================

Only list a government scheme if it is explicitly mentioned
in the article.

Do NOT add a scheme simply because it is relevant.

Distinguish between:

1. New scheme
2. Existing scheme
3. Scheme update
4. Funding/outlay
5. Beneficiary update
6. Eligibility update
7. Implementation
8. Performance
9. Announcement

Do NOT call an existing scheme "new" unless the article explicitly
says it is newly launched or announced.


============================================================
AGRICULTURE IMPACT
============================================================

Where supported by the source, discuss implications for:

- farmers
- crop production
- crop yields
- agricultural prices
- farm inputs
- fertilizer
- irrigation
- rainfall
- exports
- imports
- food security
- rural economy
- agri-business
- supply chains
- food processing
- agricultural policy

Do not force an agriculture impact if the article does not support one.


============================================================
PLACEMENT QUESTIONS
============================================================

Create useful MBA / Agri-Business placement or group-discussion
questions based on the article.

Questions should test:

- understanding
- business implications
- agricultural implications
- policy trade-offs
- supply-chain implications
- market implications

Do not invent facts in order to create a question.


============================================================
OUTPUT
============================================================

Return the requested structured JSON only.
"""


    return prompt


# ============================================================
# 4. ANALYZE ONE ARTICLE
# ============================================================

def analyze_article(article):

    prompt = build_prompt(article)

    article_text = article.get("article_text", "").strip()

    word_count = len(article_text.split())

    # --------------------------------------------------------
    # LOCAL SOURCE-QUALITY CHECK
    # --------------------------------------------------------

    if word_count < 25:

        return {
            "source_quality": "INSUFFICIENT",

            "analysis_status": "NEEDS_REVIEW",

            "needs_review": True,

            "summary": (
                "The extracted source contains insufficient article "
                "text for a reliable analysis. Only a headline or a "
                "very small snippet was available."
            ),

            "source_basis": {
                "reported_facts": (
                    [article.get("headline", "")]
                    if article.get("headline")
                    else []
                ),
                "interpretations": []
            },

            "key_facts": (
                [article.get("headline", "")]
                if article.get("headline")
                else []
            ),

            "key_numbers": [],

            "agriculture_impact": (
                "Cannot be reliably assessed because the article "
                "body was not sufficiently extracted."
            ),

            "why_it_matters": (
                "The article needs to be reviewed against the "
                "original newspaper PDF before drawing conclusions."
            ),

            "connections": [],

            "government_schemes": [],

            "placement_questions": [
                "What additional information from the original "
                "article is needed to assess its significance "
                "for agriculture?"
            ]
        }


    # --------------------------------------------------------
    # GEMINI REQUEST
    # --------------------------------------------------------

    max_retries = 3
    wait_times = [5, 10, 15]

    for attempt in range(max_retries):

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )

            result = json.loads(response.text)

            return result


        except Exception as e:

            error_text = str(e)

            print(
                f"      Gemini error "
                f"(attempt {attempt + 1}/{max_retries}): "
                f"{error_text}"
            )

            if attempt < max_retries - 1:

                wait_time = wait_times[attempt]

                print(
                    f"      Waiting {wait_time} seconds "
                    f"before retry..."
                )

                time.sleep(wait_time)

            else:

                print("      Gemini analysis failed.")

                return {
                    "source_quality": "LIMITED",

                    "analysis_status": "NEEDS_REVIEW",

                    "needs_review": True,

                    "summary": (
                        "Gemini analysis could not be completed. "
                        "The article should be reviewed manually."
                    ),

                    "source_basis": {
                        "reported_facts": [],
                        "interpretations": []
                    },

                    "key_facts": [],

                    "key_numbers": [],

                    "agriculture_impact": "",

                    "why_it_matters": "",

                    "connections": [],

                    "government_schemes": [],

                    "placement_questions": []
                }


# ============================================================
# 5. PROCESS ONE NEWSPAPER
# ============================================================

def process_newspaper(input_file):

    print()
    print("=" * 70)
    print(f"Processing: {input_file.name}")
    print("=" * 70)

    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as f:

        articles = json.load(f)

    print(f"Articles found: {len(articles)}")

    analyzed_articles = []

    for index, article in enumerate(
        articles,
        start=1
    ):

        headline = article.get(
            "headline",
            "NO HEADLINE"
        )

        print()
        print(
            f"[{index}/{len(articles)}] "
            f"{headline}"
        )

        article_text = article.get(
            "article_text",
            ""
        )

        word_count = len(
            article_text.split()
        )

        print(
            f"    Extracted words: "
            f"{word_count}"
        )

        # ----------------------------------------------------
        # ANALYZE
        # ----------------------------------------------------

        analysis = analyze_article(
            article
        )

        # ----------------------------------------------------
        # PRESERVE ORIGINAL DATA
        # ----------------------------------------------------

        final_article = article.copy()

        final_article["analysis"] = analysis

        final_article["source_word_count"] = word_count

        analyzed_articles.append(
            final_article
        )

        print(
            f"    Source quality: "
            f"{analysis.get('source_quality', 'UNKNOWN')}"
        )

        print(
            f"    Status: "
            f"{analysis.get('analysis_status', 'UNKNOWN')}"
        )

        print(
            f"    Needs review: "
            f"{analysis.get('needs_review', 'UNKNOWN')}"
        )


    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    output_file = OUTPUT_DIR / (
        input_file.stem +
        "_analyzed.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            analyzed_articles,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("Saved:")
    print(output_file)

    return output_file


# ============================================================
# 6. MAIN
# ============================================================

def main():

    print("=" * 70)
    print("AGRICULTURE INTELLIGENCE SYSTEM")
    print("Gemini Article Analyzer")
    print("=" * 70)

    input_files = sorted(
        INPUT_DIR.glob(
            "*_blocks_grouped.json"
        )
    )

    if not input_files:

        print()
        print(
            "ERROR: No grouped article "
            "files found."
        )

        print()
        print(
            "Expected files inside:"
        )

        print(
            INPUT_DIR
        )

        return


    print()
    print(
        f"Found {len(input_files)} "
        f"newspaper file(s)."
    )


    output_files = []

    for input_file in input_files:

        output_file = process_newspaper(
            input_file
        )

        output_files.append(
            output_file
        )


    print()
    print("=" * 70)
    print("ALL NEWSPAPERS PROCESSED")
    print("=" * 70)


    for output_file in output_files:

        print(output_file)


    print()
    print(
        "Next step: inspect the analyzed "
        "JSON files."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()