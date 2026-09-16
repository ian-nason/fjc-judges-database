#!/usr/bin/env python3
"""Build fjc-judges.duckdb from the FJC Biographical Directory of Article III Federal Judges.
Source: https://www.fjc.gov/history/judges/biographical-directory-article-iii-federal-judges-export
(seven CSV exports, updated by the FJC as judges are appointed; run ./download_data.sh first).
Tables (one per export; the wide judges.csv is the same data denormalised and is not loaded):
    judges                          one row per judge (demographics.csv)
    federal_judicial_service        one row per Article III appointment: court, nomination -> confirmation ->
                                    commission dates, chief-judge service, senior status, termination
    education                       one row per degree
    professional_career             one row per career entry (free text, ordered)
    other_federal_judicial_service  one row per non-Article III federal judicial post (magistrate, bankruptcy ...)
    other_nominations_recess        one row per unsuccessful nomination or recess appointment (free text)
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from datapond_build import Checker, build_columns_table, ensure_metadata, export_dictionary
from datapond_build.session import connect

RAW = Path("data/raw")
DEFAULT_OUTPUT = "fjc-judges.duckdb"
SOURCE_URL = "https://www.fjc.gov/history/judges/biographical-directory-article-iii-federal-judges-export"
FILES = {
    "judges": "demographics.csv",
    "federal_judicial_service": "federal-judicial-service.csv",
    "education": "education.csv",
    "professional_career": "professional-career.csv",
    "other_federal_judicial_service": "other-federal-judicial-service.csv",
    "other_nominations_recess": "other-nominations-recess.csv",
}
TABLE_DESCRIPTIONS = {
    "judges": "One row per Article III judge, 1789-present: name, birth and death date/place, gender, race or ethnicity (FJC Biographical Directory)",
    "federal_judicial_service": "One row per Article III appointment: court, appointing president and party, ABA rating, seat, nomination, "
                                "committee, Senate vote and confirmation dates, commission date, chief-judge service, senior status, termination and reason",
    "education": "One row per degree: school, degree, year",
    "professional_career": "One row per professional-career entry as written by the FJC (clerkships, practice, prior judgeships), in sequence",
    "other_federal_judicial_service": "One row per non-Article III federal judicial post (magistrate judge, bankruptcy judge, territorial court ...)",
    "other_nominations_recess": "One row per unsuccessful nomination or recess appointment, as written by the FJC",
}
JOIN_HINTS = {
    "nid": "FJC judge identifier; joins every table",
    "jid": "Legacy FJC judge id (judges table only)",
    "sequence": "Order of the entry within the judge's record",
    "seat_id": "Court seat identifier; successive holders of one seat share it",
}
DATE_COLS = {"recess_appointment_date", "nomination_date", "committee_referral_date", "hearing_date", "committee_action_date",
             "confirmation_date", "commission_date", "service_as_chief_judge_begin", "service_as_chief_judge_end",
             "2nd_service_as_chief_judge_begin", "2nd_service_as_chief_judge_end", "senior_status_date", "termination_date"}
INT_COLS = {"nid", "jid", "sequence", "birth_month", "birth_day", "birth_year", "death_month", "death_day", "death_year", "degree_year"}


RENAME = {"2nd_service_as_chief_judge_begin": "chief_judge_2nd_begin", "2nd_service_as_chief_judge_end": "chief_judge_2nd_end",
          "service_as_chief_judge_begin": "chief_judge_begin", "service_as_chief_judge_end": "chief_judge_end",
          "other_nominations_recess_appointments": "description", "other_federal_judicial_service": "description",
          "professional_career": "description"}


def norm(name: str) -> str:
    """Export header -> snake_case key (DuckDB renders the header's embedded newline as ', ')."""
    return "_".join(re.sub(r"[,/]", " ", name).replace("\n", " ").split()).lower()


def load(con, t: str) -> int:
    path = RAW / FILES[t]
    con.execute(f"CREATE OR REPLACE TABLE _raw AS SELECT * FROM read_csv('{path}', all_varchar=true, header=true, sample_size=-1)")
    header = [r[0] for r in con.execute("DESCRIBE _raw").fetchall()]
    exprs, seen = [], set()
    for h in header:
        if not h.strip() or h.startswith("column"):  # trailing unnamed columns in other-federal-judicial-service.csv
            continue
        key = norm(h)
        c = RENAME.get(key, key)
        if c in seen:
            raise RuntimeError(f"{t}: duplicate column {c}")
        seen.add(c)
        clean = f'NULLIF(TRIM("{h}"), \'\')'
        if key in DATE_COLS:
            exprs.append(f"TRY_CAST({clean} AS DATE) AS {c}")
        elif c in INT_COLS:
            exprs.append(f"TRY_CAST({clean} AS INTEGER) AS {c}")
        elif c == "ayes_nays":
            exprs.append(f"{clean} AS {c}")
        else:
            exprs.append(f"{clean} AS {c}")
    con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT {', '.join(exprs)} FROM _raw")
    con.execute("DROP TABLE _raw")
    return con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]


