from pathlib import Path
from datetime import datetime
import json

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


# ============================================================
# DAILY PRIORITY INTELLIGENCE REPORT v2.0
# ============================================================
#
# Purpose:
#   Convert the complete Daily Intelligence Database into a
#   focused daily reading document.
#
# Input:
#   data/daily_intelligence_v1/
#       DAILY_INTELLIGENCE_DATABASE_v1.json
#
# Output:
#   data/daily_reports/
#       YYYY-MM-DD_Daily_Priority_Intelligence.docx
#
# IMPORTANT:
#   - No Gemini/API calls
#   - No new facts
#   - No question generation
#   - Does not modify the intelligence database
#   - Keeps the full database as the archive
#
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "daily_intelligence_v1"
    / "DAILY_INTELLIGENCE_DATABASE_v1.json"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "daily_reports"
)


# ============================================================
# DAILY READING TARGET
# ============================================================

MUST_READ_COUNT = 5
SECONDARY_COUNT = 3


# ============================================================
# CATEGORY LABELS
# ============================================================

CATEGORY_LABELS = {
    "CORE_AGRICULTURE": "Core Agriculture",
    "BANKING_FINANCE": "Banking & Finance",
    "INTERNATIONAL_TRADE": "International Trade",
    "MACRO_ECONOMY": "Macro Economy",
    "GENERAL_BUSINESS": "General Business",
}


# ============================================================
# HELPERS
# ============================================================

def clean(value):

    if value is None:
        return ""

    return str(value).strip()


def as_list(value):

    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def load_database():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Daily Intelligence database not found:\n"
            f"{INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):

    return (
        clean(value)
        .lower()
        .replace("-", " ")
        .replace("/", " ")
        .replace(",", " ")
        .replace(".", " ")
    )


# ============================================================
# PRIORITY SCORING
# ============================================================

def calculate_priority_score(record):

    """
    Deterministic priority score.

    This does NOT create new information.

    It uses fields already present in the Daily Intelligence
    Database.

    Higher score = greater priority for daily reading.
    """

    score = 0

    # --------------------------------------------------------
    # Placement relevance
    # --------------------------------------------------------

    placement = normalize_text(
        record.get(
            "placement_relevance"
        )
    )

    intelligence_type = normalize_text(
        record.get(
            "intelligence_type"
        )
    )

    if "high" in placement:
        score += 3

    elif "medium" in placement:
        score += 1

    if "placement intelligence" in intelligence_type:
        score += 2

    # --------------------------------------------------------
    # Agriculture relevance
    # --------------------------------------------------------

    agriculture_relevance = normalize_text(
        record.get(
            "agriculture_relevance"
        )
    )

    agriculture_connection = normalize_text(
        record.get(
            "agriculture_connection"
        )
    )

    if agriculture_relevance == "high":
        score += 3

    elif agriculture_relevance == "medium":
        score += 2

    elif agriculture_relevance == "low":
        score += 1

    if agriculture_connection == "direct":
        score += 3

    elif agriculture_connection == "indirect":
        score += 2

    elif agriculture_connection == "contextual":
        score += 1

    # --------------------------------------------------------
    # Government intelligence
    # --------------------------------------------------------

    government = as_list(
        record.get(
            "government_intelligence"
        )
    )

    if government:
        score += 3

    # --------------------------------------------------------
    # Cross-news connections
    # --------------------------------------------------------

    connections = as_list(
        record.get(
            "connections"
        )
    )

    if connections:
        score += 3

    # --------------------------------------------------------
    # Key quantitative information
    # --------------------------------------------------------

    key_numbers = as_list(
        record.get(
            "key_numbers"
        )
    )

    if len(key_numbers) >= 3:
        score += 2

    elif key_numbers:
        score += 1

    # --------------------------------------------------------
    # Why-it-matters content
    # --------------------------------------------------------

    if clean(
        record.get(
            "why_it_matters"
        )
    ):
        score += 1

    # --------------------------------------------------------
    # Agriculture impact
    # --------------------------------------------------------

    if clean(
        record.get(
            "agriculture_impact"
        )
    ):
        score += 1

    return score


# ============================================================
# DIVERSITY / DUPLICATE EVENT PROTECTION
# ============================================================

def story_signature(record):

    """
    Creates a simple deterministic signature so that several
    stories about essentially the same headline/event are not
    unnecessarily selected together.

    Uses headline + category + key entities/topics.
    """

    headline = normalize_text(
        record.get(
            "headline"
        )
    )

    category = normalize_text(
        record.get(
            "primary_category"
        )
    )

    topics = [
        normalize_text(x)
        for x in as_list(
            record.get(
                "topics"
            )
        )
    ]

    topics = [
        x for x in topics
        if x
    ]

    return (
        headline,
        category,
        tuple(sorted(topics[:5]))
    )


