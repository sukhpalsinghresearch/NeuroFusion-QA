# Contributing

Use the repository issue tracker for reproducible bugs, documentation corrections and proposed changes. Include package/dependency versions, expected and observed behavior, and a small synthetic example. Do not upload participant data, institutional paths, credentials or proprietary fonts.

Discuss changes to feature definitions, QC thresholds, fusion rules or evaluation conventions before implementation. Such changes can invalidate frozen evidence and require a new protocol rather than replacement of an old result file.

Install a development environment with `python -m pip install -e ".[test,figures]"`. Run `python -m pytest -W error`, `python scripts/check_api_docs.py` and `python scripts/validate_release.py`. Release validation must also use a non-editable built wheel; see `docs/INSTALLATION_AND_CI.md`. Style-only edits should preserve behavior, identifiers and legal notices. Keep comments focused on contracts or nonobvious decisions.

Contributions are reviewed through pull requests. The author team must approve changes before a submission release. There is no promised response time or service-level agreement. Contributors retain their copyright and must have permission to contribute under BSD-3-Clause.
