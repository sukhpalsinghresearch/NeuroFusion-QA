# DGX-to-public release boundary

The analysis archive and this public repository serve different purposes. The private archive preserves full notebook history, logs, intermediate attempts, protocol hashes, and subject-level compact packages. The public repository contains only generalized source code, unit tests, configuration, and frozen aggregate evidence.

Excluded from the public repository:

- raw or derived EEG/fMRI data and participant-level predictions;
- all protected-cohort identifiers, manifests, and artifacts;
- SSH keys, credentials, tokens, hostnames, and local storage paths;
- large notebook outputs, duplicated exploratory cells, and interrupted work directories;
- files whose redistribution rights are not established.

This boundary is enforced by `scripts/validate_release.py`. The script scans only the repository itself and fails closed on medical-data extensions, participant-like identifiers, private-key headers, and machine-specific paths.