def get_topic_tokens(record):

    tokens = []

    for value in as_list(
        record.get(
            "topics"
        )
    ):

        text = normalize_text(value)

        if text:
            tokens.append(text)

    for value in as_list(
        record.get(
            "important_terms"
        )
    ):

        text = normalize_text(value)

        if text:
            tokens.append(text)

    return set(tokens)


def is_similar_story(
    candidate,
    selected
):

    """
    Conservative similarity check.

    This prevents obvious repetition without trying to
    perform fuzzy semantic analysis.
    """

    candidate_headline = normalize_text(
        candidate.get(
            "headline"
        )
    )

    candidate_category = normalize_text(
        candidate.get(
            "primary_category"
        )
    )

    candidate_tokens = get_topic_tokens(
        candidate
    )

    for existing in selected:

        existing_headline = normalize_text(
            existing.get(
                "headline"
            )
        )

        existing_category = normalize_text(
            existing.get(
                "primary_category"
            )
        )

        existing_tokens = get_topic_tokens(
            existing
        )

        # Exact headline = duplicate
        if (
            candidate_headline
            and candidate_headline
            == existing_headline
        ):
            return True

        # Same category + substantial topic overlap
        if (
            candidate_category
            and candidate_category
            == existing_category
            and candidate_tokens
            and existing_tokens
        ):

            overlap = (
                len(
                    candidate_tokens
                    & existing_tokens
                )
                / max(
                    1,
                    len(
                        candidate_tokens
                        | existing_tokens
                    )
                )
            )

            if overlap >= 0.60:
                return True

    return False


# ============================================================
# SELECT PRIORITY STORIES
# ============================================================

def select_priority_stories(records):

    scored = []

    for record in records:

        score = calculate_priority_score(
            record
        )

        scored.append(
            {
                "record": record,
                "score": score,
                "signature":
                    story_signature(record)
            }
        )

    # Highest score first
    # Then agriculture relevance
    # Then headline for deterministic ordering
    scored.sort(
        key=lambda x: (
            -x["score"],
            normalize_text(
                x["record"].get(
                    "headline"
                )
            )
        )
    )

    selected = []

    # --------------------------------------------------------
    # Must Read
    # --------------------------------------------------------

    for item in scored:

        record = item["record"]

        if is_similar_story(
            record,
            selected
        ):
            continue

        selected.append(
            record
        )

        if len(selected) >= MUST_READ_COUNT:
            break

    must_read_ids = {
        clean(
            record.get(
                "record_id"
            )
        )
        for record in selected
    }

    # --------------------------------------------------------
    # Secondary
    # --------------------------------------------------------

    secondary = []

    for item in scored:

        record = item["record"]

        record_id = clean(
            record.get(
                "record_id"
            )
        )

        if record_id in must_read_ids:
            continue

        if is_similar_story(
            record,
            selected + secondary
        ):
            continue

        secondary.append(
            record
        )

        if len(secondary) >= SECONDARY_COUNT:
            break

    return selected, secondary, scored


# ============================================================
# WORD FORMATTING
# ============================================================

def set_cell_shading(
    cell,
    fill
):

    tc_pr = cell._tc.get_or_add_tcPr()

    shd = tc_pr.find(
        qn("w:shd")
    )

    if shd is None:

        shd = OxmlElement("w:shd")

        tc_pr.append(shd)

    shd.set(
        qn("w:fill"),
        fill
    )


def set_cell_text(
    cell,
    text,
    bold=False
):

    cell.text = ""

    paragraph = cell.paragraphs[0]

    run = paragraph.add_run(
        clean(text)
    )

    run.bold = bold
    run.font.size = Pt(9)


def configure_document(
    doc
):

    section = doc.sections[0]

    section.top_margin = Inches(
        0.65
    )

    section.bottom_margin = Inches(
        0.65
    )

    section.left_margin = Inches(
        0.7
    )

    section.right_margin = Inches(
        0.7
    )

    styles = doc.styles

    normal = styles["Normal"]

    normal.font.name = "Aptos"
    normal.font.size = Pt(10)

    normal.paragraph_format.space_after = Pt(
        5
    )

    for style_name, size in [
        ("Title", 24),
        ("Heading 1", 17),
        ("Heading 2", 14),
        ("Heading 3", 11),
    ]:

        style = styles[
            style_name
        ]

        style.font.name = "Aptos"
        style.font.size = Pt(
            size
        )


