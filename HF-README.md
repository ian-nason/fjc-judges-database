---
license: other
license_name: public-domain
license_link: https://www.fjc.gov/history/judges
task_categories:
  - tabular-classification
  - tabular-regression
tags:
  - judges
  - federal-courts
  - judiciary
  - fjc
  - biographical
  - duckdb
  - datapond
pretty_name: FJC Biographical Directory of Article III Federal Judges (1789-present)
size_categories:
  - 10K<n<100K
---

# Federal Judges Biographical Database (FJC)

Every Article III federal judge since 1789 from the Federal Judicial Center's Biographical
Directory: demographics, every appointment with its nomination -> confirmation -> commission
timeline, chief-judge and senior-status dates, education, career, and other federal judicial
service. Six normalised tables joined on `nid`, plus `v_current_judges`.
Snapshot: October 17, 2026. Chief-judge year columns and raw birth/degree-year text
preserve source precision; no first-of-year dates are invented. Appointment counts are not distinct-judge counts. `v_current_judges` is current only as of this snapshot. Within this database join on `nid`; CourtListener `judges.fjc_id` joins this directory's `judges.jid`.
**37,797 rows across 6 tables.**

| Table | Description | Row Count | Column Count |
|---|---|---|---|
| `professional_career` | One row per professional-career entry as written by the FJC (clerkships, practice, prior judgeships), in sequence | 19,330 | 4 |
| `education` | One row per degree: school, degree, year | 8,159 | 7 |
| `federal_judicial_service` | One row per Article III appointment: court, appointing president and party, ABA rating, seat, nomination, committee, Senate vote and confirmation dates, commission date, chief-judge service, senior status, termination and reason | 4,777 | 34 |
| `judges` | One row per Article III judge, 1789-present: name, birth and death date/place, gender, race or ethnicity (FJC Biographical Directory) | 4,077 | 19 |
| `other_nominations_recess` | One row per unsuccessful nomination or recess appointment, as written by the FJC | 836 | 4 |
| `other_federal_judicial_service` | One row per non-Article III federal judicial post (magistrate judge, bankruptcy judge, territorial court ...) | 618 | 5 |

## Quick start

The database file is 3.5 MiB on disk.

```sql
SET memory_limit='128MiB'; SET threads=1; SET max_temp_directory_size='0B';
INSTALL httpfs; LOAD httpfs;
ATTACH 'https://huggingface.co/datasets/Nason/fjc-judges-database/resolve/ed77e33910daecf8467fba011743b1d0d6b0a2df/fjc-judges.duckdb' AS fjc_judges (READ_ONLY);

SELECT appointing_president, COUNT(*) AS appointments, ROUND(AVG(confirmation_date - nomination_date)) AS avg_days_to_confirm
FROM fjc_judges.federal_judicial_service WHERE nomination_date >= '1981-01-01'
GROUP BY 1 ORDER BY MIN(nomination_date);
```

Install/upgrade Python with `python -m pip install --upgrade datapond` (the examples use 0.1.5), or install released R datapond from [CRAN](https://cran.r-project.org/package=datapond) with `install.packages("datapond")`. R 0.1.1 remains a separate development version. The package ID is `fjc-judges`; Python 0.1.1 must be upgraded for that ID.

Remote queries run on your machine. File size is disk storage, not required RAM; selected columns reduce transfer, but filters and a final `LIMIT` do not guarantee a small scan. A 128 MiB setting limits DuckDB's buffer pool, not the whole Python/R process. Larger queries can fail with spill disabled. Download only when you have room for the file, temporary download bytes and any existing copy. The direct SQL above sets limits before attachment.

[Dictionary](https://huggingface.co/datasets/Nason/fjc-judges-database/blob/ed77e33910daecf8467fba011743b1d0d6b0a2df/DICTIONARY.md) · [Source and caveats](https://github.com/ian-nason/fjc-judges-database#researcher-caveats) · [Release provenance](https://huggingface.co/datasets/Nason/fjc-judges-database/blob/ed77e33910daecf8467fba011743b1d0d6b0a2df/sources-2026-10-17.json)

Build pipeline and caveats: https://github.com/ian-nason/fjc-judges-database
Source: https://www.fjc.gov/history/judges (public domain).
