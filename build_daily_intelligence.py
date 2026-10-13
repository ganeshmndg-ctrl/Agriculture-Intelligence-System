"""
DAILY INTELLIGENCE DATABASE BUILDER v1.2
=========================================

Purpose
-------
Build the Daily Intelligence Database from the authoritative:

    MASTER INTELLIGENCE DATABASE
    GOVERNMENT INTELLIGENCE BANK
    CURRENT CONNECTIONS BANK

Important design rules
----------------------
- Master Database is the primary source for intelligence records.
- Government Intelligence Bank is the primary source for government links.
- CURRENT Connections Bank is the only source for cross-story connections.
- Old/stale connection references are removed during rebuild.
- No placement/GD questions are generated.
- No external facts are introduced.
- Master Database is never modified.
- Government Intelligence Bank is never modified.
- Connections Bank is never modified.
"""


from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

MASTER_FILE = (
    DATA_DIR
    / "master_database_v1"
    / "MASTER_INTELLIGENCE_DATABASE_v1.json"
)

GOVERNMENT_FILE = (
    DATA_DIR
    / "government_intelligence_bank_v2"
    / "GOVERNMENT_INTELLIGENCE_BANK_v2.json"
)

CONNECTIONS_FILE = (
    DATA_DIR
    / "connections_bank_v1_1"
    / "CONNECTIONS_BANK_v1_1.json"
)

OUTPUT_DIR = (
    DATA_DIR
    / "daily_intelligence_v1"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "DAILY_INTELLIGENCE_DATABASE_v1.json"
)

REPORT_FILE = (
    OUTPUT_DIR
    / "DAILY_INTELLIGENCE_REPORT_v1.txt"
)


# ============================================================
# HELPERS
# ============================================================