def add_heading(
    doc,
    text,
    level=1
):

    return doc.add_heading(
        text,
        level=level
    )


def add_bullet(
    doc,
    text
):

    text = clean(text)

    if not text:
        return

    paragraph = doc.add_paragraph(
        style="List Bullet"
    )

    paragraph.paragraph_format.space_after = Pt(
        2
    )

    run = paragraph.add_run(
        text
    )

    run.font.size = Pt(10)


def add_label_paragraph(
    doc,
    label,
    text
):

    text = clean(text)

    if not text:
        return

    paragraph = doc.add_paragraph()

    paragraph.paragraph_format.space_after = Pt(
        5
    )

    run = paragraph.add_run(
        label
    )

    run.bold = True
    run.font.size = Pt(10)

    run2 = paragraph.add_run(
        text
    )

    run2.font.size = Pt(10)


# ============================================================
# TITLE
# ============================================================

def add_title(
    doc,
    database
):

    summary = database.get(
        "summary",
        {}
    )

    dates = summary.get(
        "dates",
        {}
    )

    if dates:

        report_date = next(
            iter(dates.keys())
        )

    else:

        report_date = datetime.now().strftime(
            "%Y-%m-%d"
        )

    try:

        parsed = datetime.strptime(
            report_date,
            "%Y-%m-%d"
        )

        display_date = parsed.strftime(
            "%d %B %Y"
        )

    except ValueError:

        display_date = report_date

    title = doc.add_paragraph()

    title.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = title.add_run(
        "DAILY AGRICULTURE & BUSINESS\n"
        "INTELLIGENCE"
    )

    run.bold = True
    run.font.size = Pt(25)

    subtitle = doc.add_paragraph()

    subtitle.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = subtitle.add_run(
        display_date
    )

    run.font.size = Pt(14)

    newspapers = summary.get(
        "newspapers",
        {}
    )

    if newspapers:

        paragraph = doc.add_paragraph()

        paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.CENTER
        )

        run = paragraph.add_run(
            " | ".join(
                newspapers.keys()
            )
        )

        run.italic = True
        run.font.size = Pt(10)

    doc.add_paragraph()

    paragraph = doc.add_paragraph()

    paragraph.alignment = (
        WD_ALIGN_PARAGRAPH.CENTER
    )

    run = paragraph.add_run(
        "Focused reading edition — "
        "selected from the complete "
        "Daily Intelligence Database"
    )

    run.font.size = Pt(9)
    run.italic = True

    doc.add_page_break()


# ============================================================
# DAILY SNAPSHOT
# ============================================================

def add_daily_snapshot(
    doc,
    database,
    must_read,
    secondary
):

    add_heading(
        doc,
        "1. Today's Reading Plan",
        level=1
    )

    total = len(
        database.get(
            "records",
            []
        )
    )

    paragraph = doc.add_paragraph()

    run = paragraph.add_run(
        f"Analysed today: {total} stories\n"
    )

    run.bold = True

    paragraph.add_run(
        f"Must read: {len(must_read)} stories\n"
    )

    paragraph.add_run(
        f"Read if time permits: "
        f"{len(secondary)} stories"
    )

    doc.add_paragraph()

    paragraph = doc.add_paragraph()

    run = paragraph.add_run(
        "Recommended approach: "
    )

    run.bold = True

    paragraph.add_run(
        "Read the Must Read section carefully. "
        "Use the Secondary section when you have "
        "additional time. The remaining stories "
        "are retained in the underlying intelligence "
        "database for future reference."
    )


# ============================================================
# STORY SUMMARY
# ============================================================

