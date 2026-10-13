"""
DETERMINISTIC FINAL INTELLIGENCE BUILDER
=========================================

This stage intentionally makes NO Gemini/API calls.

The hybrid analyzer has already produced the semantic analysis.

This script converts that existing analysis into the final intelligence
structure expected by the downstream database.

No new facts are generated.
No new semantic interpretation is generated.
No placement questions are generated.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "consolidated_articles_v1"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "final_intelligence_v1"
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


def save_json(
    data,
    path
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp_path.replace(
        path
    )


def clean_text(value):

    if value is None:
        return ""

    return " ".join(
        str(value)
        .replace(
            "\r",
            " "
        )
        .replace(
            "\n",
            " "
        )
        .split()
    )


def normalize_list(value):

    if isinstance(
        value,
        list
    ):

        return value

    if value is None:
        return []

    return [
        value
    ]


# ============================================================
# CONTENT TYPE
# ============================================================

def normalize_content_type(
    value
):

    value = clean_text(
        value
    ).lower()

    mapping = {

        "article":
            "article",

        "snippet":
            "snippet",

        "fact_box":
            "fact_box",

        "table":
            "table",

        "advertisement":
            "other",

        "page_furniture":
            "other",

        "caption":
            "other",

        "duplicate":
            "other",

        "unclear":
            "other",

        "section_package":
            "section_package"
    }

    return mapping.get(
        value,
        "other"
    )


# ============================================================
# SOURCE QUALITY
# ============================================================

def derive_source_quality(
    analysis,
    article_text
):

    existing = clean_text(
        analysis.get(
            "source_quality"
        )
    ).lower()

    if existing in {
        "high",
        "medium",
        "low"
    }:

        return existing

    content_type = clean_text(
        analysis.get(
            "content_type"
        )
    ).lower()

    if (
        content_type == "article"
        and len(article_text) >= 500
    ):

        return "high"

    if len(article_text) >= 150:

        return "medium"

    return "low"


# ============================================================
# DATE
# ============================================================

def derive_date(
    newspaper
):

    # Supports filenames such as:
    #
    # ET Delhi 01-10-2026
    # BS Mumbai 16-09-2026
    #
    match = re.search(
        r"(\d{2})-(\d{2})-(\d{4})",
        newspaper
    )

    if match:

        day, month, year = (
            match.groups()
        )

        return (
            f"{year}-"
            f"{month}-"
            f"{day}"
        )

    # Fallback only if the newspaper filename
    # contains no recognizable date.
    return datetime.now().strftime(
        "%Y-%m-%d"
    )


# ============================================================
# GET HYBRID ANALYSIS
# ============================================================

def get_hybrid_analysis(
    story
):

    source_records = (
        story.get(
            "source_records"
        )
        or []
    )

    if source_records:

        first = source_records[0]

        if isinstance(
            first,
            dict
        ):

            analysis = (
                first.get(
                    "hybrid_analysis"
                )
            )

            if isinstance(
                analysis,
                dict
            ):

                return analysis

    return {}


# ============================================================
# BUILD FINAL ANALYSIS
# ============================================================

def build_final_analysis(
    story
):

    analysis = get_hybrid_analysis(
        story
    )

    headline = clean_text(

        story.get(
            "merged_headline"
        )

        or story.get(
            "primary_headline"
        )

        or analysis.get(
            "clean_headline"
        )
    )

    article_text = clean_text(

        story.get(
            "merged_article_text"
        )

        or analysis.get(
            "article_text"
        )
    )

    content_type = normalize_content_type(

        analysis.get(
            "content_type"
        )

        or story.get(
            "content_type"
        )
    )

    keep = bool(

        analysis.get(
            "keep",
            story.get(
                "keep",
                False
            )
        )
    )

    needs_review = bool(

        analysis.get(
            "needs_review",
            story.get(
                "needs_review",
                True
            )
        )
    )

    if (
        not article_text
        and not headline
    ):

        keep = False

        needs_review = True

    topics = normalize_list(
        analysis.get(
            "topics"
        )
    )

    agriculture_relevance = clean_text(

        analysis.get(
            "agriculture_relevance",
            "none"
        )
    ).lower()

    if agriculture_relevance not in {

        "high",
        "medium",
        "low",
        "none"

    }:

        agriculture_relevance = (
            "none"
        )

        needs_review = True

    reported_facts = normalize_list(

        analysis.get(
            "reported_facts"
        )
    )

    interpretations = normalize_list(

        analysis.get(
            "interpretations"
        )
    )

    key_facts = normalize_list(

        analysis.get(
            "key_facts"
        )
    )

    key_numbers = normalize_list(

        analysis.get(
            "key_numbers"
        )
    )

    connections = normalize_list(

        analysis.get(
            "connections"
        )
    )

    government_schemes = normalize_list(

        analysis.get(
            "government_schemes"
        )
    )

    # IMPORTANT:
    # We intentionally do NOT include placement_questions.
    #
    # The user decided not to generate or maintain
    # placement/GD questions.

    return {

        "keep":
            keep,

        "content_type":
            content_type,

        "headline":
            headline,

        "summary":
            clean_text(
                analysis.get(
                    "summary"
                )
            ),

        "article_text":
            article_text,

        "source_quality":
            derive_source_quality(
                analysis,
                article_text
            ),

        "needs_review":
            needs_review,

        "topics":
            topics,

        "agriculture_relevance":
            agriculture_relevance,

        "agriculture_relevance_reason":
            clean_text(
                analysis.get(
                    "agriculture_relevance_reason"
                )
            ),

        "reported_facts":
            reported_facts,

        "interpretations":
            interpretations,

        "key_facts":
            key_facts,

        "key_numbers":
            key_numbers,

        "agriculture_impact":
            clean_text(
                analysis.get(
                    "agriculture_impact"
                )
            ),

        "why_it_matters":
            clean_text(
                analysis.get(
                    "why_it_matters"
                )
            ),

        "connections":
            connections,

        "government_schemes":
            government_schemes
    }


# ============================================================
# RECORD ID
# ============================================================

def make_record_id(
    newspaper,
    page,
    index
):

    safe = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        newspaper
    ).strip("_")

    return (
        f"{safe}_"
        f"P{page}_"
        f"S{index}"
    )


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(
    input_file
):

    data = load_json(
        input_file
    )

    newspaper = clean_text(
        data.get(
            "newspaper"
        )
    )

    pages = (
        data.get(
            "pages"
        )
        or []
    )

    all_stories = []

    for page_record in pages:

        if not isinstance(
            page_record,
            dict
        ):

            continue

        page_number = (
            page_record.get(
                "page"
            )
        )

        stories = (
            page_record.get(
                "stories"
            )
            or []
        )

        if not isinstance(
            stories,
            list
        ):

            continue

        for story in stories:

            if not isinstance(
                story,
                dict
            ):

                continue

            if story.get(
                "keep"
            ) is False:

                continue

            all_stories.append(
                (
                    page_number,
                    story
                )
            )

    print()
    print(
        "=" * 78
    )

    print(
        f"PROCESSING: "
        f"{input_file.name}"
    )

    print(
        "=" * 78
    )

    print(
        f"Usable stories found: "
        f"{len(all_stories)}"
    )

    results = []

    for index, (
        page_number,
        story
    ) in enumerate(
        all_stories,
        start=1
    ):

        final_analysis = (
            build_final_analysis(
                story
            )
        )

        headline = (
            final_analysis[
                "headline"
            ]
        )

        record = {

            "record_id":
                make_record_id(
                    newspaper,
                    page_number,
                    index
                ),

            "newspaper":
                newspaper,

            "date":
                derive_date(
                    newspaper
                ),

            "page":
                page_number,

            "story_id":
                story.get(
                    "story_id"
                ),

            "source_headline":
                headline,

            "final_analysis":
                final_analysis,

            "source_record":
                story,

            "processing": {

                "method":
                    "deterministic_final_intelligence_from_hybrid",

                "gemini_calls":
                    0,

                "questions_generated":
                    False
            }
        }

        results.append(
            record
        )

        print(
            f"[{index}/{len(all_stories)}] "
            f"Page {page_number} | "
            f"{headline[:110]}"
        )

        print(
            f"    keep="
            f"{final_analysis['keep']} | "
            f"type="
            f"{final_analysis['content_type']} | "
            f"agriculture="
            f"{final_analysis['agriculture_relevance']} | "
            f"review="
            f"{final_analysis['needs_review']}"
        )

    output_file = (

        OUTPUT_DIR
        /
        (
            input_file.stem
            + "_final.json"
        )
    )

    save_json(
        results,
        output_file
    )

    print()
    print(
        f"SAVED: "
        f"{output_file}"
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
            "*_consolidated_v1.json"
        )
    )

    if not input_files:

        raise FileNotFoundError(

            "No consolidated JSON "
            "files found.\n"
            f"Expected directory:\n"
            f"{INPUT_DIR}"
        )

    print(
        "=" * 78
    )

    print(
        "DETERMINISTIC FINAL "
        "INTELLIGENCE BUILDER"
    )

    print(
        "=" * 78
    )

    print(
        f"Found {len(input_files)} "
        f"consolidated file(s)."
    )

    print(
        "Gemini/API calls: 0"
    )

    print(
        "Placement questions generated: 0"
    )

    all_results = []

    for input_file in input_files:

        results = process_file(
            input_file
        )

        all_results.extend(
            results
        )

    master_file = (

        OUTPUT_DIR
        /
        "ALL_FINAL_INTELLIGENCE_v1.json"
    )

    save_json(
        all_results,
        master_file
    )

    total = len(
        all_results
    )

    kept = sum(

        1

        for record in all_results

        if record[
            "final_analysis"
        ].get(
            "keep"
        )
    )

    review = sum(

        1

        for record in all_results

        if record[
            "final_analysis"
        ].get(
            "needs_review"
        )
    )

    agri_counts = {

        "high": 0,
        "medium": 0,
        "low": 0,
        "none": 0
    }

    for record in all_results:

        value = record[
            "final_analysis"
        ].get(
            "agriculture_relevance",
            "none"
        )

        if value in agri_counts:

            agri_counts[
                value
            ] += 1

    print()
    print(
        "=" * 78
    )

    print(
        "DETERMINISTIC FINAL "
        "INTELLIGENCE COMPLETE"
    )

    print(
        "=" * 78
    )

    print(
        f"Total records          : "
        f"{total}"
    )

    print(
        f"Useful records         : "
        f"{kept}"
    )

    print(
        f"Needs review           : "
        f"{review}"
    )

    print()

    print(
        "Agriculture relevance:"
    )

    print(
        f"  HIGH   : "
        f"{agri_counts['high']}"
    )

    print(
        f"  MEDIUM : "
        f"{agri_counts['medium']}"
    )

    print(
        f"  LOW    : "
        f"{agri_counts['low']}"
    )

    print(
        f"  NONE   : "
        f"{agri_counts['none']}"
    )

    print()

    print(
        f"Master file: "
        f"{master_file}"
    )

    print()

    print(
        "Gemini/API calls: 0"
    )


if __name__ == "__main__":

    main()