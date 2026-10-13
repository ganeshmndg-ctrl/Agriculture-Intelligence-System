from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parent

CONNECTIONS_FILE = (
    BASE_DIR
    / "data"
    / "connections_bank_v1_1"
    / "CONNECTIONS_BANK_v1_1.json"
)


print("=" * 80)
print("CONNECTIONS INTELLIGENCE BANK")
print("INSPECTION")
print("=" * 80)

print()
print("Reading:")
print(CONNECTIONS_FILE)

if not CONNECTIONS_FILE.exists():

    print()
    print("ERROR: Connections Bank file not found.")
    print(CONNECTIONS_FILE)
    raise SystemExit(1)


with open(
    CONNECTIONS_FILE,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


connections = (
    data.get(
        "connections",
        []
    )
    if isinstance(data, dict)
    else []
)


print()
print(
    f"Total connections: {len(connections)}"
)


for connection in connections:

    print()
    print("-" * 80)

    print(
        f"Connection ID: "
        f"{connection.get('connection_id', '')}"
    )

    print(
        f"Type: "
        f"{connection.get('connection_type', '')}"
    )

    print(
        f"Relationship type: "
        f"{connection.get('relationship_type', '')}"
    )

    print(
        f"Source records: "
        f"{connection.get('source_record_ids', [])}"
    )

    print(
        f"Source events: "
        f"{connection.get('source_event_ids', [])}"
    )

    print(
        f"Entities: "
        f"{connection.get('entities', [])}"
    )

    print(
        f"Relationship: "
        f"{connection.get('relationship', '')}"
    )

    print(
        f"Chain: "
        f"{connection.get('chain', [])}"
    )

    print(
        f"Agriculture relevance: "
        f"{connection.get('agriculture_relevance', '')}"
    )

    print(
        f"Placement relevance: "
        f"{connection.get('placement_relevance', '')}"
    )

    print(
        f"Confidence: "
        f"{connection.get('confidence', '')}"
    )

    print()

    print("Explanation:")
    print(
        connection.get(
            "explanation",
            ""
        )
    )

    print()

    print("Evidence:")

    for evidence in connection.get(
        "evidence",
        []
    ):

        print(
            f"  - {evidence}"
        )


print()
print("=" * 80)
print("INSPECTION COMPLETE")
print("=" * 80)