def add_priority_story(
    doc,
    record,
    number,
    level_label
):

    headline = clean(
        record.get(
            "headline"
        )
    )

    category = clean(
        record.get(
            "primary_category"
        )
    )

    category_label = CATEGORY_LABELS.get(
        category,
        category
    )

    score = calculate_priority_score(
        record
    )

    add_heading(
        doc,
        f"{number}. {headline}",
        level=2
    )

    metadata = []

    if category_label:
        metadata.append(
            category_label
        )

    if clean(
        record.get(
            "agriculture_relevance"
        )
    ):
        metadata.append(
            "Agriculture: "
            + clean(
                record.get(
                    "agriculture_relevance"
                )
            )
        )

    metadata.append(
        f"Priority score: {score}"
    )

    paragraph = doc.add_paragraph()

    run = paragraph.add_run(
        " | ".join(metadata)
    )

    run.italic = True
    run.font.size = Pt(9)

    # --------------------------------------------------------
    # What happened
    # --------------------------------------------------------

    add_label_paragraph(
        doc,
        "What happened: ",
        record.get(
            "what_happened"
        )
    )

    # --------------------------------------------------------
    # Key facts
    # --------------------------------------------------------

    key_facts = as_list(
        record.get(
            "key_facts"
        )
    )

    if key_facts:

        add_heading(
            doc,
            "Key facts",
            level=3
        )

        for fact in key_facts[:5]:

            if isinstance(
                fact,
                dict
            ):

                for key, value in fact.items():

                    if clean(value):

                        add_bullet(
                            doc,
                            f"{key}: {value}"
                        )

            else:

                add_bullet(
                    doc,
                    fact
                )

    # --------------------------------------------------------
    # Key numbers
    # --------------------------------------------------------

    key_numbers = as_list(
        record.get(
            "key_numbers"
        )
    )

    if key_numbers:

        add_heading(
            doc,
            "Key numbers",
            level=3
        )

        for number_value in key_numbers[:5]:

            if isinstance(
                number_value,
                dict
            ):

                for key, value in (
                    number_value.items()
                ):

                    if clean(value):

                        add_bullet(
                            doc,
                            f"{key}: {value}"
                        )

            else:

                add_bullet(
                    doc,
                    number_value
                )

    # --------------------------------------------------------
    # Why it matters
    # --------------------------------------------------------

    add_label_paragraph(
        doc,
        "Why it matters: ",
        record.get(
            "why_it_matters"
        )
    )

    # --------------------------------------------------------
    # Agriculture impact
    # --------------------------------------------------------

    agriculture_impact = clean(
        record.get(
            "agriculture_impact"
        )
    )

    if agriculture_impact:

        add_label_paragraph(
            doc,
            "Agriculture impact: ",
            agriculture_impact
        )

    # --------------------------------------------------------
    # Government intelligence
    # --------------------------------------------------------

    government = as_list(
        record.get(
            "government_intelligence"
        )
    )

    if government:

        add_heading(
            doc,
            "Government intelligence",
            level=3
        )

        for item in government:

            if not isinstance(
                item,
                dict
            ):
                add_bullet(
                    doc,
                    item
                )
                continue

            name = clean(
                item.get(
                    "initiative_name"
                )
            )

            event_type = clean(
                item.get(
                    "event_type"
                )
            )

            details = clean(
                item.get(
                    "details"
                )
            )

            if name:

                paragraph = doc.add_paragraph()

                run = paragraph.add_run(
                    name
                )

                run.bold = True

            if event_type:

                add_label_paragraph(
                    doc,
                    "Event: ",
                    event_type
                )

            if details:

                add_label_paragraph(
                    doc,
                    "Details: ",
                    details
                )

    # --------------------------------------------------------
    # Connections
    # --------------------------------------------------------

    connections = as_list(
        record.get(
            "connections"
        )
    )

    if connections:

        add_heading(
            doc,
            "Connection to other news",
            level=3
        )

        for connection in connections:

            if not isinstance(
                connection,
                dict
            ):
                add_bullet(
                    doc,
                    connection
                )
                continue

            chain = as_list(
                connection.get(
                    "chain"
                )
            )

            if chain:

                add_label_paragraph(
                    doc,
                    "Chain: ",
                    " → ".join(
                        clean(x)
                        for x in chain
                    )
                )

            relationship = clean(
                connection.get(
                    "relationship"
                )
            )

            if relationship:

                add_label_paragraph(
                    doc,
                    "Relationship: ",
                    relationship
                )

    # --------------------------------------------------------
    # Important terms
    # --------------------------------------------------------

    terms = as_list(
        record.get(
            "important_terms"
        )
    )

    if terms:

        add_label_paragraph(
            doc,
            "Important terms: ",
            " | ".join(
                clean(x)
                for x in terms[:12]
                if clean(x)
            )
        )

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    source = record.get(
        "source",
        {}
    )

    if isinstance(
        source,
        dict
    ):

        source_items = []

        newspaper = clean(
            source.get(
                "newspaper"
            )
        )

        page = clean(
            source.get(
                "page"
            )
        )

        source_pdf = clean(
            source.get(
                "source_pdf"
            )
        )

        if newspaper:
            source_items.append(
                newspaper
            )

        if page:
            source_items.append(
                f"Page {page}"
            )

        if source_pdf:
            source_items.append(
                source_pdf
            )

        if source_items:

            add_label_paragraph(
                doc,
                "Source: ",
                " | ".join(
                    source_items
                )
            )

    doc.add_paragraph()


# ============================================================
# ARCHIVE NOTE
# ============================================================