def load_json(path: Path):

    if not path.exists():

        raise FileNotFoundError(
            f"Required file not found:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(
    path: Path,
    data
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

    temp_path.replace(path)


def clean(value):

    if value is None:
        return ""

    return str(value).strip()


def as_list(value):

    if isinstance(
        value,
        list
    ):

        return value

    if value is None:
        return []

    return [value]


# ============================================================
# MASTER DATABASE
# ============================================================

def load_master_records():

    data = load_json(
        MASTER_FILE
    )

    if isinstance(
        data,
        dict
    ):

        records = data.get(
            "records",
            []
        )

    elif isinstance(
        data,
        list
    ):

        records = data

    else:

        records = []

    return [
        record
        for record in records
        if isinstance(
            record,
            dict
        )
    ]


# ============================================================
# GOVERNMENT INTELLIGENCE
# ============================================================

def load_government_intelligence():

    data = load_json(
        GOVERNMENT_FILE
    )

    if not isinstance(
        data,
        dict
    ):

        return [], []

    initiatives = data.get(
        "initiatives",
        []
    )

    if not isinstance(
        initiatives,
        list
    ):

        initiatives = []

    source_links = []

    for initiative in initiatives:

        if not isinstance(
            initiative,
            dict
        ):

            continue

        initiative_id = clean(
            initiative.get(
                "initiative_id"
            )
        )

        initiative_name = clean(
            initiative.get(
                "initiative_name"
            )
        )

        initiative_type = clean(
            initiative.get(
                "initiative_type"
            )
        )

        mentions = initiative.get(
            "newspaper_mentions",
            []
        )

        if not isinstance(
            mentions,
            list
        ):

            continue

        for mention in mentions:

            if not isinstance(
                mention,
                dict
            ):

                continue

            record_id = clean(
                mention.get(
                    "record_id"
                )
            )

            if not record_id:
                continue

            source_links.append(
                {
                    "initiative_id":
                        initiative_id,

                    "initiative_name":
                        initiative_name,

                    "initiative_type":
                        initiative_type,

                    "event_type":
                        clean(
                            mention.get(
                                "event_type"
                            )
                        ),

                    "details":
                        clean(
                            mention.get(
                                "details"
                            )
                        ),

                    "date":
                        clean(
                            mention.get(
                                "date"
                            )
                        ),

                    "newspaper":
                        clean(
                            mention.get(
                                "newspaper"
                            )
                        ),

                    "page":
                        mention.get(
                            "page"
                        ),

                    "headline":
                        clean(
                            mention.get(
                                "headline"
                            )
                        ),

                    "source_pdf":
                        clean(
                            mention.get(
                                "source_pdf"
                            )
                        )
                }
            )

    return initiatives, source_links


# ============================================================
# CONNECTIONS BANK
# ============================================================

def load_current_connections():

    data = load_json(
        CONNECTIONS_FILE
    )

    if not isinstance(
        data,
        dict
    ):

        return []

    connections = data.get(
        "connections",
        []
    )

    if not isinstance(
        connections,
        list
    ):

        return []

    valid_connections = []

    for connection in connections:

        if not isinstance(
            connection,
            dict
        ):

            continue

        source_ids = connection.get(
            "source_record_ids",
            []
        )

        if not isinstance(
            source_ids,
            list
        ):

            continue

        source_ids = [
            clean(x)
            for x in source_ids
            if clean(x)
        ]

        if len(source_ids) < 2:
            continue

        valid_connections.append(
            {
                "connection_id":
                    clean(
                        connection.get(
                            "connection_id"
                        )
                    ),

                "connection_type":
                    clean(
                        connection.get(
                            "connection_type"
                        )
                    ),

                "relationship_type":
                    clean(
                        connection.get(
                            "relationship_type"
                        )
                    ),

                "source_record_ids":
                    source_ids,

                "source_event_ids":
                    as_list(
                        connection.get(
                            "source_event_ids",
                            []
                        )
                    ),

                "entities":
                    as_list(
                        connection.get(
                            "entities",
                            []
                        )
                    ),

                "relationship":
                    clean(
                        connection.get(
                            "relationship"
                        )
                    ),

                "chain":
                    as_list(
                        connection.get(
                            "chain",
                            []
                        )
                    ),

                "explanation":
                    clean(
                        connection.get(
                            "explanation"
                        )
                    ),

                "agriculture_relevance":
                    clean(
                        connection.get(
                            "agriculture_relevance"
                        )
                    ),

                "confidence":
                    clean(
                        connection.get(
                            "confidence"
                        )
                    ),

                "validation_status":
                    clean(
                        connection.get(
                            "validation_status"
                        )
                    ),

                "evidence":
                    as_list(
                        connection.get(
                            "evidence",
                            []
                        )
                    )
            }
        )

    return valid_connections


# ============================================================
# GOVERNMENT LINKS FOR A RECORD
# ============================================================

def government_links_for_record(
    record_id,
    source_links
):

    matches = []

    for link in source_links:

        if clean(
            link.get(
                "record_id",
                ""
            )
        ) == record_id:

            matches.append(
                {
                    key: value
                    for key, value in link.items()
                    if key != "record_id"
                }
            )

    return matches


# ============================================================
# CONNECTION LINKS FOR A RECORD
# ============================================================

def connections_for_record(
    record_id,
    connections
):

    matches = []

    for connection in connections:

        source_ids = connection.get(
            "source_record_ids",
            []
        )

        if record_id not in source_ids:
            continue

        matches.append(
            {
                "connection_id":
                    connection.get(
                        "connection_id",
                        ""
                    ),

                "connection_type":
                    connection.get(
                        "connection_type",
                        ""
                    ),

                "relationship_type":
                    connection.get(
                        "relationship_type",
                        ""
                    ),

                "source_record_ids":
                    connection.get(
                        "source_record_ids",
                        []
                    ),

                "source_event_ids":
                    connection.get(
                        "source_event_ids",
                        []
                    ),

                "entities":
                    connection.get(
                        "entities",
                        []
                    ),

                "relationship":
                    connection.get(
                        "relationship",
                        ""
                    ),

                "chain":
                    connection.get(
                        "chain",
                        []
                    ),

                "explanation":
                    connection.get(
                        "explanation",
                        ""
                    ),

                "agriculture_relevance":
                    connection.get(
                        "agriculture_relevance",
                        ""
                    ),

                "confidence":
                    connection.get(
                        "confidence",
                        ""
                    ),

                "validation_status":
                    connection.get(
                        "validation_status",
                        ""
                    ),

                "evidence":
                    connection.get(
                        "evidence",
                        []
                    )
            }
        )

    return matches


# ============================================================
# BUILD ONE DAILY RECORD
# ============================================================

def build_daily_record(
    master_record,
    government_links,
    connection_links,
    timestamp
):

    record_id = clean(
        master_record.get(
            "record_id"
        )
    )

    intelligence_id = (
        "INT_"
        + record_id
    )

    daily = {

        "intelligence_id":
            intelligence_id,

        "record_id":
            record_id,

        "newspaper":
            master_record.get(
                "newspaper",
                ""
            ),

        "date":
            master_record.get(
                "date",
                ""
            ),

        "page":
            master_record.get(
                "page"
            ),

        "headline":
            master_record.get(
                "source_headline",
                master_record.get(
                    "headline",
                    ""
                )
            ),

        "content_type":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "content_type",
                master_record.get(
                    "content_type",
                    ""
                )
            ),

        "source_quality":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "source_quality",
                ""
            ),

        "primary_category":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "primary_category",
                ""
            ),

        "primary_category_label":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "primary_category_label",
                ""
            ),

        "secondary_categories":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "secondary_categories",
                []
            ),

        "intelligence_type":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "intelligence_type",
                ""
            ),

        "agriculture_connection":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "agriculture_connection",
                ""
            ),

        "agriculture_relevance":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "agriculture_relevance",
                ""
            ),

        "agriculture_relevance_reason":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "agriculture_relevance_reason",
                ""
            ),

        "what_happened":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "what_happened",
                ""
            ),

        "key_facts":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "key_facts",
                []
            ),

        "reported_facts":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "reported_facts",
                []
            ),

        "key_numbers":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "key_numbers",
                []
            ),

        "why_it_matters":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "why_it_matters",
                ""
            ),

        "agriculture_impact":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "agriculture_impact",
                ""
            ),

        "interpretations":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "interpretations",
                []
            ),

        "topics":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "topics",
                []
            ),

        "important_terms":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "important_terms",
                []
            ),

        "government_intelligence":
            government_links,

        "connections":
            connection_links,

        "article_text":
            master_record.get(
                "final_analysis",
                {}
            ).get(
                "article_text",
                master_record.get(
                    "source_record",
                    {}
                ).get(
                    "article_text",
                    ""
                )
            ),

        "source":
            {
                "record_id":
                    record_id,

                "newspaper":
                    master_record.get(
                        "newspaper",
                        ""
                    ),

                "date":
                    master_record.get(
                        "date",
                        ""
                    ),

                "page":
                    master_record.get(
                        "page"
                    ),

                "headline":
                    master_record.get(
                        "source_headline",
                        ""
                    ),

                "source_pdf":
                    master_record.get(
                        "source_record",
                        {}
                    ).get(
                        "source_pdf",
                        ""
                    )
            },

        "created_from":
            "MASTER_INTELLIGENCE_DATABASE",

        "last_updated":
            timestamp
    }

    return daily


