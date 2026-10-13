"""
DETERMINISTIC STORY CONSOLIDATION
==================================

This stage intentionally makes NO Gemini/API calls.

The hybrid analyzer has already performed semantic analysis.

This stage:
- preserves hybrid analysis
- keeps different candidates separate
- merges only exact normalized headline duplicates
- preserves source records and provenance
- does not invent relationships between stories
"""

from __future__ import annotations

import json
import re
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "hybrid_articles_v3"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "consolidated_articles_v1"
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

    temp_path.replace(path)


def clean_text(value):

    if value is None:
        return ""

    return " ".join(
        str(value)
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )


def normalize_headline(value):

    text = clean_text(value).lower()

    text = re.sub(
        r"[^\w\s₹$%.-]",
        " ",
        text,
        flags=re.UNICODE
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# LOAD RECORDS
# ============================================================

def load_records(path):

    data = load_json(path)

    if isinstance(data, list):

        return [
            x
            for x in data
            if isinstance(x, dict)
        ]

    return []


# ============================================================
# CANDIDATE ID
# ============================================================

def candidate_id(
    record,
    index
):

    return (
        f"P{record.get('page')}"
        f"_C{index}"
    )


# ============================================================
# PREPARE ONE STORY
# ============================================================

def prepare_story(
    record,
    cid
):

    analysis = (
        record.get("hybrid_analysis")
        or {}
    )

    source_headline = clean_text(
        record.get(
            "source_headline"
        )
    )

    clean_headline = clean_text(
        analysis.get(
            "clean_headline"
        )
    )

    headline = (
        clean_headline
        or source_headline
    )

    content_type = str(
        analysis.get(
            "content_type",
            "UNCLEAR"
        )
    ).upper()

    keep = bool(
        analysis.get(
            "keep",
            False
        )
    )

    article_text = clean_text(
        analysis.get(
            "article_text"
        )
        or record.get(
            "source_article_text"
        )
    )

    needs_review = bool(
        analysis.get(
            "needs_review",
            True
        )
    )

    return {

        "story_id": cid,

        "keep": keep,

        "content_type": content_type,

        "primary_headline": (
            source_headline
            or headline
        ),

        "merged_headline": headline,

        "merged_article_text": article_text,

        "candidate_ids": [
            cid
        ],

        "supporting_candidate_ids": [],

        "duplicate_candidate_ids": [],

        "needs_review": needs_review,

        "reason": (
            "Preserved as an independent "
            "candidate. No semantic "
            "cross-candidate merge was "
            "attempted."
        ),

        "source_records": [
            record
        ]
    }


# ============================================================
# CONSOLIDATE ONE PAGE
# ============================================================

def consolidate_page(
    page_records
):

    stories = []

    seen = {}

    for index, record in enumerate(
        page_records,
        start=1
    ):

        cid = candidate_id(
            record,
            index
        )

        story = prepare_story(
            record,
            cid
        )

        key = normalize_headline(
            story[
                "merged_headline"
            ]
        )

        # ----------------------------------------------------
        # Exact normalized headline duplicate
        # ----------------------------------------------------

        if (
            key
            and key in seen
        ):

            existing_index = seen[key]

            existing = stories[
                existing_index
            ]

            existing[
                "duplicate_candidate_ids"
            ].append(cid)

            existing[
                "candidate_ids"
            ].append(cid)

            existing[
                "source_records"
            ].append(record)

            # Preserve longer available text.
            if (
                len(
                    story[
                        "merged_article_text"
                    ]
                )
                >
                len(
                    existing[
                        "merged_article_text"
                    ]
                )
            ):

                existing[
                    "merged_article_text"
                ] = story[
                    "merged_article_text"
                ]

            existing[
                "needs_review"
            ] = (
                existing[
                    "needs_review"
                ]
                or story[
                    "needs_review"
                ]
            )

            continue

        # ----------------------------------------------------
        # New story
        # ----------------------------------------------------

        seen[key] = len(stories)

        stories.append(
            story
        )

    return stories


# ============================================================
# GROUP BY PAGE
# ============================================================

def group_by_page(
    records
):

    pages = {}

    for record in records:

        page = record.get(
            "page"
        )

        if page is None:
            continue

        pages.setdefault(
            page,
            []
        ).append(record)

    return pages


# ============================================================
# PROCESS ONE NEWSPAPER
# ============================================================

def process_newspaper(
    input_file
):

    records = load_records(
        input_file
    )

    print()
    print(
        "=" * 90
    )

    print(
        input_file.stem
    )

    print(
        "=" * 90
    )

    print(
        f"Hybrid candidate records: "
        f"{len(records)}"
    )

    pages = group_by_page(
        records
    )

    final_pages = []

    total_stories = 0

    for page_number, page_records in sorted(
        pages.items(),
        key=lambda x: x[0]
    ):

        stories = consolidate_page(
            page_records
        )

        print()
        print(
            "-" * 90
        )

        print(
            f"PAGE {page_number}"
        )

        print(
            f"Candidate records: "
            f"{len(page_records)}"
        )

        print(
            f"Story records:     "
            f"{len(stories)}"
        )

        kept_stories = [
            story
            for story in stories
            if story.get("keep") is True
        ]

        print(
            f"Stories kept:      "
            f"{len(kept_stories)}"
        )

        for story in stories:

            print(
                f"  - "
                f"{story.get('merged_headline', '')[:120]}"
                f" | "
                f"{story.get('content_type', '')}"
                f" | "
                f"KEEP={story.get('keep')}"
            )

        final_pages.append({

            "page": page_number,

            "input_candidate_count":
                len(page_records),

            "consolidated_story_count":
                len(stories),

            "stories":
                stories
        })

        total_stories += len(
            stories
        )

    return {

        "newspaper":
            input_file.stem,

        "input_candidate_count":
            len(records),

        "page_count":
            len(final_pages),

        "pages":
            final_pages,

        "processing": {

            "method":
                "deterministic_conservative_consolidation",

            "gemini_calls":
                0,

            "semantic_cross_candidate_merge":
                False,

            "exact_duplicate_headlines_merged":
                True
        }
    }


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
            "*_hybrid_v3.json"
        )
    )

    if not input_files:

        raise FileNotFoundError(

            "No hybrid V3 files found.\n"
            f"Expected directory:\n"
            f"{INPUT_DIR}"
        )

    print(
        "=" * 90
    )

    print(
        "DETERMINISTIC STORY CONSOLIDATION"
    )

    print(
        "=" * 90
    )

    print(
        f"Found {len(input_files)} "
        f"hybrid file(s)."
    )

    print(
        "Gemini/API calls: 0"
    )

    total = 0

    for input_file in input_files:

        result = process_newspaper(
            input_file
        )

        output_file = (
            OUTPUT_DIR
            / (
                input_file.stem
                + "_consolidated_v1.json"
            )
        )

        save_json(
            result,
            output_file
        )

        count = sum(

            page.get(
                "consolidated_story_count",
                0
            )

            for page in result.get(
                "pages",
                []
            )
        )

        total += count

        print()
        print(
            f"SAVED: {output_file}"
        )

        print(
            f"Consolidated stories: "
            f"{count}"
        )

    print()
    print(
        "=" * 90
    )

    print(
        "DETERMINISTIC STORY "
        "CONSOLIDATION COMPLETE"
    )

    print(
        "=" * 90
    )

    print(
        f"Total story records: "
        f"{total}"
    )

    print(
        "Gemini calls made: 0"
    )


if __name__ == "__main__":

    main()