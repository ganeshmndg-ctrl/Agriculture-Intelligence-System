import json
import shutil
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "data" / "grouped_all_articles_v4"
BACKUP_DIR = BASE_DIR / "data" / "grouped_all_articles_v4_raw"

MAX_CANDIDATES_PER_NEWSPAPER = 60
MIN_SCORE = 4


# ============================================================
# KEYWORD GROUPS
# ============================================================

AGRICULTURE = {
    "agriculture", "agricultural", "farmer", "farmers", "farming",
    "crop", "crops", "kharif", "rabi", "msp", "minimum support price",
    "paddy", "rice", "wheat", "maize", "corn", "pulse", "pulses",
    "chana", "tur", "urad", "soybean", "soya", "cotton", "sugar",
    "sugarcane", "oilseed", "oilseeds", "edible oil", "fertilizer",
    "fertiliser", "seed", "seeds", "irrigation", "monsoon",
    "rainfall", "drought", "foodgrain", "food grains", "horticulture",
    "livestock", "dairy", "milk", "fpo", "food processing",
    "agri", "agtech", "agribusiness", "agri-business", "commodity",
    "commodities", "mandi", "procurement", "warehousing", "warehouse",
    "cold chain", "farmgate", "farm gate", "rural economy",
    "rural demand", "rural income"
}

GOVERNMENT_POLICY = {
    "government", "govt", "ministry", "scheme", "programme", "program",
    "policy", "regulation", "regulatory", "notification", "notified",
    "cabinet", "parliament", "budget", "subsidy", "support",
    "msp", "duty", "duties", "tariff", "tariffs", "tax", "gst", "rbi",
    "sebi", "npci", "nabard", "fssai", "dgft", "wto",
    "trade policy", "export policy", "import policy"
}

BANKING_FINANCE = {
    "rbi", "reserve bank", "banking", "bank", "banks", "nbfc",
    "credit", "loan", "loans", "lending", "deposit", "deposits",
    "interest rate", "repo rate", "monetary policy", "upi", "npci",
    "mdr", "digital payments", "payment", "payments", "finance",
    "financial", "sebi", "mutual fund", "bond", "bonds", "npa",
    "capital market", "ipo", "listing", "insurance", "credit growth",
    "fpi", "foreign portfolio investment"
}

MACRO_ECONOMY = {
    "gdp", "inflation", "cpi", "wpi", "fiscal deficit", "fiscal",
    "monetary", "economy", "economic growth", "growth", "employment",
    "unemployment", "jobs", "manufacturing", "industrial output",
    "iip", "consumption", "demand", "capex", "investment",
    "interest rates", "rupee", "currency", "forex", "oil prices",
    "crude oil", "fuel prices", "energy"
}

TRADE = {
    "export", "exports", "exported", "import", "imports", "imported",
    "trade", "trade deficit", "trade surplus", "tariff", "tariffs",
    "customs", "wto", "fta", "free trade", "bilateral trade",
    "trade deal", "trade agreement", "supply chain", "supply chains",
    "shipping", "logistics", "global market", "global markets"
}

BUSINESS = {
    "company", "companies", "corporate", "business", "industry",
    "industries", "manufacturing", "production", "capacity",
    "investment", "investments", "acquisition", "merger", "ipo",
    "revenue", "profit", "profits", "sales", "demand", "market",
    "markets", "startup", "startups", "infrastructure", "logistics",
    "supply chain", "supply chains"
}

INTERNATIONAL = {
    "india and china", "india-china", "india and us", "india-us",
    "india and u.s.", "india and eu", "india-eu", "europe",
    "european union", "us", "u.s.", "united states", "china", "japan",
    "russia", "middle east", "west asia", "bangladesh", "africa",
    "global", "international", "wto"
}

LOW_VALUE = {
    "cricket", "football", "tennis", "sport", "sports", "match",
    "actor", "actress", "film", "movie", "cinema", "music",
    "concert", "celebrity", "fashion", "travel", "restaurant",
    "recipe", "lifestyle", "horoscope", "festival", "festive",
    "crime", "murder", "arrested", "robbery", "police",
    "terror", "terrorist", "encounter", "rally", "campaign",
    "poll", "election", "mla", "mp", "political party",
    "politics", "protest"
}

ADVERTISEMENT = {
    "advertisement", "advertorial", "classified", "tender notice",
    "e-tender", "invitation to bid", "last date of online",
    "for full report, go to", "contact us", "whatsapp",
    "subscribe now"
}

