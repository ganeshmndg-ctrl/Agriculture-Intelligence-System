import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "data" / "grouped_all_articles_v4"

# Keep almost everything at this stage.
# This is only a structural validity check.
MIN_HEADLINE_LENGTH = 15


def clean(text):
    if text is None:
        return ""
    return " ".join(str(text).split())


def get_article_text(article):
    parts = []

    parts.append(article.get("headline", ""))
    parts.append(article.get("full_article_text", ""))

    related = article.get("related_blocks", [])

    if isinstance(related, list):
        parts.extend(related)

    blocks = article.get("blocks", [])

    if isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict):
                parts.append(
                    block.get("text", "")
                )

    return clean(
        " ".join(
            str(x)
            for x in parts
            if x
        )
    )


# ============================================================
# STRUCTURAL VALIDITY
# ============================================================

def validity_check(article):

    headline = clean(
        article.get("headline", "")
    )

    h = headline.lower()

    article_text = get_article_text(article)

    body_count = int(
        article.get(
            "body_block_count",
            0
        ) or 0
    )

    block_count = int(
        article.get(
            "block_count",
            0
        ) or 0
    )

    # --------------------------------------------------------
    # 1. Empty / extremely short headline
    # --------------------------------------------------------

    if len(headline) < MIN_HEADLINE_LENGTH:

        return False, "SHORT_HEADLINE"

    # --------------------------------------------------------
    # 2. Newspaper mastheads
    # --------------------------------------------------------

    masthead_patterns = [

        r"the economic times.*new delhi",

        r"the economic times.*gurgaon",

        r"business standard.*new delhi",

        r"business standard.*delhi",

        r"business standard.*mumbai",

        r"www\.economictimes\.com",

        r"www\.business-standard\.com",

        r"economy: macro, micro",

        r"thursday.*1 october 2026",

        r"wednesday.*30 september 2026",
    ]

    for pattern in masthead_patterns:

        if re.search(
            pattern,
            h,
            re.IGNORECASE
        ):

            return False, "NEWSPAPER_HEADER"

    # --------------------------------------------------------
    # 3. Page-number + newspaper header
    # --------------------------------------------------------

    if re.match(
        r"^\s*\d{1,3}\s+the economic times",
        h
    ):

        return False, "PAGE_HEADER"

    # --------------------------------------------------------
    # 4. Obvious market tables
    # --------------------------------------------------------

    table_patterns = [

        r"market overview",

        r"index.*pe.*shrs",

        r"expiry.*strike.*traded",

        r"strike.*traded.*open",

        r"open.*interest.*chg",

        r"traded.*open.*interest",

        r"name of the trading member",

        r"sebi registration",

        r"price.*qty.*open interest",

        r"qty.*open interest",

        r"day high.*day low",

        r"52[- ]week.*high",

        r"52[- ]week.*low",

        r"volume.*open interest",
    ]

    for pattern in table_patterns:

        if re.search(
            pattern,
            h,
            re.IGNORECASE
        ):

            return False, "MARKET_TABLE"

    # --------------------------------------------------------
    # 5. Chart / graph captions
    # --------------------------------------------------------

    chart_patterns = [

        r"^rainfall scenario",

        r"^growth in gross value",

        r"^growth in .* at .* prices",

        r"^from june 1",

        r"^from june 1 to september",

        r"^in percentage$",

        r"^in %$",

        r"^in rs",

        r"^in ₹",

        r"^fig\.?\s*\d",

        r"^figure\s*\d",

        r"^chart\s*\d",

        r"^table\s*\d",
    ]

    for pattern in chart_patterns:

        if re.search(
            pattern,
            h,
            re.IGNORECASE
        ):

            # Keep it if there is a substantial body.
            if body_count < 2:

                return False, "CHART_CAPTION"

    # --------------------------------------------------------
    # 6. Page navigation / cross references
    # --------------------------------------------------------

    navigation_patterns = [

        r"^p\d+\s*>",

        r"^page\s+\d+$",

        r"\bp\d+\s*$",

        r"\bsee page\s+\d+",

        r"\bcontinued on page\s+\d+",

        r"\bcontinued from page\s+\d+",
    ]

    for pattern in navigation_patterns:

        if re.search(
            pattern,
            h,
            re.IGNORECASE
        ):

            return False, "PAGE_NAVIGATION"

    # --------------------------------------------------------
    # 7. Headlines containing many pipe-separated fragments
    # --------------------------------------------------------

    if headline.count("|") >= 2:

        return False, "HEADER_FRAGMENT"

    # --------------------------------------------------------
    # 8. Headlines dominated by numbers / symbols
    # --------------------------------------------------------

    alpha_count = sum(
        1
        for c in headline
        if c.isalpha()
    )

    digit_count = sum(
        1
        for c in headline
        if c.isdigit()
    )

    if alpha_count < 12:

        return False, "LOW_TEXT_CONTENT"

    if (
        digit_count > alpha_count
        and len(headline) < 90
    ):

        return False, "DATA_FRAGMENT"

    # --------------------------------------------------------
    # 9. Obvious repeated navigation fragments
    # --------------------------------------------------------

    fragment_patterns = [

        r"^navigate the market",

        r"^company days",

        r"^expiry strike",

        r"^price qty",

        r"^open % chg",

        r"^n cabinet decisions n",
    ]

    for pattern in fragment_patterns:

        if re.search(
            pattern,
            h,
            re.IGNORECASE
        ):

            return False, "EXTRACTION_FRAGMENT"

    # --------------------------------------------------------
    # 10. Extremely thin non-article
    # --------------------------------------------------------

    if (
        body_count == 0
        and block_count <= 1
        and len(article_text) < 100
    ):

        return False, "THIN_BLOCK"

    # --------------------------------------------------------
    # Otherwise valid
    # --------------------------------------------------------

    return True, "VALID"