def run_validation(con) -> int:
    ck = Checker("Validation")
    ck.query(con, "judges: nid unique", "SELECT COUNT(*) - COUNT(DISTINCT nid) FROM judges", lambda n: n == 0, str)
    ck.query(con, "judges: >= 4,000 judges", "SELECT COUNT(*) FROM judges", lambda n: n >= 4000, lambda n: f"{n:,}")
    for t in FILES:
        if t != "judges":
            ck.query(con, f"{t}: every nid exists in judges", f"SELECT COUNT(*) FROM {t} x LEFT JOIN judges j USING (nid) WHERE j.nid IS NULL", lambda n: n == 0, str)
    ck.query(con, "federal_judicial_service: commission_date parsed (> 99%)",
             "SELECT COUNT(commission_date) * 1.0 / COUNT(*) FROM federal_judicial_service", lambda v: v > 0.99, lambda v: f"{v:.2%}")
    ck.query(con, "federal_judicial_service: earliest commission 1789", "SELECT MIN(commission_date) FROM federal_judicial_service", lambda d: str(d).startswith("1789"), str)
    ck.query(con, "federal_judicial_service: a 2026 commission exists", "SELECT MAX(commission_date) FROM federal_judicial_service", lambda d: str(d) >= "2025-01-01", str)
    ck.query(con, "federal_judicial_service: (nid, sequence) unique", "SELECT COUNT(*) - COUNT(DISTINCT (nid, sequence)) FROM federal_judicial_service", lambda n: n == 0, str)
    ck.query(con, "federal_judicial_service: court_type populated", "SELECT COUNT(court_type) * 1.0 / COUNT(*) FROM federal_judicial_service", lambda v: v > 0.999, lambda v: f"{v:.2%}")
    ck.query(con, "judges: birth_year populated (> 95%)", "SELECT COUNT(birth_year) * 1.0 / COUNT(*) FROM judges", lambda v: v > 0.95, lambda v: f"{v:.1%}")
    return ck.report()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT))
    a = ap.parse_args()
    t0 = time.time()
    con = connect(a.output, fresh=True, memory_limit="2GB", threads=2)
    counts = {t: load(con, t) for t in FILES}
    for t, n in counts.items():
        print(f"  {t}: {n:,} rows")
    con.execute("""
        CREATE VIEW v_current_judges AS
        SELECT j.nid, j.last_name, j.first_name, s.court_type, s.court_name, s.appointment_title, s.appointing_president,
               s.party_of_appointing_president, s.commission_date, s.senior_status_date
        FROM federal_judicial_service s JOIN judges j USING (nid)
        WHERE s.termination_date IS NULL""")
    print("\nMetadata + dictionary")
    ensure_metadata(con, descriptions=TABLE_DESCRIPTIONS, tables=list(FILES), source_url=SOURCE_URL, license="Public domain", replace=True)
    build_columns_table(con, join_hints=JOIN_HINTS, tables=list(FILES))
    export_dictionary(con, Path("DICTIONARY.md"), title="fjc-judges Data Dictionary",
                      intro=[f"Source: [FJC Biographical Directory of Article III Federal Judges, export files]({SOURCE_URL}).",
                             "Column names are the export headers in snake_case; dates are DATE; free-text entries are as the FJC wrote them.",
                             "`v_current_judges` lists appointments with no termination date (active and senior judges)."],
                      style="registry", tables=list(FILES))
    con.execute("CHECKPOINT")
    failures = run_validation(con)
    con.close()
    print(f"\nBUILD DONE in {time.time() - t0:.0f}s; " + ", ".join(f"{k} {v:,}" for k, v in counts.items()) + f"; {a.output.stat().st_size / 1024**2:.0f} MB")
    if failures:
        print(f"BUILD FAILED: {failures} check(s) failed -- do not publish this file")
        sys.exit(1)


if __name__ == "__main__":
    main()