TABLE_TERMS = {
    "expiry", "strike", "traded", "open interest", "oi",
    "volume", "change close", "2-week avg", "52-week",
    "day high", "day low", "open price", "close price",
    "market data", "price qty", "qty open", "yield %",
    "coupon", "isin", "bid", "ask", "lot size",
    "open", "high", "low", "close", "chg"
}


# ============================================================
# HELPERS
# ============================================================

def clean(text):
    if text is None:
        return ""
    return " ".join(str(text).split())


def lower(text):
    return clean(text).lower()


def count_hits(text, terms):
    return sum(1 for term in terms if term in text)


def article_text(article):
    parts = [
        article.get("headline", ""),
        article.get("full_article_text", "")
    ]

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
# STRUCTURAL QUALITY CHECK
# ============================================================

def structural_noise(article):

    headline = clean(
        article.get("headline", "")
    )

    h = headline.lower()
    text = lower(
        article_text(article)
    )

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
    # 1. Advertisement
    # --------------------------------------------------------

    if count_hits(
        h,
        ADVERTISEMENT
    ) > 0:

        return True, "ADVERTISEMENT"

    # --------------------------------------------------------
    # 2. Newspaper mastheads / page headers
    # --------------------------------------------------------

    masthead_patterns = [
        r"the economic times.*new delhi",
        r"the economic times.*gurgaon",
        r"business standard.*new delhi",
        r"business standard.*mumbai",
        r"business standard.*delhi",
        r"business standard.*bengaluru",
        r"www\.economictimes\.com",
        r"www\.business-standard\.com",
        r"thursday.*1 october 2026",
        r"wednesday.*30 september 2026",
        r"economy: macro, micro",
    ]

    for pattern in masthead_patterns:

        if re.search(
            pattern,
            h,
            flags=re.IGNORECASE
        ):

            return True, "NEWSPAPER_HEADER"

    # --------------------------------------------------------
    # 3. Page-number fragments
    # --------------------------------------------------------

    page_fragment = re.match(
        r"^\s*\d{1,3}\s+the economic times",
        h
    )

    if page_fragment:

        return True, "PAGE_HEADER"

    # --------------------------------------------------------
    # 4. Obvious table / market-data fragments
    # --------------------------------------------------------

    table_hits = count_hits(
        h,
        TABLE_TERMS
    )

    if table_hits >= 2:

        return True, "MARKET_TABLE"

    # Short headline + market table terminology
    if (
        len(h) < 55
        and table_hits >= 1
        and body_count <= 1
    ):

        return True, "TABLE_FRAGMENT"

    # --------------------------------------------------------
    # 5. Chart / graph captions
    # --------------------------------------------------------

    chart_patterns = [
        r"^rainfall scenario",
        r"^growth in gross value",
        r"^growth in .* at .* prices",
        r"^from june 1 to september 30",
        r"^from june 1",
        r"^in percentage",
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
            flags=re.IGNORECASE
        ):

            # Protect it if it appears to be a
            # genuine article headline with a body.
            if body_count == 0:
                return True, "CHART_CAPTION"

    # --------------------------------------------------------
    # 6. Mostly numbers / symbols
    # --------------------------------------------------------

    if headline:

        alpha = sum(
            c.isalpha()
            for c in headline
        )

        digits = sum(
            c.isdigit()
            for c in headline
        )

        symbols = sum(
            not c.isalnum() and not c.isspace()
            for c in headline
        )

        if alpha < 12:

            return True, "TOO_FEW_LETTERS"

        if (
            digits > alpha
            and len(headline) < 90
        ):

            return True, "DATA_FRAGMENT"

        if (
            symbols > alpha
            and len(headline) < 80
        ):

            return True, "SYMBOL_FRAGMENT"

    # --------------------------------------------------------
    # 7. Very short isolated fragment
    # --------------------------------------------------------

    if (
        len(headline) < 12
        and body_count == 0
    ):

        return True, "VERY_SHORT_FRAGMENT"

    # --------------------------------------------------------
    # 8. Headline ending with extraction debris
    # --------------------------------------------------------

    debris_patterns = [
        r"\bp\d+\s*>$",
        r"\bp\d+\s*$",
        r"\.\.\.$",
        r"\|\s*$",
        r"\*\s*$",
    ]

    for pattern in debris_patterns:

        if re.search(
            pattern,
            h
        ):

            if body_count == 0:

                return True, "EXTRACTION_DEBRIS"

    # --------------------------------------------------------
    # 9. Extremely thin article
    # --------------------------------------------------------

    # Only reject if the story is ALSO weakly relevant.
    if (
        body_count == 0
        and block_count <= 1
        and len(text) < 120
    ):

        relevance_hits = (
            count_hits(
                h,
                AGRICULTURE
            )
            + count_hits(
                h,
                GOVERNMENT_POLICY
            )
            + count_hits(
                h,
                BANKING_FINANCE
            )
            + count_hits(
                h,
                MACRO_ECONOMY
            )
            + count_hits(
                h,
                TRADE
            )
        )

        if relevance_hits == 0:

            return True, "THIN_NON_RELEVANT_BLOCK"

    return False, ""


