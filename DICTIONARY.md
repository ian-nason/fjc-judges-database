# fjc-judges Data Dictionary

Source: [FJC Biographical Directory of Article III Federal Judges, export files](https://www.fjc.gov/history/judges/biographical-directory-article-iii-federal-judges-export).
Column names are the export headers in snake_case; full dates are DATE; free-text entries are as the FJC wrote them.
Chief-judge service is often year-only: use the four chief_judge_*_year columns. Existing DATE columns remain NULL for year-only values. birth_year_raw and degree_year_raw preserve approximate years and ranges.
`v_current_judges` lists appointments with no termination date (active and senior judges).

## judges

One row per Article III judge, 1789-present: name, birth and death date/place, gender, race or ethnicity (FJC Biographical Directory)

Rows: 4,077

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| nid | INTEGER | 0.0% | 10226111 | FJC judge identifier; joins every table |
| jid | INTEGER | 0.0% | 1 | Legacy FJC judge id (judges table only) |
| last_name | VARCHAR | 0.0% | Abelson |  |
| first_name | VARCHAR | 0.0% | A. |  |
| middle_name | VARCHAR | 12.3% | A. |  |
| suffix | VARCHAR | 90.3% | II |  |
| birth_month | INTEGER | 42.1% | 1 |  |
| birth_day | INTEGER | 42.2% | 1 |  |
| birth_year | INTEGER | 0.0% | 1732 |  |
| birth_city | VARCHAR | 0.6% | (Belmont), Philadelphia |  |
| birth_state | VARCHAR | 0.0% | AK |  |
| death_month | INTEGER | 41.5% | 1 |  |
| death_day | INTEGER | 41.5% | 1 |  |
| death_year | INTEGER | 41.5% | 1790 |  |
| death_city | VARCHAR | 58.5% | (Belmont), Philadelphia |  |
| death_state | VARCHAR | 58.3% | AK |  |
| gender | VARCHAR | 0.0% | Declined to Report |  |
| race_or_ethnicity | VARCHAR | 0.0% | African American |  |
| birth_year_raw | VARCHAR | 0.0% | 1732 |  |

## federal_judicial_service

One row per Article III appointment: court, appointing president and party, ABA rating, seat, nomination, committee, Senate vote and confirmation dates, commission date, chief-judge service, senior status, termination and reason

Rows: 4,777

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| nid | INTEGER | 0.0% | 10226111 | FJC judge identifier; joins every table |
| sequence | INTEGER | 0.0% | 1 | Order of the entry within the judge's record |
| judge_name | VARCHAR | 0.0% | Abelson, Adam Ben |  |
| court_type | VARCHAR | 0.0% | Other |  |
| court_name | VARCHAR | 0.0% | Circuit Court of the District of Columbia |  |
| appointment_title | VARCHAR | 0.0% | Associate Judge |  |
| appointing_president | VARCHAR | 0.0% | Abraham Lincoln |  |
| party_of_appointing_president | VARCHAR | 0.8% | Democratic |  |
| reappointing_president | VARCHAR | 99.8% | Calvin Coolidge |  |
| party_of_reappointing_president | VARCHAR | 99.8% | Republican |  |
| aba_rating | VARCHAR | 40.9% | Exceptionally Well Qualified |  |
| seat_id | VARCHAR | 0.0% | 1801CC10101 | Court seat identifier; successive holders of one seat share it |
| statute_authorizing_new_seat | VARCHAR | 75.9% | 1 Stat. 126 |  |
| recess_appointment_date | DATE | 93.1% | 1789-11-18 |  |
| nomination_date | DATE | 3.4% | 1789-09-24 |  |
| committee_referral_date | DATE | 7.4% | 1826-05-08 |  |
| hearing_date | DATE | 35.6% | 1890-02-17 |  |
| judiciary_committee_action | VARCHAR | 3.4% | No Committee before December 10, 1816 |  |
| committee_action_date | DATE | 7.8% | 1826-05-22 |  |
| senate_vote_type | VARCHAR | 3.8% | Roll Call |  |
| ayes_nays | VARCHAR | 78.0% | 10//14 |  |
| confirmation_date | DATE | 4.0% | 1789-09-25 |  |
| commission_date | DATE | 0.7% | 1789-09-26 |  |
| chief_judge_begin | DATE | 100.0% |  |  |
| chief_judge_end | DATE | 100.0% |  |  |
| chief_judge_2nd_begin | DATE | 100.0% |  |  |
| chief_judge_2nd_end | DATE | 100.0% |  |  |
| senior_status_date | DATE | 56.5% | 1919-10-06 |  |
| termination | VARCHAR | 30.8% | Abolition of Court |  |
| termination_date | DATE | 30.8% | 1790-05-18 |  |
| chief_judge_begin_year | INTEGER | 73.4% | 1801 |  |
| chief_judge_end_year | INTEGER | 75.6% | 1802 |  |
| chief_judge_2nd_begin_year | INTEGER | 99.9% | 1966 |  |
| chief_judge_2nd_end_year | INTEGER | 99.9% | 1968 |  |

## education

One row per degree: school, degree, year

Rows: 8,159

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| nid | INTEGER | 0.0% | 10226111 | FJC judge identifier; joins every table |
| sequence | INTEGER | 0.0% | 1 | Order of the entry within the judge's record |
| judge_name | VARCHAR | 0.0% | Abelson, Adam Ben |  |
| school | VARCHAR | 0.0% | Abilene Christian University |  |
| degree | VARCHAR | 12.1% | A.A. |  |
| degree_year | INTEGER | 4.0% | 1751 |  |
| degree_year_raw | VARCHAR | 4.0% | 1751 |  |

## professional_career

One row per professional-career entry as written by the FJC (clerkships, practice, prior judgeships), in sequence

Rows: 19,330

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| nid | INTEGER | 0.0% | 10226111 | FJC judge identifier; joins every table |
| sequence | INTEGER | 0.0% | 1 | Order of the entry within the judge's record |
| judge_name | VARCHAR | 0.0% | Abelson, Adam Ben |  |
| description | VARCHAR | 0.0% | Accountant, Chicago, Illinois, 1947-1949 |  |

## other_federal_judicial_service

One row per non-Article III federal judicial post (magistrate judge, bankruptcy judge, territorial court ...)

Rows: 618

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| nid | INTEGER | 0.0% | 10236621 | FJC judge identifier; joins every table |
| sequence | INTEGER | 0.0% | 1 | Order of the entry within the judge's record |
| judge_name | VARCHAR | 0.0% | Abelson, Adam Ben |  |
| type | VARCHAR | 0.0% | Alien Terrorist Removal Court |  |
| description | VARCHAR | 0.0% | Appellate Military Judge, U.S. Army Court of Military Review (now U.S. Army C... |  |

## other_nominations_recess

One row per unsuccessful nomination or recess appointment, as written by the FJC

Rows: 836

| Column | Type | Nulls | Example | Join |
|--------|------|-------|---------|------|
| nid | INTEGER | 0.0% | 10226111 | FJC judge identifier; joins every table |
| sequence | INTEGER | 0.0% | 1 | Order of the entry within the judge's record |
| judge_name | VARCHAR | 0.0% | Abudu, Nancy Gbana |  |
| description | VARCHAR | 0.0% | Nominated to Court of Claims, August 25, 1959; no Senate vote |  |
