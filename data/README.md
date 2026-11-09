# HousingOps local data

This folder intentionally excludes generated CSVs and the original Excel workbook from version control.

## Public source, required for reproduction

Obtain the N.C. A&T source workbook used in Milestone 1, titled **`Project Data.xlsx`** (Exhibit C: Current Site Data), and save it **exactly** at:

```text
data/raw/Project Data.xlsx
```

The `Demographics` worksheet has 25 properties and six historical term columns. The workbook was provided to the team for the approved project but **a verified public direct download URL is not currently included in this repository**. The team must provide graders access via an approved course attachment or stable download location before final submission.

Do not substitute a similarly named or updated workbook without checking the counts. [Source documentation](../docs/data_sources.md) describes the expected totals.

## Generated files

Run `scripts/clean_public_data.py` to create:

- `data/processed/housing_properties.csv`
- `data/processed/academic_terms.csv`
- `data/processed/occupancy_observations.csv`

Run `scripts/generate_synthetic.py --seed 532 --as-of 2026-10-28` to create 13 synthetic table CSVs and `manifest.json` under `data/processed/synthetic/`.

These files are recreated locally and excluded by `.gitignore`. No real student or RA records are part of this dataset.
