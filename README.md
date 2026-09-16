# FJC Biographical Directory of Article III Federal Judges as a DuckDB database

Every judge who has served on a U.S. Article III court since 1789, from the Federal Judicial
Center's [Biographical Directory export](https://www.fjc.gov/history/judges/biographical-directory-article-iii-federal-judges-export):
who they are, every appointment with its nomination-to-commission timeline, education, career
and other federal judicial service. Companion to [fjc](https://github.com/ian-nason/fjc-database)
(the case-level Integrated Database) and [scdb](https://github.com/ian-nason/scdb-database).

| Table | One row per | Rows |
|-------|-------------|-----:|
| `judges` | judge: name, birth/death date and place, gender, race or ethnicity | 4,074 |
| `federal_judicial_service` | Article III appointment: court, appointing president and party, ABA rating, seat, nomination, committee, Senate vote, confirmation, commission, chief-judge service, senior status, termination | 4,774 |
| `education` | degree | 8,153 |
| `professional_career` | career entry (free text, in sequence) | 19,313 |
| `other_federal_judicial_service` | non-Article III federal judicial post (magistrate, bankruptcy, territorial ...) | 618 |
| `other_nominations_recess` | unsuccessful nomination or recess appointment (free text) | 836 |

`nid` joins everything. `v_current_judges` lists appointments with no termination date
(active and senior judges). Columns and null rates: `DICTIONARY.md`.

## Quick start

```python
import datapond
con = datapond.connect("fjc-judges")
con.sql("""
    SELECT party_of_appointing_president AS party, EXTRACT(YEAR FROM commission_date) // 10 * 10 AS decade, COUNT(*) AS judges
    FROM federal_judicial_service WHERE court_type = 'U.S. Court of Appeals'
    GROUP BY 1, 2 ORDER BY 2, 1
""").show()
```

```sql
-- days from nomination to confirmation, by president
SELECT appointing_president, COUNT(*) AS n, ROUND(AVG(confirmation_date - nomination_date)) AS avg_days
FROM federal_judicial_service WHERE nomination_date >= '1981-01-01' GROUP BY 1 ORDER BY MIN(nomination_date);
```

## Researcher caveats

- The FJC updates the export as judges are commissioned or leave; this build is a snapshot
  (`_metadata.built_at`). Rebuild to refresh.
- `judges.csv` on the FJC site is the same data denormalised into 225 columns; it is not
  loaded. The wide-to-long export files are.
- Free-text tables (`professional_career`, `other_nominations_recess`,
  `other_federal_judicial_service.description`) are the FJC's prose; parse with care.
- `seat_id` links successive holders of one seat; it is blank for some historical courts.
- Dates before 1900 are exact where the FJC records them; `commission_date` is missing for
  0.7% of appointments (mostly 18th-19th century).

## Build

```bash
uv sync && ./download_data.sh && uv run python build_database.py && uv run python publish_to_hf.py --verify
```

## License

Code: MIT. Data: public domain (Federal Judicial Center).
