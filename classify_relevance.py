import json
import re
from pathlib import Path

clean_folder = Path("data/clean_blocks")
output_folder = Path("data/classified")
output_folder.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. STRONG AGRICULTURE KEYWORDS
# These are relatively reliable agriculture signals.
# ============================================================

strong_keywords = [
    "agriculture",
    "agricultural",
    "farmer",
    "farmers",
    "farming",
    "crop",
    "crops",
    "cultivation",
    "harvest",
    "harvesting",
    "irrigation",
    "fertilizer",
    "fertiliser",
    "pesticide",
    "herbicide",
    "soil",
    "monsoon",
    "rainfall",
    "drought",
    "farmland",
    "horticulture",
    "floriculture",

    # Crops
    "wheat",
    "rice",
    "paddy",
    "maize",
    "corn",
    "soybean",
    "soyabean",
    "soya",
    "cotton",
    "sugarcane",
    "pulses",
    "millet",
    "chickpea",
    "groundnut",
    "mustard",
    "rapeseed",

    # Allied agriculture
    "livestock",
    "dairy",
    "fisheries",
    "aquaculture",
    "poultry",
    "animal husbandry",

    # Agricultural markets/policy
    "agribusiness",
    "agri-business",
    "agritech",
    "agri-tech",
    "agtech",
    "mandi",
    "minimum support price",
    "msp",
    "procurement",
    "foodgrain",
    "food grains",
    "food security",

    # Rural economy
    "rural economy",
    "rural development",
    "rural income",
    "rural demand",
    "rural credit",
    "rural employment",

    # Agriculture trade
    "agricultural exports",
    "agri exports",
    "agricultural imports",
    "food exports",
    "food imports",

    # Inputs/subsidies
    "fertiliser subsidy",
    "fertilizer subsidy",
    "farm subsidy",

    # Biofuel/agriculture connection
    "ethanol",
    "biofuel",

    # Agriculture supply chain
    "cold chain",
    "food processing",
    "agricultural supply chain",
    "farm supply chain",
]


# ============================================================
# 2. CONTEXT-DEPENDENT KEYWORDS
# These should only count when agriculture-related words
# appear nearby.
# ============================================================

context_keywords = [
    "seed",
    "seeds",
    "milk",
    "grain",
    "grains",
    "gram",
    "tur",
    "pulse",
    "vegetable",
    "vegetables",
    "fruit",
    "fruits",
    "tractor",
    "tractors",
    "warehouse",
    "warehousing",
    "cooking oil",
    "edible oil",
]


# ============================================================
# 3. WORDS THAT CAN CREATE FALSE POSITIVES
# ============================================================

negative_context = [
    "startup",
    "start-up",
    "funding",
    "seed round",
    "venture capital",
    "investment",
    "turnaround",
    "air india",
    "political",
    "election",
    "seat",
    "tender",
    "coal india",
    "property",
    "real estate",
    "apartment",
    "housing",
    "colony",
    "stock market",
    "share price",
]


# ============================================================
# 4. REGEX WHOLE-WORD MATCHING
# ============================================================

def contains_keyword(text, keyword):
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


# ============================================================
# 5. CHECK WHETHER CONTEXT KEYWORD IS ACTUALLY AGRICULTURAL
# ============================================================

def context_keyword_is_agriculture(text, keyword):

    text_lower = text.lower()

    # Find all occurrences of the keyword
    matches = list(
        re.finditer(
            r"\b" + re.escape(keyword) + r"\b",
            text_lower
        )
    )

    for match in matches:

        start = max(0, match.start() - 100)
        end = min(len(text_lower), match.end() + 100)

        nearby_text = text_lower[start:end]

        # Agriculture context
        agriculture_context = [
            "farmer",
            "farmers",
            "farming",
            "agriculture",
            "agricultural",
            "crop",
            "crops",
            "cultivation",
            "harvest",
            "soil",
            "fertilizer",
            "fertiliser",
            "monsoon",
            "rainfall",
            "irrigation",
            "kharif",
            "rabi",
            "field",
            "fields",
            "farm",
            "rural",
            "mandi",
            "msp",
            "procurement",
            "foodgrain",
            "food security",
            "export",
            "exports",
            "import",
            "imports",
            "yield",
            "acreage",
            "sowing",
            "sown",
            "ethanol",
        ]

        for word in agriculture_context:

            if re.search(
                r"\b" + re.escape(word) + r"\b",
                nearby_text
            ):
                return True

    return False


# ============================================================
# 6. CLASSIFY ONE BLOCK
# ============================================================

def classify_text(text):

    text_lower = text.lower()

    strong_matches = []
    context_matches = []
    negative_matches = []

    # --------------------------------------------------------
    # Strong agriculture keywords
    # --------------------------------------------------------

    for keyword in strong_keywords:

        if contains_keyword(text_lower, keyword):
            strong_matches.append(keyword)

    # --------------------------------------------------------
    # Context-dependent keywords
    # --------------------------------------------------------

    for keyword in context_keywords:

        if contains_keyword(text_lower, keyword):

            if context_keyword_is_agriculture(text_lower, keyword):
                context_matches.append(keyword)

    # --------------------------------------------------------
    # Negative context
    # --------------------------------------------------------

    for keyword in negative_context:

        if contains_keyword(text_lower, keyword):
            negative_matches.append(keyword)

    # --------------------------------------------------------
    # Calculate score
    # --------------------------------------------------------

    score = 0

    score += len(strong_matches) * 2
    score += len(context_matches)

    # Negative context reduces confidence
    score -= len(negative_matches) * 2

    # --------------------------------------------------------
    # Extra combinations
    # --------------------------------------------------------

    # Agriculture + context-dependent keyword
    if strong_matches and context_matches:
        score += 2

    # Agriculture + negative context
    if strong_matches and negative_matches:
        score -= 1

    # --------------------------------------------------------
    # Final classification
    # --------------------------------------------------------

    if score >= 4:
        relevance = "HIGH"

    elif score >= 2:
        relevance = "POSSIBLE"

    else:
        relevance = "LOW"

    return (
        relevance,
        score,
        strong_matches,
        context_matches,
        negative_matches
    )


# ============================================================
# 7. PROCESS NEWSPAPERS
# ============================================================

for json_file in clean_folder.glob("*_blocks.json"):

    print("=" * 80)
    print("PROCESSING:", json_file.name)
    print("=" * 80)

    with open(json_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    classified_blocks = []

    high = 0
    possible = 0
    low = 0

    for block in blocks:

        result = classify_text(block["text"])

        (
            relevance,
            score,
            strong_matches,
            context_matches,
            negative_matches
        ) = result

        block["agriculture_relevance"] = relevance
        block["agriculture_score"] = score
        block["strong_keywords"] = strong_matches
        block["context_keywords"] = context_matches
        block["negative_keywords"] = negative_matches

        classified_blocks.append(block)

        if relevance == "HIGH":
            high += 1

        elif relevance == "POSSIBLE":
            possible += 1

        else:
            low += 1

    # --------------------------------------------------------
    # Save output
    # --------------------------------------------------------

    output_file = output_folder / json_file.name

    with open(output_file, "w", encoding="utf-8") as file:

        json.dump(
            classified_blocks,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("Total blocks:", len(blocks))
    print("HIGH:", high)
    print("POSSIBLE:", possible)
    print("LOW:", low)
    print("Saved to:", output_file)
    print()


print("=" * 80)
print("CLASSIFICATION COMPLETE")
print("=" * 80)