def add_archive_note(
    doc,
    total,
    selected
):

    remaining = max(
        0,
        total - selected
    )

    add_heading(
        doc,
        "Complete Intelligence Archive",
        level=1
    )

    paragraph = doc.add_paragraph()

    paragraph.add_run(
        f"{remaining} additional analysed "
        "stories were not included in today's "
        "focused reading list.\n\n"
    )

    paragraph.add_run(
        "They have NOT been deleted or discarded. "
        "They remain available in:"
    )

    paragraph = doc.add_paragraph()

    run = paragraph.add_run(
        "DAILY_INTELLIGENCE_DATABASE_v1.json"
    )

    run.bold = True

    paragraph = doc.add_paragraph()

    paragraph.add_run(
        "This keeps the daily reading load manageable "
        "while preserving the complete intelligence "
        "archive for future reference."
    )


# ============================================================
# BUILD DOCUMENT
# ============================================================

def build_report(
    database
):

    records = database.get(
        "records",
        []
    )

    if not records:

        raise ValueError(
            "No records found in Daily Intelligence database."
        )

    must_read, secondary, scored = (
        select_priority_stories(
            records
        )
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    dates = database.get(
        "summary",
        {}
    ).get(
        "dates",
        {}
    )

    if dates:

        report_date = next(
            iter(dates.keys())
        )

    else:

        report_date = datetime.now().strftime(
            "%Y-%m-%d"
        )

    output_file = (
        OUTPUT_DIR
        / f"{report_date}_Daily_Priority_Intelligence.docx"
    )

    doc = Document()

    configure_document(
        doc
    )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    add_title(
        doc,
        database
    )

    # --------------------------------------------------------
    # Reading plan
    # --------------------------------------------------------

    add_daily_snapshot(
        doc,
        database,
        must_read,
        secondary
    )

    doc.add_page_break()

    # --------------------------------------------------------
    # Must Read
    # --------------------------------------------------------

    add_heading(
        doc,
        "2. 🔥 MUST READ",
        level=1
    )

    paragraph = doc.add_paragraph()

    paragraph.add_run(
        "These are the highest-priority stories "
        "selected from today's analysed news."
    )

    for index, record in enumerate(
        must_read,
        start=1
    ):

        add_priority_story(
            doc,
            record,
            index,
            "MUST READ"
        )

    # --------------------------------------------------------
    # Secondary
    # --------------------------------------------------------

    if secondary:

        doc.add_page_break()

        add_heading(
            doc,
            "3. 🟡 READ IF TIME PERMITS",
            level=1
        )

        paragraph = doc.add_paragraph()

        paragraph.add_run(
            "These stories provide additional context "
            "but are not part of the core daily reading."
        )

        for index, record in enumerate(
            secondary,
            start=1
        ):

            add_priority_story(
                doc,
                record,
                index,
                "SECONDARY"
            )

    # --------------------------------------------------------
    # Archive
    # --------------------------------------------------------

    doc.add_page_break()

    add_archive_note(
        doc,
        len(records),
        len(must_read) + len(secondary)
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    doc.save(
        output_file
    )

    return (
        output_file,
        must_read,
        secondary,
        scored
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "DAILY PRIORITY INTELLIGENCE REPORT v2.0"
    )
    print("=" * 70)
    print()

    print(
        f"Input:\n{INPUT_FILE}"
    )

    print()

    database = load_database()

    records = database.get(
        "records",
        []
    )

    print(
        f"Total records available: "
        f"{len(records)}"
    )

    print()

    (
        output_file,
        must_read,
        secondary,
        scored
    ) = build_report(
        database
    )

    print("=" * 70)
    print("PRIORITY REPORT CREATED")
    print("=" * 70)

    print(
        f"Must Read:              "
        f"{len(must_read)}"
    )

    print(
        f"Read if time permits:   "
        f"{len(secondary)}"
    )

    print(
        f"Total selected:         "
        f"{len(must_read) + len(secondary)}"
    )

    print(
        f"Complete archive:       "
        f"{len(records)}"
    )

    print()

    print("MUST READ:")

    for index, record in enumerate(
        must_read,
        start=1
    ):

        print(
            f"{index}. "
            f"{record.get('headline', '')}"
            f" "
            f"[score={calculate_priority_score(record)}]"
        )

    print()

    print("SECONDARY:")

    for index, record in enumerate(
        secondary,
        start=1
    ):

        print(
            f"{index}. "
            f"{record.get('headline', '')}"
            f" "
            f"[score={calculate_priority_score(record)}]"
        )

    print()

    print(
        f"Output:\n{output_file}"
    )

    print()

    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()