# ============================================================
# INTELLIGENCE SCORE
# ============================================================

def score_article(article):

    headline = lower(
        article.get(
            "headline",
            ""
        )
    )

    text = lower(
        article_text(article)
    )

    score = 0
    reasons = []

    ag_h = count_hits(
        headline,
        AGRICULTURE
    )

    ag_t = count_hits(
        text,
        AGRICULTURE
    )

    gov_h = count_hits(
        headline,
        GOVERNMENT_POLICY
    )

    gov_t = count_hits(
        text,
        GOVERNMENT_POLICY
    )

    bank_h = count_hits(
        headline,
        BANKING_FINANCE
    )

    bank_t = count_hits(
        text,
        BANKING_FINANCE
    )

    macro_h = count_hits(
        headline,
        MACRO_ECONOMY
    )

    macro_t = count_hits(
        text,
        MACRO_ECONOMY
    )

    trade_h = count_hits(
        headline,
        TRADE
    )

    trade_t = count_hits(
        text,
        TRADE
    )

    business_h = count_hits(
        headline,
        BUSINESS
    )

    business_t = count_hits(
        text,
        BUSINESS
    )

    intl_h = count_hits(
        headline,
        INTERNATIONAL
    )

    low_h = count_hits(
        headline,
        LOW_VALUE
    )

    # Agriculture
    if ag_h:
        score += 8
        reasons.append(
            "AGRICULTURE_HEADLINE"
        )

    elif ag_t:
        score += 4
        reasons.append(
            "AGRICULTURE_TEXT"
        )

    # Government
    if gov_h:
        score += 5
        reasons.append(
            "GOVERNMENT_POLICY_HEADLINE"
        )

    elif gov_t >= 2:
        score += 2
        reasons.append(
            "GOVERNMENT_POLICY_TEXT"
        )

    # Banking
    if bank_h:
        score += 5
        reasons.append(
            "BANKING_FINANCE_HEADLINE"
        )

    elif bank_t:
        score += 2
        reasons.append(
            "BANKING_FINANCE_TEXT"
        )

    # Macro
    if macro_h:
        score += 4
        reasons.append(
            "MACRO_HEADLINE"
        )

    elif macro_t:
        score += 2
        reasons.append(
            "MACRO_TEXT"
        )

    # Trade
    if trade_h:
        score += 5
        reasons.append(
            "TRADE_HEADLINE"
        )

    elif trade_t:
        score += 2
        reasons.append(
            "TRADE_TEXT"
        )

    # Business
    if business_h:
        score += 3
        reasons.append(
            "BUSINESS_HEADLINE"
        )

    elif business_t:
        score += 1
        reasons.append(
            "BUSINESS_TEXT"
        )

    # International
    if intl_h:
        score += 2
        reasons.append(
            "INTERNATIONAL_HEADLINE"
        )

    # Article depth
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

    if body_count >= 3:

        score += 2

        reasons.append(
            "SUBSTANTIAL_BODY"
        )

    elif body_count >= 1:

        score += 1

        reasons.append(
            "HAS_BODY"
        )

    # Short headline penalty
    if len(headline) < 12:

        score -= 2

        reasons.append(
            "VERY_SHORT_HEADLINE"
        )

    # Low-value penalty
    if low_h:

        score -= min(
            8,
            low_h * 3
        )

        reasons.append(
            "LOW_VALUE_HEADLINE"
        )

    # Strong protection
    guaranteed = (
        ag_h >= 1
        or (
            gov_h >= 1
            and (
                ag_t
                or bank_h
                or trade_h
                or macro_h
            )
        )
        or (
            trade_h >= 1
            and (
                ag_t
                or macro_h
                or business_h
            )
        )
        or bank_h >= 1
        or macro_h >= 1
    )

    return (
        score,
        reasons,
        guaranteed
    )


# ============================================================
# SELECT ARTICLES
# ============================================================

