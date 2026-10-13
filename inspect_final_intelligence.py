import json
from pathlib import Path
from collections import Counter


# ================================================================
# PATHS
# ================================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "data" / "final_intelligence_v1"
OUTPUT_DIR = BASE_DIR / "data" / "inspection"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ================================================================
# HEADER
# ================================================================

print("=" * 78)
print("FINAL INTELLIGENCE INSPECTION")
print("=" * 78)

print(f"Input directory : {INPUT_DIR}")
print(f"Output directory: {OUTPUT_DIR}")
print()


# ================================================================
# FIND FINAL INTELLIGENCE FILES
# ================================================================

files = sorted(
    p for p in INPUT_DIR.glob("*_final.json")
    if p.name != "ALL_FINAL_INTELLIGENCE_v1.json"
)

if not files:
    print("ERROR: No *_final.json files found.")
    raise SystemExit(1)

print(f"Found {len(files)} final intelligence files.")
print()


# ================================================================
# LOAD ALL RECORDS
# ================================================================

all_records = []


for file_path in files:

    print("=" * 78)
    print(f"FILE: {file_path.name}")
    print("=" * 78)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    except Exception as e:
        print(f"ERROR reading {file_path.name}: {e}")
        continue


    # The final analyzer normally saves a list of records.
    # This also handles a dictionary containing "records".
    if isinstance(data, list):
        records = data

    elif isinstance(data, dict):
        records = data.get("records", [])

    else:
        records = []


    print(f"Records found: {len(records)}")
    print()


    # ============================================================
    # INSPECT EACH RECORD
    # ============================================================

    for idx, record in enumerate(records, start=1):

        analysis = record.get("final_analysis", {})

        if not isinstance(analysis, dict):
            analysis = {}


        # --------------------------------------------------------
        # BASIC FIELDS
        # --------------------------------------------------------

        headline = (
            analysis.get("headline")
            or record.get("headline")
            or record.get("source_headline")
            or "NO HEADLINE"
        )

        content_type = str(
            analysis.get("content_type", "unknown")
        ).upper()

        agriculture = str(
            analysis.get("agriculture_relevance", "unknown")
        ).upper()

        source_quality = str(
            analysis.get("source_quality", "unknown")
        ).upper()

        keep = bool(
            analysis.get("keep", True)
        )

        needs_review = bool(
            analysis.get("needs_review", False)
        )


        # --------------------------------------------------------
        # DISPLAY
        # --------------------------------------------------------

        print(
            f"[{idx:02d}] "
            f"Page {record.get('page', '?')} | "
            f"{headline}"
        )

        print(
            f"     Type         : {content_type}"
        )

        print(
            f"     Agriculture  : {agriculture}"
        )

        print(
            f"     Keep         : {keep}"
        )

        print(
            f"     Source qual. : {source_quality}"
        )

        print(
            f"     Review       : "
            f"{'YES' if needs_review else 'NO'}"
        )


        # --------------------------------------------------------
        # AGRICULTURE REASON
        # --------------------------------------------------------

        agri_reason = analysis.get(
            "agriculture_relevance_reason",
            ""
        )

        if agri_reason:
            print(
                f"     Agri reason  : {agri_reason}"
            )


        # --------------------------------------------------------
        # WHY IT MATTERS
        # --------------------------------------------------------

        why_matters = analysis.get(
            "why_it_matters",
            ""
        )

        if why_matters:
            print(
                f"     Why matters  : {why_matters}"
            )


        # --------------------------------------------------------
        # SOURCE HEADLINE
        # --------------------------------------------------------

        source_headline = record.get(
            "source_headline",
            ""
        )

        if (
            source_headline
            and source_headline != headline
        ):
            print(
                f"     Source title : {source_headline}"
            )


        print()


        # --------------------------------------------------------
        # STORE INSPECTION METADATA
        # --------------------------------------------------------

        record["_inspection"] = {

            "headline": headline,

            "content_type": content_type,

            "agriculture_relevance": agriculture,

            "keep": keep,

            "needs_review": needs_review,

            "source_quality": source_quality

        }


        all_records.append(record)


# ================================================================
# OVERALL SUMMARY
# ================================================================

print("=" * 78)
print("SUMMARY")
print("=" * 78)


total = len(all_records)

review_count = sum(
    r["_inspection"]["needs_review"]
    for r in all_records
)

kept_count = sum(
    r["_inspection"]["keep"]
    for r in all_records
)


discarded_count = total - kept_count


# ================================================================
# CONTENT TYPE COUNTS
# ================================================================

