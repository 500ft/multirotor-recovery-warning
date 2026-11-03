"""Inventory the pinned 4TU v2 propeller-damage metadata without reading flight arrays."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Data/4tu-qualification/source"
OUTPUT = ROOT / "Data/4tu-qualification/results.json"
FILES = (
    "README_flight_data.txt",
    "DragonFly_file_log.csv",
    "DragonFlyConfig_CGI.json",
    "HoverFly_FIDINFO.json",
    "zip-directory.json",
    "datacite.json",
)


def main():
    source_hashes = {
        name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
        for name in FILES
    }
    registry = json.loads((SOURCE / "datacite.json").read_text())["data"]["attributes"]
    members = json.loads((SOURCE / "zip-directory.json").read_text())
    files = [member["name"] for member in members if member["size"]]
    flight_arrays = [name for name in files if "/Onboard/" in name and name.endswith(".csv")]
    with (SOURCE / "DragonFly_file_log.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    config = json.loads((SOURCE / "DragonFlyConfig_CGI.json").read_text())
    hover_damage = json.loads((SOURCE / "HoverFly_FIDINFO.json").read_text())
    readme = (SOURCE / "README_flight_data.txt").read_text()

    result = {
        "source": {
            "dataset_doi": registry["doi"],
            "version": registry["version"],
            "license": [
                {"name": item.get("rights"), "url": item.get("rightsUri")}
                for item in registry["rightsList"]
            ],
            "related_publication_doi": next(
                item["relatedIdentifier"] for item in registry["relatedIdentifiers"]
                if item["relationType"] == "IsSupplementTo"
                and item["relatedIdentifierType"] == "DOI"
            ),
            "source_sha256": source_hashes,
            "scope": "Archive directory and metadata only; no flight time series read",
        },
        "archive": {
            "members": len(members),
            "nonempty_files": len(files),
            "onboard_csv_by_vehicle": dict(sorted(Counter(
                name.split("/")[0] for name in flight_arrays
            ).items())),
            "non_flight_files": sorted(set(files) - set(flight_arrays)),
        },
        "dragonfly_log": {
            "rows": len(rows),
            "distinct_flight_ids": len({row["Flight ID"] for row in rows}),
            "empty_fields": {
                field: sum(not row[field].strip() for row in rows)
                for field in ("LOC Type", "time LOC (start)", "time LOC (end)", "Video Path")
            },
            "observed_values": {
                field: sorted({row[field] for row in rows})
                for field in ("Batteries", "Mass", "Flight controller", "Has OT data", "Drone Config File")
            },
        },
        "dragonfly_config": {
            "mass_unqualified": config["mass"],
            "flight_controller": config["flight controller"],
            "rotor_config": config["rotor config"],
            "inertia_warning_in_readme": "moment of inertia is not accurate" in readme,
        },
        "hoverfly_damage_identifiers": len(hover_damage),
        "decision": {
            "metadata_and_reuse": "qualified",
            "native_timing_and_alignment": "unverified; no flight arrays inspected",
            "configuration_for_physics_model": "unresolved mass/controller discrepancy and inaccurate inertia",
            "independent_recovery_endpoints": "unavailable in inspected archive metadata and paper methods",
            "registered_recovery_warning_comparison": "ineligible",
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