def choose_articles(articles):

    scored = []

    for article in articles:

        noise, noise_reason = (
            structural_noise(
                article
            )
        )

        if noise:

            scored.append({
                "article": article,
                "score": -999,
                "reasons": [
                    noise_reason
                ],
                "guaranteed": False,
                "noise": True
            })

            continue

        score, reasons, guaranteed = (
            score_article(
                article
            )
        )

        scored.append({
            "article": article,
            "score": score,
            "reasons": reasons,
            "guaranteed": guaranteed,
            "noise": False
        })

    candidates = [
        item
        for item in scored
        if (
            not item["noise"]
            and (
                item["score"] >= MIN_SCORE
                or item["guaranteed"]
            )
        )
    ]

    candidates.sort(
        key=lambda x: (
            x["guaranteed"],
            x["score"],
            int(
                x["article"].get(
                    "body_block_count",
                    0
                ) or 0
            ),
            int(
                x["article"].get(
                    "block_count",
                    0
                ) or 0
            )
        ),
        reverse=True
    )

    selected = candidates[
        :MAX_CANDIDATES_PER_NEWSPAPER
    ]

    return (
        scored,
        selected
    )


# ============================================================
# PROCESS FILE
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
            f"in {path.name}: expected "
            f"a list of pages."
        )

    all_articles = []

    for page_record in data:

        articles = page_record.get(
            "articles",
            []
        )

        if isinstance(
            articles,
            list
        ):

            all_articles.extend(
                articles
            )

    scored, selected = (
        choose_articles(
            all_articles
        )
    )

    selected_ids = {
        id(item["article"])
        for item in selected
    }

    output = []

    for page_record in data:

        page_articles = (
            page_record.get(
                "articles",
                []
            )
        )

        filtered_articles = [
            article
            for article in page_articles
            if id(article)
            in selected_ids
        ]

        new_page = dict(
            page_record
        )

        new_page["articles"] = (
            filtered_articles
        )

        diagnostics = dict(
            page_record.get(
                "diagnostics",
                {}
            )
        )

        diagnostics[
            "original_article_count"
        ] = len(page_articles)

        diagnostics[
            "filtered_article_count"
        ] = len(
            filtered_articles
        )

        diagnostics[
            "prefilter_applied"
        ] = True

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
        len(all_articles),
        len(selected),
        scored
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
            "ERROR: No grouped V4 JSON "
            "files found."
        )

        return

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print()
    print("=" * 90)
    print(
        "INTELLIGENCE ARTICLE PRE-FILTER V3"
    )
    print("=" * 90)

    print(
        "No Gemini/API calls are made."
    )

    print(
        "Removing newspaper headers, "
        "tables, charts and extraction noise."
    )

    print()

    total_before = 0
    total_after = 0
    total_noise = 0

    for path in files:

        # ----------------------------------------------------
        # IMPORTANT:
        # Backup the CURRENT V2 result.
        # The original V4 is already safely preserved.
        # ----------------------------------------------------

        backup_path = (
            BACKUP_DIR / path.name
        )

        shutil.copy2(
            path,
            backup_path
        )

        before, after, scored = (
            process_file(path)
        )

        total_before += before
        total_after += after

        noise_count = sum(
            1
            for item in scored
            if item["noise"]
        )

        total_noise += noise_count

        print("-" * 90)

        print(
            f"NEWSPAPER: {path.stem}"
        )

        print(
            f"Before V3 cleanup : {before}"
        )

        print(
            f"Structural noise  : {noise_count}"
        )

        print(
            f"After V3 cleanup  : {after}"
        )

        print(
            f"Removed this stage: "
            f"{before - after}"
        )

        print()

        print(
            "Top selected candidates:"
        )

        selected_preview = [
            item
            for item in scored
            if (
                not item["noise"]
                and (
                    item["score"] >= MIN_SCORE
                    or item["guaranteed"]
                )
            )
        ]

        selected_preview.sort(
            key=lambda x: (
                x["guaranteed"],
                x["score"]
            ),
            reverse=True
        )

        for i, item in enumerate(
            selected_preview[:25],
            start=1
        ):

            headline = clean(
                item["article"].get(
                    "headline",
                    ""
                )
            )

            print(
                f"  {i:02d}. "
                f"[{item['score']:>2}] "
                f"{headline}"
            )

        if after > 25:

            print(
                f"  ... and "
                f"{after - 25} more"
            )

    print()

    print("=" * 90)
    print(
        "INTELLIGENCE ARTICLE PRE-FILTER V3 COMPLETE"
    )
    print("=" * 90)

    print(
        f"Total before V3    : {total_before}"
    )

    print(
        f"Structural noise    : {total_noise}"
    )

    print(
        f"Total after V3     : {total_after}"
    )

    print(
        f"Total removed      : "
        f"{total_before - total_after}"
    )

    print()

    print(
        "Backup location:"
    )

    print(
        BACKUP_DIR
    )

    print()

    print(
        "Filtered files are ready "
        "for Gemini analysis."
    )

    print("=" * 90)


if __name__ == "__main__":
    main()