type_counts = Counter(
    r["_inspection"]["content_type"]
    for r in all_records
)


# ================================================================
# AGRICULTURE RELEVANCE COUNTS
# ================================================================

agri_counts = Counter(
    r["_inspection"]["agriculture_relevance"]
    for r in all_records
)


# ================================================================
# SOURCE QUALITY COUNTS
# ================================================================

quality_counts = Counter(
    r["_inspection"]["source_quality"]
    for r in all_records
)


print(f"Total records       : {total}")

print(f"Kept                : {kept_count}")

print(f"Discarded           : {discarded_count}")

print(f"Needs review        : {review_count}")

print()


# ================================================================
# CONTENT TYPE SUMMARY
# ================================================================

print("Content types:")

for key, value in sorted(type_counts.items()):

    print(
        f"  {key:<15}: {value}"
    )

print()


# ================================================================
# AGRICULTURE SUMMARY
# ================================================================

print("Agriculture relevance:")

for key in [
    "HIGH",
    "MEDIUM",
    "LOW",
    "NONE",
    "UNKNOWN"
]:

    if agri_counts[key]:

        print(
            f"  {key:<15}: "
            f"{agri_counts[key]}"
        )

print()


# ================================================================
# SOURCE QUALITY SUMMARY
# ================================================================

print("Source quality:")

for key, value in sorted(
    quality_counts.items()
):

    print(
        f"  {key:<15}: {value}"
    )

print()


# ================================================================
# CREATE REVIEW QUEUE
# ================================================================

review_records = []


for record in all_records:

    inspection = record["_inspection"]

    agriculture = inspection[
        "agriculture_relevance"
    ]

    needs_review = inspection[
        "needs_review"
    ]


    # Include:
    # 1. Anything Gemini flagged for review
    # 2. Anything with HIGH agriculture relevance
    # 3. Anything with MEDIUM agriculture relevance

    if (
        needs_review
        or agriculture in {"HIGH", "MEDIUM"}
    ):

        analysis = record.get(
            "final_analysis",
            {}
        )

        review_records.append({

            "newspaper":
                record.get(
                    "newspaper",
                    ""
                ),

            "date":
                record.get(
                    "date",
                    ""
                ),

            "page":
                record.get(
                    "page",
                    ""
                ),

            "record_id":
                record.get(
                    "record_id",
                    ""
                ),

            "source_headline":
                record.get(
                    "source_headline",
                    ""
                ),

            "headline":
                inspection[
                    "headline"
                ],

            "content_type":
                inspection[
                    "content_type"
                ],

            "keep":
                inspection[
                    "keep"
                ],

            "agriculture_relevance":
                inspection[
                    "agriculture_relevance"
                ],

            "source_quality":
                inspection[
                    "source_quality"
                ],

            "needs_review":
                inspection[
                    "needs_review"
                ],

            "agriculture_relevance_reason":
                analysis.get(
                    "agriculture_relevance_reason",
                    ""
                ),

            "summary":
                analysis.get(
                    "summary",
                    ""
                ),

            "why_it_matters":
                analysis.get(
                    "why_it_matters",
                    ""
                ),

            "government_schemes":
                analysis.get(
                    "government_schemes",
                    []
                ),

            "key_numbers":
                analysis.get(
                    "key_numbers",
                    []
                ),

            "placement_questions":
                analysis.get(
                    "placement_questions",
                    []
                )

        })


# ================================================================
# SAVE REVIEW QUEUE
# ================================================================