# ============================================================
# PROCESS NEWSPAPER
# ============================================================

def process_file(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    if not isinstance(data, list):

        raise TypeError(
            f"Unexpected JSON structure "
            f"in {path.name}"
        )

    total = 0
    valid = 0
    rejected = 0

    rejection_reasons = {}

    output = []

    for page_record in data:

        articles = page_record.get(
            "articles",
            []
        )

        if not isinstance(
            articles,
            list
        ):

            articles = []

        filtered_articles = []

        for article in articles:

            total += 1

            is_valid, reason = (
                validity_check(
                    article
                )
            )

            if is_valid:

                filtered_articles.append(
                    article
                )

                valid += 1

            else:

                rejected += 1

                rejection_reasons[
                    reason
                ] = (
                    rejection_reasons.get(
                        reason,
                        0
                    ) + 1
                )

        new_page = dict(
            page_record
        )

        new_page[
            "articles"
        ] = filtered_articles

        diagnostics = dict(
            page_record.get(
                "diagnostics",
                {}
            )
        )

        diagnostics[
            "validity_gate_applied"
        ] = True

        diagnostics[
            "validity_original_count"
        ] = len(articles)

        diagnostics[
            "validity_retained_count"
        ] = len(
            filtered_articles
        )

        new_page[
            "diagnostics"
        ] = diagnostics

        output.append(
            new_page
        )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    return (
        total,
        valid,
        rejected,
        rejection_reasons
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_DIR.exists():

        print(
            "ERROR: grouped_all_articles_v4 "
            "folder does not exist."
        )

        return

    files = sorted(
        INPUT_DIR.glob(
            "*_grouped_v4.json"
        )
    )

    if not files:

        print(
            "ERROR: No grouped V4 files found."
        )

        return

    print()
    print("=" * 90)
    print(
        "ARTICLE VALIDITY GATE"
    )
    print("=" * 90)

    print(
        "No Gemini/API calls are made."
    )

    print(
        "This stage only removes obvious "
        "non-article extraction fragments."
    )

    print()

    total_before = 0
    total_valid = 0
    total_rejected = 0

    overall_reasons = {}

    for path in files:

        before, valid, rejected, reasons = (
            process_file(path)
        )

        total_before += before
        total_valid += valid
        total_rejected += rejected

        for reason, count in reasons.items():

            overall_reasons[
                reason
            ] = (
                overall_reasons.get(
                    reason,
                    0
                ) + count
            )

        print("-" * 90)

        print(
            f"NEWSPAPER: {path.stem}"
        )

        print(
            f"Before validity gate : {before}"
        )

        print(
            f"Valid articles       : {valid}"
        )

        print(
            f"Rejected             : {rejected}"
        )

        if reasons:

            print(
                "Rejection reasons:"
            )

            for reason, count in sorted(
                reasons.items(),
                key=lambda x: (
                    -x[1],
                    x[0]
                )
            ):

                print(
                    f"  - {reason}: {count}"
                )

        print()

        print(
            "Retained headlines:"
        )

        shown = 0

        for page_record in json.load(
            open(
                path,
                "r",
                encoding="utf-8"
            )
        ):

            for article in page_record.get(
                "articles",
                []
            ):

                headline = clean(
                    article.get(
                        "headline",
                        ""
                    )
                )

                shown += 1

                if shown <= 15:

                    print(
                        f"  {shown:02d}. "
                        f"{headline}"
                    )

        if valid > 15:

            print(
                f"  ... and "
                f"{valid - 15} more"
            )

    print()

    print("=" * 90)
    print(
        "ARTICLE VALIDITY GATE COMPLETE"
    )
    print("=" * 90)

    print(
        f"Total before gate : {total_before}"
    )

    print(
        f"Total valid       : {total_valid}"
    )

    print(
        f"Total rejected    : {total_rejected}"
    )

    print()

    print(
        "Overall rejection reasons:"
    )

    for reason, count in sorted(
        overall_reasons.items(),
        key=lambda x: (
            -x[1],
            x[0]
        )
    ):

        print(
            f"  - {reason}: {count}"
        )

    print()

    print(
        "The filtered V4 files are now ready "
        "for hybrid_article_analyzer.py."
    )

    print("=" * 90)


if __name__ == "__main__":
    main()