# Install and inspect NeuroFusion-QA 0.1.1

Download the wheel and source archive from the [release page](https://github.com/sukhpalsinghresearch/NeuroFusion-QA/releases/tag/v0.1.1). Use Python 3.10-3.13; Linux and Windows are the configured CI targets. Read the actual release Actions result before treating a platform/dependency combination as verified.

Create and activate an isolated environment, then install the wheel:

```text
python -m venv .venv
python -m pip install "neurofusion_qa-0.1.1-py3-none-any.whl[test,notebooks]"
python -m pip check
```

Activation: `.venv\Scripts\Activate.ps1` in Windows PowerShell; `source .venv/bin/activate` on Linux. Run the installation command after activation. The wheel filename above assumes it is in the current directory; otherwise use its downloaded path.

Extract the source archive and enter its repository folder to check code parity, tests and examples:

```text
python -I scripts/check_wheel_install.py --wheel PATH_TO_DOWNLOADED_WHEEL
python -I -m pytest -W error
python -I scripts/check_api_docs.py
python -I scripts/validate_release.py
```

Inspect or replay the tutorial with `python scripts/s01_provenance_tutorial.py`. This operates on generated mathematical signals; it does not load participant records. See `notebooks/PROVENANCE_TUTORIAL.md` for the saved expected evidence and `docs/API_REFERENCE.md` for inputs, outputs and failure conditions. Rerunning tutorial/benchmark generators can replace synthetic outputs; preserve the release copy and use a separate extraction when experimenting.

The five ordered notebooks are an optional interface/reproduction route, not the only way to use the software. The API example in the README shows probability fusion and held-out utility directly. Publication rendering additionally needs a licensed Times New Roman installation; font files are not bundled. Do not interpret a passed array check or normalized quality weight as proof of scientific or clinical validity.
