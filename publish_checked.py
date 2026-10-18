"""Publish an audited FJC candidate atomically; retry verification without uploading."""
import argparse
import dataclasses
import datetime
import hashlib
import json
import pathlib
import os
import re
import urllib.request

import duckdb
import yaml
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from huggingface_hub import HfApi, CommitOperationAdd
from datapond_build.publish import CardSpec, render_card


def checksum(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validation_report(document):
    report = document.get('validation', document)
    required = {'status', 'sha256', 'bytes', 'counts'}
    if not isinstance(report, dict) or not required <= report.keys():
        raise ValueError('Validation requires status, sha256, bytes and counts')
    if report['status'] != 'validated' or not re.fullmatch(r'[0-9a-f]{64}', report['sha256']):
        raise ValueError('Candidate is not validated')
    if not isinstance(report['bytes'], int) or report['bytes'] <= 0 or not report['counts']:
        raise ValueError('Invalid validation size or table counts')
    for table, count in report['counts'].items():
        if not re.fullmatch(r'[a-z_]+', table) or not isinstance(count.get('new'), int) or count['new'] < 0:
            raise ValueError('Invalid validated table count')
    return report


def remote_identity(api, spec, revision, size, sha):
    info = api.get_paths_info(spec.repo, [spec.file], repo_type='dataset', revision=revision)[0]
    if info.size != size:
        raise RuntimeError('Remote artifact size mismatch')
    if info.lfs is not None:
        actual_sha = info.lfs.sha256
        method = 'lfs-sha256'
    else:
        digest, received = hashlib.sha256(), 0
        url = f'https://huggingface.co/datasets/{spec.repo}/resolve/{revision}/{spec.file}'
        with urllib.request.urlopen(url, timeout=30) as response:
            while chunk := response.read(65536):
                received += len(chunk)
                if received > size:
                    raise RuntimeError('Remote artifact exceeds validated size')
                digest.update(chunk)
        if received != size:
            raise RuntimeError('Truncated remote artifact')
        actual_sha, method = digest.hexdigest(), 'streamed-sha256'
    if actual_sha != sha:
        raise RuntimeError('Remote artifact hash mismatch')
    return method


def verify_remote(api, spec, revision, report, tables):
    verified = {}
    con = duckdb.connect(config={'memory_limit': '128MB', 'threads': '1', 'max_temp_directory_size': '0B'})
    try:
        con.execute('LOAD httpfs')
        for ref in [revision, 'main']:
            identity = remote_identity(api, spec, ref, report['bytes'], report['sha256'])
            url = f'https://huggingface.co/datasets/{spec.repo}/resolve/{ref}/{spec.file}'
            con.execute(f"ATTACH '{url}' AS remote (READ_ONLY)")
            metadata = con.execute('SELECT table_name,row_count FROM remote._metadata ORDER BY table_name').fetchall()
            if metadata != tables:
                raise RuntimeError('Remote metadata mismatch')
            actual = {t: con.execute(f'SELECT COUNT(*) FROM remote."{t}"').fetchone()[0] for t, _ in tables}
            if actual != {t: n['new'] for t, n in report['counts'].items()}:
                raise RuntimeError('Remote table counts mismatch')
            years = con.execute('SELECT COUNT(chief_judge_begin_year), COUNT(chief_judge_end_year), COUNT(chief_judge_2nd_begin_year), COUNT(chief_judge_2nd_end_year), MAX(commission_date) FROM remote.federal_judicial_service').fetchone()
            if years[:4] != tuple(report['chief_year_counts']) or str(years[4]) != report['queries']['dates'][1]:
                raise RuntimeError('Remote date precision or coverage mismatch')
            verified[ref] = {'identity': identity, 'tables': metadata, 'actual_counts': actual, 'chief_years_and_latest_commission': years}
            con.execute('DETACH remote')
    finally:
        con.close()
    return verified


def main():
    p = argparse.ArgumentParser()
    for option in ['db', 'provenance', 'dictionary', 'receipt']:
        p.add_argument('--' + option, type=pathlib.Path, required=True)
    p.add_argument('--validation', type=pathlib.Path)
    p.add_argument('--expected-parent')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--verify-only', action='store_true')
    p.add_argument('--commit')
    a = p.parse_args()
    if a.verify_only:
        if a.dry_run or not a.commit or not re.fullmatch(r'[0-9a-f]{40}', a.commit):
            p.error('--verify-only requires a full --commit and cannot be combined with --dry-run')
    elif not a.expected_parent or not re.fullmatch(r'[0-9a-f]{40}', a.expected_parent):
        p.error('Upload/dry-run requires a full --expected-parent')

    repo = pathlib.Path(__file__).resolve().parent
    card_data = yaml.safe_load((repo / 'card.yaml').read_text())
    fields = {field.name for field in dataclasses.fields(CardSpec)}
    unknown = set(card_data) - fields - {'license_name', 'license_link'}
    if unknown:
        raise ValueError('Unsupported card fields: ' + str(sorted(unknown)))
    spec = CardSpec(**{key: value for key, value in card_data.items() if key in fields})
    if spec.repo != 'Nason/fjc-judges-database' or spec.file != 'fjc-judges.duckdb':
        raise RuntimeError('Unexpected publication destination')
    provenance = json.loads(a.provenance.read_text())
    snapshot = datetime.date.fromisoformat(provenance['source_snapshot']).isoformat()
    report = validation_report(json.loads((a.validation or a.provenance).read_text()))
    public_report = validation_report(provenance)
    sha, size = checksum(a.db), a.db.stat().st_size
    for candidate in (report, public_report):
        if candidate['sha256'] != sha or candidate['bytes'] != size or candidate['counts'] != report['counts']:
            raise RuntimeError('Candidate, validation and provenance differ')
    if checksum(a.dictionary) != provenance['dictionary_sha256']:
        raise RuntimeError('Dictionary differs from the validated build')
    if 'chief_judge_begin_year' not in a.dictionary.read_text():
        raise RuntimeError('Dictionary lacks the source precision columns')
    con = duckdb.connect(config={'memory_limit': '128MB', 'threads': '1', 'max_temp_directory_size': '0B'})
    try:
        escaped_path = str(a.db.resolve()).replace("'", "''")
        con.execute(f"ATTACH '{escaped_path}' AS fjc_judges (READ_ONLY)")
        tables = con.execute('SELECT table_name,row_count FROM fjc_judges._metadata ORDER BY table_name').fetchall()
        if dict(tables) != {t: n['new'] for t, n in report['counts'].items()}:
            raise RuntimeError('Metadata differs from validated counts')
        for table, n in tables:
            if con.execute(f'SELECT COUNT(*) FROM fjc_judges."{table}"').fetchone()[0] != n:
                raise RuntimeError('Metadata differs from actual table')
        years = con.execute('SELECT COUNT(chief_judge_begin_year), COUNT(chief_judge_end_year), COUNT(chief_judge_2nd_begin_year), COUNT(chief_judge_2nd_end_year), MAX(commission_date) FROM fjc_judges.federal_judicial_service').fetchone()
        if years[:4] != tuple(report['chief_year_counts']) or str(years[4]) != report['queries']['dates'][1]:
            raise RuntimeError('Local year precision or coverage differs from validation')
        example = con.execute(spec.quick_start_sql).fetchall()
    finally:
        con.close()
    card = render_card(spec, a.db).replace('`pak::pak("datapond-db/datapond-r")`', '`install.packages("datapond")`')
    if 'license_name:' not in card:
        card = card.replace('license: other\n', 'license: other\nlicense_name: public-domain\nlicense_link: https://www.fjc.gov/history/judges\n', 1)
    frontmatter = yaml.safe_load(card.split('---', 2)[1])
    if frontmatter.get('license_name') != 'public-domain' or frontmatter.get('license_link') != 'https://www.fjc.gov/history/judges':
        raise RuntimeError('Rendered card lacks the public-domain license details')
    a.receipt.with_suffix('.README.md').write_text(card)
    api = HfApi()
    if a.verify_only:
        receipt = {'repo': spec.repo, 'commit': a.commit, 'sha256': sha, 'bytes': size, 'status': 'uploaded_pending_verification'}
        if a.receipt.exists():
            saved = json.loads(a.receipt.read_text())
            if saved.get('commit') != a.commit or saved.get('sha256') != sha:
                raise RuntimeError('Existing receipt belongs to a different artifact or commit')
            receipt.update(saved)
    else:
        current = api.repo_info(spec.repo, repo_type='dataset')
        if current.sha != a.expected_parent:
            raise RuntimeError('Published head changed; inspect before retrying (use --verify-only after upload)')
        previous = api.get_paths_info(spec.repo, [spec.file], repo_type='dataset', revision=current.sha)[0]
        if previous.lfs is None:
            raise RuntimeError('Existing destination is not an LFS artifact; inspect storage before uploading')
        print(json.dumps({'destination': spec.repo, 'bytes': size, 'sha256': sha, 'parent': current.sha, 'tables': tables, 'example_rows': len(example), 'dry_run': a.dry_run}), flush=True)
        if a.dry_run:
            return
        operations = [CommitOperationAdd(path_in_repo=spec.file, path_or_fileobj=str(a.db)), CommitOperationAdd(path_in_repo='README.md', path_or_fileobj=card.encode()), CommitOperationAdd(path_in_repo=f'sources-{snapshot}.json', path_or_fileobj=str(a.provenance)), CommitOperationAdd(path_in_repo='DICTIONARY.md', path_or_fileobj=str(a.dictionary))]
        commit = api.create_commit(repo_id=spec.repo, repo_type='dataset', parent_commit=a.expected_parent, num_threads=1, operations=operations, commit_message=f'Refresh FJC judges snapshot {snapshot}; preserve source year precision')
        receipt = {'repo': spec.repo, 'commit': commit.oid, 'url': commit.commit_url, 'sha256': sha, 'bytes': size, 'status': 'uploaded_pending_verification', 'previous_commit': a.expected_parent}
        a.receipt.write_text(json.dumps(receipt, indent=2))
        print(json.dumps(receipt), flush=True)
    receipt.update(status='verified', remote_checks=verify_remote(api, spec, receipt['commit'], report, tables))
    a.receipt.write_text(json.dumps(receipt, indent=2, default=str))
    print(json.dumps(receipt, indent=2, default=str))


if __name__ == '__main__':
    main()
