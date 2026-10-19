# FJC Biographical Directory of Article III Federal Judges as a DuckDB database

Every judge who has served on a U.S. Article III court since 1789, from the Federal Judicial
Center's [Biographical Directory export](https://www.fjc.gov/history/judges/biographical-directory-article-iii-federal-judges-export):
who they are, every appointment with its nomination-to-commission timeline, education, career
and other federal judicial service. Companion to [fjc](https://github.com/ian-nason/fjc-database)
(the case-level Integrated Database) and [scdb](https://github.com/ian-nason/scdb-database).

| Table | One row per | Rows |
|-------|-------------|-----:|
| `judges` | judge: name, birth/death date and place, gender, race or ethnicity | 4,077 |
| `federal_judicial_service` | Article III appointment: court, appointing president and party, ABA rating, seat, nomination, committee, Senate vote, confirmation, commission, chief-judge service, senior status, termination | 4,777 |
| `education` | degree | 8,159 |
| `professional_career` | career entry (free text, in sequence) | 19,330 |
| `other_federal_judicial_service` | non-Article III federal judicial post (magistrate, bankruptcy, territorial ...) | 618 |
| `other_nominations_recess` | unsuccessful nomination or recess appointment (free text) | 836 |

`nid` links the six tables within this directory. Child tables have several rows per judge, so count distinct `nid` values for people and appointment rows for service records. For CourtListener, join `courtlistener.judges.fjc_id` to this database's `judges.jid`, not `nid`.

`v_current_judges` lists appointments with no termination date as recorded in the October 17, 2026 snapshot (active and senior service). It is not a live roster. Columns and null rates: [DICTIONARY.md](DICTIONARY.md).

## Quick start

The database file is 3.5 MiB on disk.

Install/upgrade Python with `python -m pip install --upgrade datapond` (the examples use 0.1.5), or install released R datapond from [CRAN](https://cran.r-project.org/package=datapond) with `install.packages("datapond")`. R 0.1.1 remains a separate development version. Python 0.1.1 cannot attach the hyphenated `fjc-judges` ID; upgrade before running this example.

Remote queries run on your machine. File size is disk storage, not required RAM; selected columns reduce transfer, but filters and a final `LIMIT` do not guarantee a small scan. A 128 MiB setting limits DuckDB's buffer pool, not the whole Python/R process. Larger queries can fail with spill disabled. Download only when you have room for the file, temporary download bytes and any existing copy. The package examples below set limits immediately after connecting. For settings before attachment, use the [direct SQL quick start in the dataset card](https://huggingface.co/datasets/Nason/fjc-judges-database#quick-start) in a DuckDB SQL client.

```python
import datapond
con = datapond.connect("fjc-judges")
con.execute("SET memory_limit='128MiB'; SET threads=1; SET max_temp_directory_size='0B'")
con.sql("""
    SELECT party_of_appointing_president AS party, EXTRACT(YEAR FROM commission_date) // 10 * 10 AS decade, COUNT(*) AS appointments
    FROM federal_judicial_service WHERE court_type = 'U.S. Court of Appeals'
    GROUP BY 1, 2 ORDER BY 2, 1
""").show()
con.close()
```

```r
con <- datapond::dp_connect("fjc-judges")
DBI::dbExecute(con, "SET memory_limit='128MiB'; SET threads=1; SET max_temp_directory_size='0B'")
DBI::dbGetQuery(con, "SELECT count(*) AS judges FROM judges")
datapond::dp_disconnect(con)
```

The following SQL assumes this database is the default catalog. Its count is appointment records, not distinct judges; the average uses only non-NULL date differences.

```sql
-- days from nomination to confirmation, by president
SELECT appointing_president, COUNT(*) AS appointments, ROUND(AVG(confirmation_date - nomination_date)) AS avg_days
FROM federal_judicial_service WHERE nomination_date >= '1981-01-01' GROUP BY 1 ORDER BY MIN(nomination_date);
```

## October 17, 2026 refresh

37,797 rows across six tables, including 4,077 judges. Source identities, hashes and checks are in
[`docs/refresh-2026-10-17.json`](docs/refresh-2026-10-17.json). Commission dates run through October 2, 2026.

Chief-judge service exports contain years, not full dates. The four `chief_judge_*_year`
INTEGER columns retain these values; the existing DATE columns remain NULL for year-only
entries. This recovers 2,447 populated year values previously lost during conversion.
`birth_year_raw` and `degree_year_raw` preserve approximate years and ranges such as
`ca. 1793` and `1949-1951`; the corresponding INTEGER remains NULL when precision is uncertain.

## Researcher caveats

- The FJC updates the export as judges are commissioned or leave; this build is a snapshot
  (`_metadata.built_at`). A new audited build is needed to refresh it; no automatic refresh is promised.
- `judges.csv` on the FJC site is the same data denormalised into 225 columns; it is not
  loaded. The wide-to-long export files are.
- Free-text tables (`professional_career`, `other_nominations_recess`,
  `other_federal_judicial_service.description`) are the FJC's prose; parse with care.
- `seat_id` links successive holders of one seat; it is blank for some historical courts.
- Dates before 1900 are exact where the FJC records them; `commission_date` is missing for
  0.7% of appointments (mostly 18th-19th century).

## Build

```bash
work="/path/to/new-refresh"
mkdir -p "$work"
./download_data.sh --refresh --output-dir "$work/data/raw"
.venv/bin/python build_database.py --raw-dir "$work/data/raw" \
  --output "$work/fjc-judges.duckdb" --dictionary "$work/DICTIONARY.md"
.venv/bin/python test_refresh.py -v
```

The builder refuses an existing database, WAL or dictionary, and rejects unparseable typed values before loading a table. Approximate birth/degree years remain available as raw text. It defaults to 1 GB DuckDB memory, one
thread and 256 MiB maximum spill; `DATAPOND_MEMORY_LIMIT` and `DATAPOND_THREADS` override
the first two. The October refresh used 256 MB and one thread. Audit before publishing.
`publish_checked.py` validates the candidate hash and local queries, atomically uploads the
database/card/provenance, then verifies pinned and main remote checksums and queries. It
uses existing authentication and an installed HTTP extension; it does not install software.

Published artifact: [immutable October snapshot](https://huggingface.co/datasets/Nason/fjc-judges-database/commit/ed77e33910daecf8467fba011743b1d0d6b0a2df). Both the pinned artifact and `main` passed remote hash, count and precision checks. See [`docs/publication-2026-10-17.json`](docs/publication-2026-10-17.json).

### Audited publication and recovery

The checked publisher requires Python 3.11 or later. It defaults to standard LFS transfer with one upload worker (`HF_HUB_DISABLE_XET=1`) to avoid unnecessary transfer-library thread pools.

After independently auditing the source snapshot, generate a provenance JSON with
`source_snapshot`, `validation` (including SHA-256, byte size, table counts,
`chief_year_counts` and commission-date coverage), and `dictionary_sha256` from the
dictionary generated with that candidate. The checked publisher accepts this nested
report or a separate flat validation report. It verifies the candidate, counts,
dictionary and license before contacting the publication API.

```bash
.venv/bin/python publish_checked.py --db "$work/fjc-judges.duckdb" \
  --provenance docs/refresh-2026-10-17.json --dictionary "$work/DICTIONARY.md" \
  --expected-parent PREVIOUS_HF_COMMIT --receipt "$work/publication.json" --dry-run
```

Inspect the rendered `publication.README.md`, then run the same command without
`--dry-run` to upload all four files in one commit. If upload succeeds but remote
verification fails, retain the receipt and retry the same arguments with
`--verify-only --commit UPLOADED_COMMIT` (omit `--dry-run`). This sends no upload.
Both pinned and `main` hashes, table counts and source-precision queries must pass.
LFS hashes are checked directly; plain blobs are hashed with a bounded streamed read.

The receipt records the previous immutable Hugging Face commit. To roll back an
incorrect publication, retrieve and verify the prior database and README at that
revision, then restore them in one new commit guarded by the current remote head.
The previous October baseline had no dictionary or source-provenance file: also
remove the two newly introduced hosted metadata paths in that rollback commit,
while retaining their local evidence. Leave `.gitattributes` unchanged.
Do not reset history, delete the retained local source/candidate, or automatically
overwrite a head that another publisher has changed.

## License

Code: MIT. Data: public domain (Federal Judicial Center).

The reviewed current hosted card is retained in [HF-README.md](HF-README.md). The checked publisher still generates future cards from `card.yaml`; that template includes recurring reader guidance. Compare the generated card against this reviewed copy before upload. For a future release, update counts and version links, retain the guidance and caveats, and inspect the rendered card before upload.