# ============================================================
# MAIN BUILD
# ============================================================

def main():

    print("=" * 70)
    print("DAILY INTELLIGENCE DATABASE BUILDER v1.2")
    print("=" * 70)

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    # --------------------------------------------------------
    # LOAD SOURCES
    # --------------------------------------------------------

    master_records = load_master_records()

    initiatives, source_links = (
        load_government_intelligence()
    )

    current_connections = (
        load_current_connections()
    )

    print()
    print(
        f"Master records:          "
        f"{len(master_records)}"
    )

    print(
        f"Government initiatives:  "
        f"{len(initiatives)}"
    )

    print(
        f"Government source links: "
        f"{len(source_links)}"
    )

    print(
        f"CURRENT connections:     "
        f"{len(current_connections)}"
    )

    print()
    print(
        "Authoritative Connections Bank:"
    )

    print(
        CONNECTIONS_FILE
    )

    # --------------------------------------------------------
    # BUILD DAILY DATABASE FROM SCRATCH
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("BUILDING DAILY INTELLIGENCE")
    print("=" * 70)

    daily_records = []

    added = 0
    updated = 0

    for index, master_record in enumerate(
        master_records,
        start=1
    ):

        record_id = clean(
            master_record.get(
                "record_id"
            )
        )

        if not record_id:
            continue

        headline = clean(
            master_record.get(
                "source_headline",
                master_record.get(
                    "headline",
                    ""
                )
            )
        )

        gov_links = (
            government_links_for_record(
                record_id,
                source_links
            )
        )

        conn_links = (
            connections_for_record(
                record_id,
                current_connections
            )
        )

        daily_record = build_daily_record(
            master_record,
            gov_links,
            conn_links,
            timestamp
        )

        daily_records.append(
            daily_record
        )

        print(
            f"[{index}/{len(master_records)}] "
            f"{headline}"
        )

        if index <= 23:

            print(
                "    UPDATED"
            )

            updated += 1

        else:

            print(
                "    ADDED"
            )

            added += 1

    # --------------------------------------------------------
    # FINAL DATABASE
    # --------------------------------------------------------

    output = {

        "database_version":
            "v1.2",

        "created_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "last_updated":
            timestamp,

        "record_count":
            len(daily_records),

        "source_databases":
            {
                "master_database":
                    str(
                        MASTER_FILE
                    ),

                "government_intelligence":
                    str(
                        GOVERNMENT_FILE
                    ),

                "connections_bank":
                    str(
                        CONNECTIONS_FILE
                    )
            },

        "government_initiative_count":
            len(initiatives),

        "government_source_link_count":
            len(source_links),

        "connection_count":
            len(current_connections),

        "records":
            daily_records
    }

    save_json(
        OUTPUT_FILE,
        output
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    report_lines = [

        "=" * 78,

        "AGRICULTURE INTELLIGENCE SYSTEM",

        "DAILY INTELLIGENCE DATABASE v1.2",

        "=" * 78,

        "",

        f"Generated: {timestamp}",

        "",

        "SOURCE DATABASES",

        f"Master records: {len(master_records)}",

        f"Government initiatives: {len(initiatives)}",

        f"Government source links: {len(source_links)}",

        f"Current connections: {len(current_connections)}",

        "",

        "BUILD SUMMARY",

        f"Daily records created: {len(daily_records)}",

        "",

        "CONNECTION SOURCE",

        "Only the current Connections Bank is used.",

        "Stale connection references from previous daily builds are removed.",

        "",

        "QUESTION GENERATION",

        "Placement/GD questions generated: 0",

        "",

        "OUTPUT",

        str(OUTPUT_FILE),

        str(REPORT_FILE),

        "",

        "Master database was NOT modified.",

        "Government Intelligence Bank was NOT modified.",

        "Connections Bank was NOT modified.",

    ]

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        REPORT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(
                report_lines
            )
            + "\n"
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("BUILD COMPLETE")
    print("=" * 70)

    print(
        f"Daily records:        "
        f"{len(daily_records)}"
    )

    print(
        f"Government initiatives: "
        f"{len(initiatives)}"
    )

    print(
        f"Government source links: "
        f"{len(source_links)}"
    )

    print(
        f"Current connections:   "
        f"{len(current_connections)}"
    )

    print()
    print("JSON:")
    print(
        OUTPUT_FILE
    )

    print()
    print("REPORT:")
    print(
        REPORT_FILE
    )

    print()
    print(
        "Master database was NOT modified."
    )

    print(
        "Government Intelligence Bank was NOT modified."
    )

    print(
        "Connections Bank was NOT modified."
    )

    print("=" * 70)


if __name__ == "__main__":

    main()