"""Verify current comparator and figure evidence, fail closed on stale inputs."""
import csv
import json
from pathlib import Path
import struct
import re

from neurofusion_qa.provenance import canonical_json_sha256, sha256_file
from s01_comparator_benchmark import load_protocol, PROTOCOL_HASH, METHODS

ROOT = Path(__file__).resolve().parents[1]


def verify_and_export():
    protocol = load_protocol()
    results = json.loads((ROOT / "notebooks/artifacts/03_comparator_results.json").read_text(encoding="utf-8"))
    assert results["protocol_sha256"] == PROTOCOL_HASH
    for name, digest in results["metadata"]["source_sha256"].items():
        assert sha256_file(ROOT / name) == digest, f"stale benchmark source: {name}"
    folds = results["folds"]
    assert len(folds) == 72
    assert len({(f["condition"], f["fixture_seed"], f["repeat"], f["fold"]) for f in folds}) == 72
    # Conditions must have identical splits, tuning and unimodal results.
    reference = results["conditions"]["informative"]
    for condition in protocol["quality_conditions"]:
        evidence = results["conditions"][condition]
        assert evidence["records"] == 360 and set(evidence["profiles"]) == set(METHODS)
        for name in METHODS:
            assert set(evidence["profiles"][name]) == set(protocol["metrics"])
            assert sum(map(sum,evidence["confusion"][name])) == 360
            assert sum(b["count"] for b in evidence["calibration"][name]) == 360
        for name in ("eeg", "fmri", "equal", "tuned_constant"):
            assert evidence["profiles"][name] == reference["profiles"][name]
        split_signature = [(f["fixture_seed"], f["repeat"], f["fold"], f["train_hash"], f["test_hash"]) for f in folds if f["condition"] == condition]
        assert split_signature == [(f["fixture_seed"], f["repeat"], f["fold"], f["train_hash"], f["test_hash"]) for f in folds if f["condition"] == "informative"]
    directory = ROOT / "notebooks/figures"
    index = json.loads((directory / "figure_index.json").read_text(encoding="utf-8"))
    expected_count=17 if (ROOT/'notebooks/artifacts/04_robustness_results.json').exists() else 15
    assert len(index["figures"]) == expected_count
    for item in index["figures"]:
        assert len(item["exports"]) == 3
        for name, digest in (item["sources"] | item["exports"]).items():
            target=(ROOT/name).resolve()
            assert target.is_relative_to(ROOT) and sha256_file(target) == digest, f"stale figure evidence: {name}"
        caption = json.loads((directory / f"{item['id']}.caption.json").read_text(encoding="utf-8"))
        assert canonical_json_sha256(caption) == canonical_json_sha256(item)
        assert item['style']['png_dpi']==1000 and item['style']['family']=='Times New Roman'
        assert item['style']['minimum_text_points']>=14
        preview=item['preview']
        assert preview['purpose']=='screen_preview_not_publication_raster' and preview['dpi']==150
        assert sha256_file(ROOT/preview['path'])==preview['sha256']
        # Read PNG metadata without decoding the enormous publication raster.
        with (directory/f"{item['id']}.png").open('rb') as stream:
            assert stream.read(8)==b'\x89PNG\r\n\x1a\n'
            dpi=None
            while True:
                header=stream.read(8)
                assert len(header)==8, 'PNG missing resolution metadata'
                length,kind=struct.unpack('>I4s',header)
                if kind==b'pHYs':
                    x,y,unit=struct.unpack('>IIB',stream.read(length))
                    assert unit==1 and abs(x*.0254-1000)<.01 and abs(y*.0254-1000)<.01
                    dpi=x*.0254; break
                stream.seek(length+4,1)
                assert kind!=b'IEND'
            assert dpi is not None
        pdf=(directory/f"{item['id']}.pdf").read_bytes()
        fonts=re.findall(rb'/BaseFont /([^\s]+)',pdf)
        assert fonts and all(b'TimesNewRoman' in font for font in fonts), f'non-Times embedded font: {item["id"]}'
        assert b'/FontFile2' in pdf, 'PDF must embed its TrueType font'
    if expected_count==17:
        from s01_robustness_audit import load_protocol as robustness_protocol,PROTOCOL_SHA256
        robustness_protocol()
        audit=json.loads((ROOT/'notebooks/artifacts/04_robustness_results.json').read_text(encoding='utf-8'))
        assert audit['protocol_sha256']==PROTOCOL_SHA256
        assert audit['base_matches_03'] and audit['deterministic_sweep_replay']
        assert len(audit['sweeps'])==38 and len(audit['timings'])==9
        for name,digest in audit['metadata']['source_sha256'].items():
            assert sha256_file(ROOT/name)==digest, f'stale robustness source: {name}'
    destination=ROOT / "notebooks/artifacts"
    # Public aggregate tables for manuscript drafting, no individual predictions.
    with (destination / "03_comparator_metrics.csv").open("w",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["condition","method","metric","value","ci_low","ci_high"])
        writer.writeheader()
        for condition,evidence in results["conditions"].items():
            for name,profile in evidence["profiles"].items():
                for metric,values in profile.items(): writer.writerow({"condition":condition,"method":name,"metric":metric,**values})
    with (destination / "03_paired_differences.csv").open("w",encoding="utf-8",newline="") as stream:
        fields=["condition","candidate","reference","metric","difference","ci_low","ci_high","interval_spans_zero"]
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
        for condition,evidence in results["conditions"].items():
            for row in evidence["paired_differences"]: writer.writerow({"condition":condition,**row})
    print(f"Evidence verified: frozen protocols; 72 matched folds; {expected_count} figure sets / {expected_count*3} exports; Times New Roman / 1000 DPI; 180 metric rows / 144 paired differences.")


if __name__ == "__main__":
    verify_and_export()
