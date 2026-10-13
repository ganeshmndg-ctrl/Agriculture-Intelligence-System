"""
ONE-COMMAND DAILY PIPELINE
===========================

Put the newspaper PDFs you want to analyse in:
    Newspapers/Raw/

Then run:
    python run_daily_pipeline.py

Pipeline:

PDF
 ↓
Extraction
 ↓
Article grouping
 ↓
LOCAL RELEVANCE PREFILTER
 ↓
ARTICLE VALIDITY GATE
 ↓
Gemini analysis
 ↓
Story consolidation
 ↓
Final intelligence
 ↓
Curation
 ↓
Master database
 ↓
Government intelligence
 ↓
Connections
 ↓
Daily intelligence
 ↓
Priority Word report

The script:
1. Checks the Raw folder.
2. Makes a safety backup of the existing Master Intelligence Database.
3. Clears temporary/intermediate processing outputs.
4. Runs the complete newspaper -> intelligence pipeline.
5. Uses local filtering BEFORE Gemini to reduce unnecessary API calls.
6. Preserves old Master Database records and merges the new batch.
7. Rebuilds government intelligence and connections.
8. Updates the Daily Intelligence Database.
9. Creates the focused Word report.

It does NOT:
- delete your Master Database
- delete your Daily Intelligence Database
- delete previous Word reports
- move/delete your PDFs
- generate GD/interview questions
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "Newspapers" / "Raw"
DATA_DIR = BASE_DIR / "data"

MASTER_DIR = DATA_DIR / "master_database_v1"
MASTER_FILE = MASTER_DIR / "MASTER_INTELLIGENCE_DATABASE_v1.json"

BACKUP_DIR = DATA_DIR / "master_backups"

DAILY_DIR = DATA_DIR / "daily_intelligence_v1"
REPORT_DIR = DATA_DIR / "daily_reports"


# ============================================================
# TEMPORARY / REGENERATED PROCESSING FOLDERS
# ============================================================

TEMP_DIRS = [
    "extracted_text",
    "blocks",
    "clean_blocks",
    "rich_blocks",
    "classified",
    "merged_blocks",
    "articles",
    "grouped_articles",
    "analyzed_articles",
    "final_articles",
    "all_article_candidates",
    "page_layout_diagnostics",
    "grouped_all_articles_v3",
    "grouped_all_articles_v4",

    # Local filtering / Gemini stages
    "grouped_all_articles_v4_raw",
    "hybrid_articles_v1",
    "hybrid_articles_v2",
    "hybrid_articles_v3",

    # Downstream processing
    "consolidated_articles_v1",
    "final_intelligence_v1",
    "curated_intelligence_v23",
]


# ============================================================
# PIPELINE ORDER
# ============================================================

PIPELINE = [

    # --------------------------------------------------------
    # EXTRACTION
    # --------------------------------------------------------

    ("PDF extraction", "pdf_reader.py"),

    ("Block extraction", "extract_blocks.py"),

    ("Block cleaning", "clean_blocks.py"),

    ("Rich block extraction", "extract_rich_blocks.py"),


    # --------------------------------------------------------
    # ARTICLE DETECTION / GROUPING
    # --------------------------------------------------------

    (
        "General article candidate detection",
        "group_all_articles.py",
    ),

    (
        "Article grouping V4",
        "group_all_articles_v4.py",
    ),


    # --------------------------------------------------------
    # LOCAL FILTERING
    # IMPORTANT:
    # These happen BEFORE Gemini.
    # --------------------------------------------------------

    (
        "Local relevance prefilter",
        "prefilter_articles.py",
    ),

    (
        "Article validity gate",
        "article_validity_gate.py",
    ),


    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    (
        "Hybrid article analysis",
        "hybrid_article_analyzer.py",
    ),


    # --------------------------------------------------------
    # DOWNSTREAM INTELLIGENCE
    # --------------------------------------------------------

    (
        "Story consolidation",
        "consolidate_stories.py",
    ),

    (
        "Final intelligence analysis",
        "final_intelligence_analyzer.py",
    ),

    (
        "Intelligence curation",
        "curate_intelligence.py",
    ),

    (
        "Master database build",
        "build_master_database.py",
    ),

    (
        "Government intelligence bank",
        "scheme_knowledge_bank.py",
    ),

    (
        "Government encoding repair",
        "repair_government_intelligence_encoding.py",
    ),

    (
        "Connections bank",
        "build_connections_bank_v1_1.py",
    ),

    (
        "Connections validation",
        "validate_connections_bank.py",
    ),

    (
        "Daily intelligence database",
        "build_daily_intelligence.py",
    ),

    (
        "Daily priority Word report",
        "build_daily_priority_report.py",
    ),
]


# ============================================================
# HELPERS
# ============================================================

def print_header(text: str) -> None:
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def clear_directory_contents(path: Path) -> None:
    """
    Delete everything inside a directory,
    but keep the directory itself.
    """

    path.mkdir(parents=True, exist_ok=True)

    for item in path.iterdir():

        try:

            if item.is_dir():
                shutil.rmtree(item)

            else:
                item.unlink()

        except Exception as exc:

            raise RuntimeError(
                f"Could not clear temporary item:\n"
                f"{item}\n"
                f"Reason: {exc}"
            ) from exc


def get_active_pdfs() -> list[Path]:

    if not RAW_DIR.exists():

        raise FileNotFoundError(
            f"Raw newspaper folder does not exist:\n{RAW_DIR}"
        )

    pdfs = sorted(RAW_DIR.glob("*.pdf"))

    if not pdfs:

        raise RuntimeError(
            "No PDF newspapers were found in Newspapers\\Raw.\n"
            "Put the newspaper PDFs there and run the command again."
        )

    return pdfs


def extract_dates_from_filenames(
    pdfs: list[Path],
) -> set[str]:

    dates = set()

    for pdf in pdfs:

        matches = re.findall(
            r"\b\d{2}-\d{2}-\d{4}\b",
            pdf.stem,
        )

        dates.update(matches)

    return dates


def backup_master_database() -> Path | None:

    """
    Create a timestamped safety copy
    before the run.
    """

    if not MASTER_FILE.exists():

        print(
            "No existing Master Database found. "
            "This will be the first build."
        )

        return None

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_file = (
        BACKUP_DIR
        / f"MASTER_DATABASE_backup_{timestamp}.json"
    )

    shutil.copy2(
        MASTER_FILE,
        backup_file,
    )

    print(
        "Master DB backup created:"
    )

    print(
        f"  {backup_file}"
    )

    return backup_file


def load_json(path: Path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def save_json(
    path: Path,
    data,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temp_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    temp_path.replace(path)


def get_records(obj):

    """
    Supports either:

        {"records": [...]}

    or:

        [...]
    """

    if (
        isinstance(obj, dict)
        and isinstance(obj.get("records"), list)
    ):

        return obj["records"]

    if isinstance(obj, list):

        return obj

    raise ValueError(
        "Master database JSON does not contain "
        "a usable records list."
    )


def merge_master_database(
    previous_file: Path | None,
) -> None:

    """
    Merge the newly built Master DB
    with the previous Master DB.

    New records replace records
    with the same record_id.

    Old records not present in the
    new batch are preserved.
    """

    if not MASTER_FILE.exists():

        raise RuntimeError(
            "build_master_database.py completed, "
            "but the Master Database file "
            "was not created."
        )

    if previous_file is None:

        print(
            "No previous Master DB to merge."
        )

        return

    old_data = load_json(
        previous_file
    )

    new_data = load_json(
        MASTER_FILE
    )

    old_records = get_records(
        old_data
    )

    new_records = get_records(
        new_data
    )

    # --------------------------------------------------------
    # Index old records
    # --------------------------------------------------------

    old_by_id = {
        r.get("record_id"): r
        for r in old_records
        if (
            isinstance(r, dict)
            and r.get("record_id")
        )
    }

    # --------------------------------------------------------
    # Index new records
    # --------------------------------------------------------

    new_by_id = {
        r.get("record_id"): r
        for r in new_records
        if (
            isinstance(r, dict)
            and r.get("record_id")
        )
    }

    # --------------------------------------------------------
    # New batch first
    # --------------------------------------------------------

    merged_by_id = {}

    for record in new_records:

        rid = record.get(
            "record_id"
        )

        if rid:

            merged_by_id[rid] = record

    # --------------------------------------------------------
    # Preserve historical records
    # --------------------------------------------------------

    preserved_count = 0

    for record in old_records:

        rid = record.get(
            "record_id"
        )

        if (
            rid
            and rid not in merged_by_id
        ):

            merged_by_id[rid] = record

            preserved_count += 1

    merged_records = list(
        merged_by_id.values()
    )

    # --------------------------------------------------------
    # Preserve newly generated structure
    # --------------------------------------------------------

    if isinstance(
        new_data,
        dict,
    ):

        output = dict(
            new_data
        )

        output["records"] = (
            merged_records
        )

        output["record_count"] = (
            len(merged_records)
        )

        if "last_updated" in output:

            output["last_updated"] = (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )

        save_json(
            MASTER_FILE,
            output,
        )

    else:

        save_json(
            MASTER_FILE,
            merged_records,
        )

    print(
        "\nMASTER DATABASE MERGE"
    )

    print(
        f"  Previous records:   "
        f"{len(old_records)}"
    )

    print(
        f"  New batch records:  "
        f"{len(new_records)}"
    )

    print(
        f"  Preserved records:  "
        f"{preserved_count}"
    )

    print(
        f"  Final master total: "
        f"{len(merged_records)}"
    )


def run_script(
    label: str,
    script_name: str,
) -> None:

    script_path = (
        BASE_DIR
        / script_name
    )

    if not script_path.exists():

        raise FileNotFoundError(
            f"Required pipeline script not found:\n"
            f"{script_path}"
        )

    print_header(label)

    print(
        f"Running: {script_name}"
    )

    start = time.time()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=str(BASE_DIR),
        check=False,
    )

    elapsed = (
        time.time() - start
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"{script_name} failed "
            f"with exit code "
            f"{result.returncode}.\n"
            f"The pipeline has stopped "
            f"so that you can inspect "
            f"the error above."
        )

    print(
        f"\nCompleted successfully "
        f"in {elapsed:.1f} seconds."
    )


def find_latest_word_report() -> Path | None:

    if not REPORT_DIR.exists():

        return None

    reports = sorted(
        REPORT_DIR.glob(
            "*_Daily_Priority_Intelligence.docx"
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return (
        reports[0]
        if reports
        else None
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    overall_start = time.time()

    print_header(
        "AGRICULTURE INTELLIGENCE SYSTEM "
        "— ONE COMMAND PIPELINE"
    )

    print(
        "Project folder:"
    )

    print(
        f"  {BASE_DIR}"
    )

    print(
        "\nPython:"
    )

    print(
        f"  {sys.executable}"
    )


    # ========================================================
    # 1. CHECK ACTIVE NEWSPAPERS
    # ========================================================

    print_header(
        "1. CHECKING NEWSPAPERS"
    )

    pdfs = get_active_pdfs()

    print(
        f"PDFs found: {len(pdfs)}"
    )

    for pdf in pdfs:

        print(
            f"  - {pdf.name}"
        )

    detected_dates = (
        extract_dates_from_filenames(
            pdfs
        )
    )

    if len(detected_dates) > 1:

        raise RuntimeError(
            "More than one newspaper "
            "date was detected in "
            "Newspapers\\Raw:\n"
            + "\n".join(
                f"  - {d}"
                for d in sorted(
                    detected_dates
                )
            )
            + "\n\nFor this daily pipeline, "
              "keep only one day's newspapers "
              "in Raw."
        )

    if detected_dates:

        print(
            f"\nDetected newspaper date: "
            f"{next(iter(detected_dates))}"
        )

    else:

        print(
            "\nWARNING: No DD-MM-YYYY "
            "date was detected in the "
            "PDF filenames. "
            "The pipeline will continue."
        )


    # ========================================================
    # 2. SAFETY BACKUP
    # ========================================================

    print_header(
        "2. CREATING MASTER DATABASE BACKUP"
    )

    previous_master_backup = (
        backup_master_database()
    )


    # ========================================================
    # 3. CLEAR TEMPORARY DATA
    # ========================================================

    print_header(
        "3. CLEARING TEMPORARY "
        "PROCESSING DATA"
    )

    for dirname in TEMP_DIRS:

        path = (
            DATA_DIR
            / dirname
        )

        clear_directory_contents(
            path
        )

        print(
            f"  Cleared: "
            f"data\\{dirname}"
        )

    print(
        "\nPermanent databases were "
        "NOT cleared:"
    )

    print(
        "  - data\\master_database_v1"
    )

    print(
        "  - data\\government_intelligence_bank_v2"
    )

    print(
        "  - data\\connections_bank_v1_1"
    )

    print(
        "  - data\\daily_intelligence_v1"
    )

    print(
        "  - data\\daily_reports"
    )


    # ========================================================
    # 4. RUN PIPELINE
    # ========================================================

    print_header(
        "4. RUNNING COMPLETE "
        "ANALYSIS PIPELINE"
    )

    for label, script_name in PIPELINE:

        run_script(
            label,
            script_name,
        )

        # ----------------------------------------------------
        # Immediately after Master DB builder:
        # merge historical records.
        # ----------------------------------------------------

        if (
            script_name
            == "build_master_database.py"
        ):

            print_header(
                "MERGING HISTORICAL "
                "MASTER DATABASE"
            )

            merge_master_database(
                previous_master_backup
            )


    # ========================================================
    # 5. FINAL RESULT
    # ========================================================

    latest_report = (
        find_latest_word_report()
    )

    print_header(
        "PIPELINE COMPLETE"
    )

    total_time = (
        time.time()
        - overall_start
    )

    if latest_report:

        print(
            "Your Word report is ready:"
        )

        print(
            f"\n  {latest_report}\n"
        )

        print(
            "Open that file in Word."
        )

    else:

        print(
            "Pipeline completed, "
            "but no Daily Priority "
            "Word report was found."
        )

    print(
        f"\nTotal pipeline time: "
        f"{total_time / 60:.1f} minutes"
    )

    print(
        "\nNEXT DAILY RUN:"
    )

    print(
        "1. Move/archive the previous "
        "PDFs out of Newspapers\\Raw."
    )

    print(
        "2. Put the new day's PDFs "
        "into Newspapers\\Raw."
    )

    print(
        "3. Run:"
    )

    print(
        "   python run_daily_pipeline.py"
    )

    print(
        "\nYour old Master DB, Daily DB "
        "and previous Word reports "
        "are preserved."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\n\nPipeline stopped by user."
        )

        sys.exit(1)

    except Exception as exc:

        print(
            "\n\n"
            + "!" * 78
        )

        print(
            "PIPELINE STOPPED"
        )

        print(
            "!" * 78
        )

        print(
            f"\n{exc}"
        )

        print(
            "\nNo further pipeline "
            "stages were executed."
        )

        sys.exit(1)