review_path = (
    OUTPUT_DIR /
    "FINAL_REVIEW_QUEUE.json"
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


# ================================================================
# CREATE HUMAN-READABLE TXT REPORT
# ================================================================

txt_path = (
    OUTPUT_DIR /
    "FINAL_INTELLIGENCE_INSPECTION.txt"
)


with open(
    txt_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "FINAL INTELLIGENCE INSPECTION\n"
    )

    f.write(
        "=" * 78 + "\n\n"
    )


    # ------------------------------------------------------------
    # GROUP BY NEWSPAPER
    # ------------------------------------------------------------

    newspapers = sorted(
        set(
            r.get(
                "newspaper",
                ""
            )
            for r in all_records
        )
    )


    for newspaper in newspapers:

        f.write("\n")

        f.write(
            "=" * 78 + "\n"
        )

        f.write(
            newspaper + "\n"
        )

        f.write(
            "=" * 78 + "\n\n"
        )


        newspaper_records = [
            r
            for r in all_records
            if r.get(
                "newspaper",
                ""
            ) == newspaper
        ]


        for idx, record in enumerate(
            newspaper_records,
            start=1
        ):

            inspection = (
                record["_inspection"]
            )

            analysis = record.get(
                "final_analysis",
                {}
            )


            # ----------------------------------------------------
            # BASIC INFORMATION
            # ----------------------------------------------------

            f.write(
                f"[{idx:02d}] "
                f"Page {record.get('page', '?')} | "
                f"{inspection['headline']}\n"
            )


            f.write(
                f"     Type         : "
                f"{inspection['content_type']}\n"
            )


            f.write(
                f"     Agriculture  : "
                f"{inspection['agriculture_relevance']}\n"
            )


            f.write(
                f"     Keep         : "
                f"{inspection['keep']}\n"
            )


            f.write(
                f"     Source qual. : "
                f"{inspection['source_quality']}\n"
            )


            f.write(
                f"     Review       : "
                f"{'YES' if inspection['needs_review'] else 'NO'}\n"
            )


            # ----------------------------------------------------
            # SOURCE TITLE
            # ----------------------------------------------------

            if record.get(
                "source_headline"
            ):

                f.write(
                    f"     Source title : "
                    f"{record.get('source_headline')}\n"
                )


            # ----------------------------------------------------
            # AGRICULTURE REASON
            # ----------------------------------------------------

            if analysis.get(
                "agriculture_relevance_reason"
            ):

                f.write(
                    "     Agri reason  : "
                    + str(
                        analysis.get(
                            "agriculture_relevance_reason"
                        )
                    )
                    + "\n"
                )


            # ----------------------------------------------------
            # SUMMARY
            # ----------------------------------------------------

            if analysis.get(
                "summary"
            ):

                f.write(
                    "     Summary      : "
                    + str(
                        analysis.get(
                            "summary"
                        )
                    )
                    + "\n"
                )


            # ----------------------------------------------------
            # WHY IT MATTERS
            # ----------------------------------------------------

            if analysis.get(
                "why_it_matters"
            ):

                f.write(
                    "     Why matters  : "
                    + str(
                        analysis.get(
                            "why_it_matters"
                        )
                    )
                    + "\n"
                )


            # ----------------------------------------------------
            # KEY NUMBERS
            # ----------------------------------------------------

            if analysis.get(
                "key_numbers"
            ):

                f.write(
                    "     Key numbers  : "
                    + json.dumps(
                        analysis.get(
                            "key_numbers"
                        ),
                        ensure_ascii=False
                    )
                    + "\n"
                )


            # ----------------------------------------------------
            # GOVERNMENT SCHEMES
            # ----------------------------------------------------

            if analysis.get(
                "government_schemes"
            ):

                f.write(
                    "     Schemes      : "
                    + json.dumps(
                        analysis.get(
                            "government_schemes"
                        ),
                        ensure_ascii=False
                    )
                    + "\n"
                )


            # ----------------------------------------------------
            # PLACEMENT QUESTIONS
            # ----------------------------------------------------

            questions = analysis.get(
                "placement_questions",
                []
            )


            if questions:

                f.write(
                    "     Placement Qs :\n"
                )


                for question in questions:

                    if isinstance(
                        question,
                        dict
                    ):

                        question_text = (
                            question.get(
                                "question",
                                str(question)
                            )
                        )

                    else:

                        question_text = str(
                            question
                        )


                    f.write(
                        f"       - "
                        f"{question_text}\n"
                    )


            f.write("\n")


    # ------------------------------------------------------------
    # FINAL SUMMARY IN TXT
    # ------------------------------------------------------------

    f.write("\n")

    f.write(
        "=" * 78 + "\n"
    )

    f.write(
        "SUMMARY\n"
    )

    f.write(
        "=" * 78 + "\n"
    )

    f.write(
        f"Total records : {total}\n"
    )

    f.write(
        f"Kept          : {kept_count}\n"
    )

    f.write(
        f"Discarded     : {discarded_count}\n"
    )

    f.write(
        f"Needs review  : {review_count}\n"
    )


# ================================================================
# FINAL MESSAGE
# ================================================================

print("Inspection files created:")

print(
    f"  {review_path}"
)

print(
    f"  {txt_path}"
)

print()

print("=" * 78)
print("INSPECTION COMPLETE")
print("=" * 78)

print()
print("Next step:")
print(
    "Review FINAL_REVIEW_QUEUE.json and "
    "FINAL_INTELLIGENCE_INSPECTION.txt."
)

print(
    "Do NOT build the master database yet."
)