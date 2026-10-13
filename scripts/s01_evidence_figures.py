"""Literature-informed, evidence-bound figures: no protected data or brain maps.

Each family exports editable SVG/PDF, 1000 dpi PNG and a caption/source hash.
Figures are regenerated from aggregate evidence, not manually entered results.
"""
from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.text import Text
from matplotlib.colors import ListedColormap
import numpy as np
from scipy.signal import welch

from neurofusion_qa.features import eeg_features_33, fisher_connectivity, fmri_features_1440
from neurofusion_qa.gating import label_free_quality_weight
from neurofusion_qa.provenance import canonical_json, canonical_json_sha256, sha256_file
from s01_core_workflow import qc_contracts, quality_contracts

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "notebooks/figures"
COLORS = ["#255F85", "#D17C3F", "#6F6F6F", "#319B89", "#9271B7"]
METHODS = ["eeg", "fmri", "equal", "quality", "tuned_constant"]
LABELS = ["EEG", "fMRI", "Equal", "Quality", "Tuned constant"]
CONDITIONS = ["informative", "unrelated", "misleading"]
PNG_DPI = 1000
FONT_FAMILY = "Times New Roman"
plt.rcParams.update({"font.family": FONT_FAMILY, "font.size": 17,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 1.2,
    "lines.linewidth": 2.5, "legend.frameon": False, "svg.fonttype": "none",
    "pdf.fonttype": 42, "savefig.dpi": PNG_DPI,
    "mathtext.fontset":"custom", "mathtext.rm":FONT_FAMILY,
    "mathtext.it":FONT_FAMILY+":italic", "mathtext.bf":FONT_FAMILY+":bold",
    "mathtext.sf":FONT_FAMILY, "mathtext.tt":FONT_FAMILY,
    "mathtext.cal":FONT_FAMILY, "mathtext.fallback":None})


def require_publication_font():
    """Never silently substitute another typeface for the requested font."""
    # Private, user-authorized DGX copies are intentionally outside release paths.
    for private_font in sorted((ROOT / 'outputs/.fonts').glob('*.ttf')):
        font_manager.fontManager.addfont(private_font)
    try:
        path = font_manager.findfont(font_manager.FontProperties(family=FONT_FAMILY), fallback_to_default=False)
    except ValueError as error:
        raise RuntimeError("Times New Roman is not installed. Render in an environment with a licensed font; no fallback is permitted.") from error
    return {"family":FONT_FAMILY, "font_file_sha256":sha256_file(path)}


def load(name):
    path = ROOT / "notebooks/artifacts" / name
    return json.loads(path.read_text(encoding="utf-8"))


def export(fig, name, caption, sources, function):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    font = require_publication_font()
    # Explicit font on all artists, including tick/legend annotations.
    for artist in fig.findobj(Text):
        artist.set_fontfamily(FONT_FAMILY)
        artist.set_fontsize(max(14, artist.get_fontsize()))
    files = {}
    for suffix in ("png", "svg", "pdf"):
        path = DIRECTORY / f"{name}.{suffix}"
        fig.savefig(path, bbox_inches="tight", facecolor="white", dpi=PNG_DPI, pad_inches=.12)
        files[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    preview_directory = DIRECTORY / "previews"
    preview_directory.mkdir(exist_ok=True)
    preview = preview_directory / f"{name}.png"
    fig.savefig(preview, bbox_inches="tight",facecolor="white",dpi=150,pad_inches=.12)
    plt.close(fig)
    gc.collect()
    evidence = {source: sha256_file(ROOT / source) for source in sources}
    evidence["scripts/s01_evidence_figures.py"] = sha256_file(Path(__file__))
    record = {"id": name, "caption": caption, "producing_function": function,
              "sources": evidence, "exports": files, "scope": "synthetic_software_evidence_only",
              "style":{"png_dpi":PNG_DPI,"minimum_text_points":14,**font},
              "preview":{"path":preview.relative_to(ROOT).as_posix(),"sha256":sha256_file(preview),"dpi":150,"purpose":"screen_preview_not_publication_raster"}}
    (DIRECTORY / f"{name}.caption.json").write_text(canonical_json(record) + "\n", encoding="utf-8")
    print(f"Exported {name}: {FONT_FAMILY}, {PNG_DPI} dpi",flush=True)
    return record


def render_environment():
    evidence = load("00_preflight_report.json")
    environment = evidence["environment"]
    fig, ax = plt.subplots(figsize=(10, 4.8), layout="constrained")
    ax.axis("off")
    ax.text(0, .94, "S01 environment and release boundary", fontsize=21, weight="bold")
    rows = [f"Python {environment['python']} · {environment['platform_system']} / {environment['platform_machine']}",
            " · ".join(f"{key} {value}" for key, value in environment["packages"].items()),
            "Inputs: public documentation / mathematical fixtures only",
            "Protected data accessed: no · Clinical claim supported: no",
            "Audit records versions; it does not certify all-platform support."]
    for y, row in zip([.75, .58, .41, .24, .07], rows):
        ax.text(0, y, row, fontsize=13)
    return [export(fig, "F00_environment", "Environment and boundary audit for this execution, not a portability certification.",
        ["notebooks/artifacts/00_preflight_report.json"], "render_environment")]


def make_signal_fixture(seed=20260918):
    """Exact mathematical fixture in notebook 01; no physiological model."""
    rng = np.random.default_rng(seed)
    time = np.arange(1000) / 250.
    eeg = np.vstack([(1 + .04 * c) * np.sin(2*np.pi*(3+c)*time+.2*c)
        + .35*np.sin(2*np.pi*10*time-.1*c)+rng.normal(0,.08,time.size) for c in range(8)])
    time = np.arange(160) / 1.25
    latent = np.vstack([np.sin(2*np.pi*.03*time), np.cos(2*np.pi*.06*time), np.sin(2*np.pi*.09*time+.4)])
    fmri = rng.normal(0,.7,(360,3)) @ latent + rng.normal(0,.35,(360,time.size))
    return eeg, fmri


def render_core():
    sources = ["notebooks/artifacts/01_feature_contracts.json", "scripts/s01_core_workflow.py"]
    fixture_evidence = load("01_feature_contracts.json")
    eeg, fmri = make_signal_fixture(fixture_evidence["seed"])
    ef, ff, fc = eeg_features_33(eeg, 250), fmri_features_1440(fmri, 1.25), fisher_connectivity(fmri)
    # Bind visuals to the exact arrays whose contracts were recorded in 01.
    import hashlib
    for name, array in (("eeg", ef), ("fmri", ff), ("connectivity", fc)):
        canonical = np.ascontiguousarray(array, dtype='<f8')
        digest = hashlib.sha256(json.dumps(list(canonical.shape), separators=(',', ':')).encode('ascii'))
        digest.update(canonical.tobytes(order='C'))
        assert digest.hexdigest() == fixture_evidence["features"][name]["sha256"]
    fig, axes = plt.subplots(2, 2, figsize=(13, 10), layout="constrained")
    frequency, psd = welch(eeg, fs=250, nperseg=500, axis=1)
    axes[0,0].plot(frequency, psd.mean(axis=0), color=COLORS[0])
    axes[0,0].set(xlim=(0,40), xlabel="Frequency (Hz)", ylabel="Mean power density (arbitrary units)", title="A  Mathematical EEG spectrum")
    axes[0,1].plot(np.arange(33), ef, "o-", color=COLORS[0], markersize=3)
    axes[0,1].set(xlabel="Feature index (declared ordering)", ylabel="Native value (mixed units)", title="B  EEG feature contract: 33 values")
    limit = np.quantile(np.abs(fc), .99)
    image = axes[1,0].imshow(fc, cmap="RdBu_r", vmin=-limit, vmax=limit, rasterized=True)
    axes[1,0].set(xlabel="Mathematical parcel index", ylabel="Mathematical parcel index", title="C  Fisher-z connectivity")
    fig.colorbar(image, ax=axes[1,0], label="Fisher z (99th-percentile display limit)", shrink=.8)
    for block, label, color in zip(np.split(ff,4), ["Strength", "ALFF", "fALFF", "SD"], COLORS):
        # Different feature units are shown separately as normalized distributions.
        axes[1,1].hist((block-np.median(block))/(np.std(block) or 1), bins=24, histtype="step", density=True, label=label, color=color)
    axes[1,1].set(xlabel="Within-block centered value / SD", ylabel="Density", title="D  fMRI blocks: 360 values each")
    axes[1,1].legend(fontsize=11)
    records = [export(fig, "F01_feature_contracts", "Deterministic mathematical inputs, identical to notebook 01. Mixed EEG feature units must not be compared as effect sizes; fMRI block distributions are normalized only for display; connectivity is not an anatomical brain map.", sources, "render_core")]
    qc = qc_contracts()
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), layout="constrained", gridspec_kw={"width_ratios":[2,1]})
    criteria = list(dict.fromkeys(row["criterion"] for row in qc["threshold_cases"]))
    for i, name in enumerate(criteria):
        rows = [row for row in qc["threshold_cases"] if row["criterion"] == name]
        for j, row in enumerate(rows):
            axes[0].text(j, i, str(row["value"]), ha="center", va="center", color="white", fontsize=11,
                bbox={"boxstyle":"round,pad=.5", "edgecolor":"none", "facecolor":COLORS[3] if row["observed_pass"] else COLORS[1]})
    axes[0].set(yticks=range(7), yticklabels=[n.replace("_", " ") for n in criteria], xticks=range(3), xticklabels=["Lower / false", "Boundary / true", "Upper"], title="A  One criterion varied; others pass", ylim=(6.6,-.6), xlim=(-.4,2.4))
    axes[0].tick_params(axis="y", labelsize=11)
    axes[1].imshow([[0,1],[1,1]], cmap=ListedColormap([COLORS[3], COLORS[1]]), vmin=0,vmax=1)
    for a in range(2):
        for b in range(2):
            axes[1].text(b,a, "Eligible" if a==b==0 else "Rejected",ha="center",va="center",color="white",fontsize=12)
    axes[1].set(xticks=[0,1], xticklabels=["Pass","Fail"], yticks=[0,1], yticklabels=["Pass","Fail"], xlabel="Scientific QC", ylabel="Feature integrity", title="B  Independent gates")
    records.append(export(fig, "F02_qc_boundaries", "Seven declared fMRI QC criteria checked at/around their boundaries. Green passes; orange rejects. QC and feature integrity are distinct: neither substitutes for the other. Binary criterion has only two cases; values are in each criterion's native units.", sources, "render_core"))
    quality = quality_contracts()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    image = axes[0].imshow(quality["scaled_held_out"], cmap="RdBu_r", vmin=-5, vmax=5, aspect="auto")
    for i,row in enumerate(quality["scaled_held_out"]):
        for j,value in enumerate(row):
            axes[0].text(j,i,f"{value:g}",ha="center",va="center",color="white" if abs(value)>3 else "black")
    axes[0].set(xticks=[0,1], xticklabels=["Quality 1","Quality 2"], yticks=[0,1], yticklabels=["Median / missing","Extreme held-out"], title="A  Frozen training-only transform")
    fig.colorbar(image, ax=axes[0], label="Robust scaled quality", shrink=.8)
    fmri_quality = np.linspace(0,1,101)
    for eeg_quality,color in zip([.1,.5,1], [COLORS[0],COLORS[1],COLORS[3]]):
        axes[1].plot(fmri_quality, label_free_quality_weight(np.full(101,eeg_quality),fmri_quality), label=f"EEG quality {eeg_quality:g}",color=color)
    axes[1].set(xlabel="fMRI quality", ylabel="fMRI fusion weight", ylim=(0,1), title="B  Label-free quality response")
    axes[1].legend(fontsize=11)
    records.append(export(fig, "F03_quality_response", "Missing quality imputes to the training median; extremes clip to [-5,5]. Fusion response follows q_fMRI/(q_EEG+q_fMRI); both-zero quality is rejected, not drawn. Monotonic response is a contract, not proof of predictive benefit.", sources, "render_core"))
    return records


def render_provenance():
    sources = ["notebooks/artifacts/02_tutorial_summary.json", "notebooks/artifacts/02_provenance_failures.json", "notebooks/artifacts/02_execution_manifest.json"]
    summary = load("02_tutorial_summary.json")
    failures = load("02_provenance_failures.json")
    fig, ax = plt.subplots(figsize=(14, 5), layout="constrained")
    ax.set(xlim=(-.5,4.5),ylim=(-.8,2)); ax.axis("off")
    nodes = ["Namespaced\nobservation IDs", "Cardinality-checked\npaired join", "Training-only\nfit / held-out test", "Aggregate\nevidence", "Hash-bound\nexecution manifest"]
    for i,label in enumerate(nodes):
        ax.text(i,.9,label,ha="center",va="center",fontsize=12,bbox={"boxstyle":"round,pad=.8","facecolor":"#EEF3F7","edgecolor":COLORS[0]})
        if i:
            ax.annotate("",xy=(i-.37,.9),xytext=(i-.63,.9),arrowprops={"arrowstyle":"->","lw":2})
    ax.text(2,1.75,"Pairing and provenance contract",ha="center",fontsize=21)
    ax.text(2,-.1,"Fail closed: missing / duplicate / cross-namespace keys; unsafe paths; changed files",ha="center",fontsize=13)
    ax.text(2,-.55,"Hashes detect changes relative to a trusted digest; they do not authenticate the executor.",ha="center",fontsize=13)
    records = [export(fig,"F04_provenance_lineage","Conceptual flow of the executed tutorial's identity and manifest contract; actual failure checks accompany the schematic. A manifest is not an authenticated signature.",sources,"render_provenance")]
    fig, axes = plt.subplots(1,2,figsize=(12,5),layout="constrained")
    axes[0].bar(["Train","Held-out"],[summary["training_records"],summary["held_out_records"]],color=[COLORS[0],COLORS[3]])
    axes[0].set(ylabel="Mathematical records",title="A  Disjoint tutorial split",ylim=(0,20))
    for x,value in enumerate([summary["training_records"],summary["held_out_records"]]): axes[0].text(x,value+.3,str(value),ha="center")
    axes[1].axis("off")
    texts = ["24 paired records → EEG 33 / fMRI 1,440 features", "One scientific-QC fixture failure", "Separate constant-feature integrity failure", "QC rejection → zero modality contribution", f"{len(failures)} provenance failures rejected", "Tutorial metrics are not benchmark results."]
    for y,text in zip(np.linspace(.95,.05,len(texts)),texts): axes[1].text(0,y,text,fontsize=12)
    records.append(export(fig,"F05_tutorial_accounting","Tutorial accounting from executed evidence: disjoint 16/8 split, actual feature shapes, separate QC/integrity checks and fail-closed provenance demonstrations. Small, deliberately easy signals cannot establish prediction performance.",sources,"render_provenance"))
    return records


def method_legend(fig):
    from matplotlib.lines import Line2D
    fig.legend([Line2D([0],[0],color=c,lw=2.5) for c in COLORS],LABELS,loc="outside lower center",ncol=5,fontsize=12)


def render_benchmark():
    result = load("03_comparator_results.json")
    sources = ["notebooks/artifacts/03_comparator_results.json", "config/s01_comparator_protocol.json"]
    conditions = result["conditions"]
    records = []
    metrics = list(conditions["informative"]["profiles"]["eeg"])
    # Canonical JSON sorts keys; use protocol's explicit display order.
    metrics = json.loads((ROOT / sources[1]).read_text(encoding="utf-8"))["metrics"]
    for condition in CONDITIONS:
        fig, axes = plt.subplots(3,4,figsize=(18,13),layout="constrained")
        for ax,metric in zip(axes.flat,metrics):
            for i,(name,color) in enumerate(zip(METHODS,COLORS)):
                item = conditions[condition]["profiles"][name][metric]
                ax.hlines(i,item["ci_low"],item["ci_high"],color=color,lw=2)
                ax.plot(item["value"],i,"o",color=color)
            ax.set(yticks=range(5),yticklabels=LABELS, title=metric.replace("_"," "),ylim=(4.6,-.6))
            ax.tick_params(labelsize=11)
        fig.suptitle(f"Controlled synthetic comparison — {condition} quality\nPoint estimates and paired-record 95% bootstrap intervals",fontsize=20)
        records.append(export(fig,f"F06_metrics_{condition}",f"All 12 predeclared metrics, five methods, {condition} quality; 360 balanced mathematical records, three seeds, shared 4-fold/2-repeat nested predictions. 1,000 seed/class-stratified record bootstrap resamples of averaged predictions: conditional on fitted models, not model-refitting or population uncertainty. Lower is better for Brier, log loss, ECE; higher for the other metrics. Threshold metrics use majority decisions from training-OOF thresholds (ties positive), not 0.5 on averaged probabilities. Undefined precision/F1/MCC use zero.",sources,"render_benchmark"))
    fig, axes = plt.subplots(1,3,figsize=(14,5),layout="constrained")
    for ax,condition in zip(axes,CONDITIONS):
        rows=[r for r in conditions[condition]["paired_differences"] if r["metric"]=="brier_score"]
        for i,row in enumerate(rows):
            color=COLORS[METHODS.index(row["candidate"])]
            ax.hlines(i,row["ci_low"],row["ci_high"],color=color,lw=2)
            ax.plot(row["difference"],i,"o",color=color)
        ax.axvline(0,color="#777777",ls="--",lw=1)
        ax.set(title=condition, yticks=range(4),yticklabels=[LABELS[METHODS.index(r["candidate"])] for r in rows],xlabel="Brier difference vs equal\n← lower error",ylim=(3.5,-.5))
        ax.tick_params(labelsize=12)
    records.append(export(fig,"F07_paired_brier","Paired candidate-minus-equal Brier differences with 95% record-bootstrap intervals. Negative is lower error. Same resampled indices for every method; intervals are descriptive, no multiplicity-adjusted significance claim. Misleading-quality failures remain visible.",sources,"render_benchmark"))
    fig, axes = plt.subplots(3,2,figsize=(12,15),layout="constrained")
    for row,condition in enumerate(CONDITIONS):
        for name,color in zip(METHODS,COLORS):
            curves=conditions[condition]["curves"][name]
            axes[row,0].plot(curves["fpr"],curves["tpr"],color=color)
            axes[row,1].plot(curves["recall"],curves["precision"],color=color)
        axes[row,0].plot([0,1],[0,1],color="#999999",ls="--",lw=1)
        axes[row,1].axhline(.5,color="#999999",ls="--",lw=1)
        axes[row,0].set(xlabel="False-positive rate",ylabel="True-positive rate",title=f"{condition}: ROC",xlim=(0,1),ylim=(0,1.02))
        axes[row,1].set(xlabel="Recall",ylabel="Precision",title=f"{condition}: PR (prevalence 0.5)",xlim=(0,1),ylim=(0,1.02))
    method_legend(fig)
    records.append(export(fig,"F08_discrimination_curves","ROC and precision-recall curves from repeat-averaged held-out predictions. Random reference lines are diagonal ROC and prevalence 0.5 for PR. Curves have no pointwise CI bands; scalar AUC/AP intervals are in F06.",sources,"render_benchmark"))
    fig, axes = plt.subplots(3,2,figsize=(12,15),layout="constrained")
    for row,condition in enumerate(CONDITIONS):
        for name,color in zip(METHODS,COLORS):
            bins=conditions[condition]["calibration"][name]
            occupied=[b for b in bins if b["count"]]
            axes[row,0].plot([b["mean_probability"] for b in occupied],[b["positive_fraction"] for b in occupied],"o-",color=color,markersize=4)
            axes[row,1].plot(np.arange(10)/10+.05,[b["count"] for b in bins],"o-",color=color,markersize=4)
        axes[row,0].plot([0,1],[0,1],ls="--",lw=1,color="#999999")
        axes[row,0].set(xlabel="Mean predicted probability",ylabel="Observed positive fraction",title=f"{condition}: calibration",xlim=(0,1),ylim=(0,1))
        axes[row,1].set(xlabel="Bin midpoint (10 equal-width bins)",ylabel="Records in bin",title=f"{condition}: bin support",xlim=(0,1))
    method_legend(fig)
    records.append(export(fig,"F09_calibration_support","Ten equal-width reliability bins paired with their actual support. Empty bins are omitted from calibration curves but retained as zero in count panels; probability 1 belongs to the last bin. These curves are descriptive, with no bin-wise uncertainty claim; ECE depends on binning.",sources,"render_benchmark"))
    fig, axes = plt.subplots(3,5,figsize=(17,10),layout="constrained")
    for row,condition in enumerate(CONDITIONS):
        for col,name in enumerate(METHODS):
            ax=axes[row,col]; matrix=np.array(conditions[condition]["confusion"][name])
            ax.imshow(matrix,cmap="Blues",vmin=0,vmax=180)
            for a in range(2):
                for b in range(2): ax.text(b,a,str(matrix[a,b]),ha="center",va="center",color="white" if matrix[a,b]>90 else "black",fontsize=16)
            ax.set(xticks=[0,1],yticks=[0,1],xlabel="Predicted class",ylabel="True class",title=f"{condition}\n{LABELS[col]}")
            ax.tick_params(labelsize=11)
    records.append(export(fig,"F10_confusion_counts","All thresholded confusion matrices, counts on a common 0–180 color scale, 180 true records per class. Row=true/column=predicted. Decisions are majority votes from training-only OOF threshold selection; no threshold tuned on held-out labels.",sources,"render_benchmark"))
    fig, axes = plt.subplots(2,3,figsize=(14,9),layout="constrained")
    for col,condition in enumerate(CONDITIONS):
        bins=conditions[condition]["gate_bins"]
        axes[0,col].plot([b["weight_mean"] for b in bins],[b["utility_mean"] for b in bins],"o-",color=COLORS[3])
        for b in bins:
            axes[0,col].annotate(f"n={b['count']}",(b['weight_mean'],b['utility_mean']),xytext=(4,5),textcoords='offset points',fontsize=10)
        axes[0,col].axhline(0,color="#999999",lw=1)
        axes[0,col].set(xlabel="Mean fMRI weight within bin",ylabel="Mean held-out fMRI utility",title=condition,xlim=(0,1))
        for i,key in enumerate(["utility_auc","spearman_rho"]):
            item=conditions[condition]["gate_validity"][key]
            if item["value"] is not None:
                axes[1,col].hlines(i,item["ci_low"],item["ci_high"],color=COLORS[3],lw=2)
                axes[1,col].plot(item["value"],i,"o",color=COLORS[3])
        axes[1,col].set(yticks=[0,1],yticklabels=["Utility AUC","Spearman ρ"],xlabel="Gate diagnostic (95% interval)",xlim=(-1,1),ylim=(1.5,-.5))
        axes[1,col].axvline(0,color="#999999",ls="--",lw=1)
        axes[1,col].axvline(.5,color="#BBBBBB",ls=":",lw=1)
    records.append(export(fig,"F11_gate_validity","Utility is |y−p_EEG|−|y−p_fMRI|, computed from held-out unimodal predictions independently of the gate. Upper row: descriptive means in weight bins, no CI. Lower: utility-sign AUC (chance .5) and Spearman association (null 0), paired-record bootstrap intervals. Quality monotonicity alone does not validate utility.",sources,"render_benchmark"))
    fig, axes = plt.subplots(3,3,figsize=(14,12),layout="constrained")
    for row,condition in enumerate(CONDITIONS):
        folds=[f for f in result["folds"] if f["condition"]==condition]
        x=np.arange(len(folds))
        for name,color in zip(METHODS[:2],COLORS): axes[row,0].plot(x,[f["selected_c"][name] for f in folds],"o-",color=color,markersize=4,label=name)
        axes[row,0].set(yscale="log",xlabel="Seed/repeat/fold index",ylabel="Selected C",title=f"{condition}: unimodal tuning")
        axes[row,1].plot(x,[f["constant_weight"] for f in folds],"o-",color=COLORS[4],markersize=4)
        axes[row,1].set(xlabel="Seed/repeat/fold index",ylabel="Tuned fMRI weight",ylim=(0,1),title="Training OOF constant rule")
        for name,color in zip(METHODS,COLORS): axes[row,2].plot(x,[f["thresholds"][name] for f in folds],"o-",color=color,markersize=3)
        axes[row,2].set(xlabel="Seed/repeat/fold index",ylabel="Training OOF threshold",ylim=(0,1),title="Operating points")
    method_legend(fig)
    records.append(export(fig,"F12_nested_tuning","Training-only selected C, constant fMRI weight and operating thresholds for all 24 outer folds per quality condition. The JSON also records split hashes/counts; identical folds and shared unimodal predictions are tested. Fold points are dependent and are not independent samples for inference.",sources,"render_benchmark"))
    return records


def render_robustness():
    result=load('04_robustness_results.json')
    sources=['notebooks/artifacts/04_robustness_results.json','config/s01_robustness_protocol.json']
    rows=result['sweeps']
    fig,axes=plt.subplots(2,2,figsize=(13,10),layout='constrained')
    for ax,experiment,title in [(axes[0,0],'eeg_missing','A  EEG unavailable'),(axes[0,1],'fmri_missing','B  fMRI unavailable'),(axes[1,1],'probability_shrinkage','D  fMRI probability shrunk toward 0.5')]:
        for method,color in [('quality',COLORS[3]),('equal',COLORS[2])]:
            selected=[r for r in rows if r['experiment']==experiment and r['method']==method]
            x=[r['level'] for r in selected]; value=np.array([r['brier_score'] for r in selected])
            ax.errorbar(x,value,yerr=[value-np.array([r['ci_low'] for r in selected]),np.array([r['ci_high'] for r in selected])-value],fmt='o-',capsize=3,color=color,label=method.capitalize())
        ax.set(title=title,xlabel='Requested missing fraction' if experiment!='probability_shrinkage' else 'Shrinkage level',ylabel='Brier error (lower is better)',xlim=(-.03,1.03))
        ax.legend()
    selected=[r for r in rows if r['experiment']=='quality_ablation']
    for i,r in enumerate(selected):
        axes[1,0].hlines(i,r['ci_low'],r['ci_high'],color=COLORS[3],lw=2)
        axes[1,0].plot(r['brier_score'],i,'o',color=COLORS[3])
    axes[1,0].set(title='C  Weight ablations',yticks=range(4),yticklabels=['Informative','Record permutation','Reversed','Equal'],xlabel='Brier error (lower is better)',ylim=(3.5,-.5))
    records=[export(fig,'F13_interface_robustness','Controlled prediction-interface audit, not EEG/fMRI signal corruption or external validation. Missingness uses shared nested random masks (actual counts in JSON); both methods remove unavailable modalities. Shrinkage also scales quality-aware fMRI reliability mass; no model retraining. Apply perturbation per repeat before averaging. Points/95% intervals use 1,000 seed/class-stratified record resamples conditional on fitted models; intervals are not paired-difference significance tests. Both-unavailable and zero-reliability cases reject explicitly.',sources,'render_robustness')]
    fig,ax=plt.subplots(figsize=(9,6),layout='constrained')
    for operation,color in zip(['soft_fusion','quality_normalization','held_out_utility'],COLORS):
        selected=[r for r in result['timings'] if r['operation']==operation]
        x=[r['records'] for r in selected]; med=np.array([r['median_ms'] for r in selected])
        ax.errorbar(x,med,yerr=[med-np.array([r['q25_ms'] for r in selected]),np.array([r['q75_ms'] for r in selected])-med],fmt='o-',capsize=4,color=color,label=operation.replace('_',' '))
    ax.set(xscale='log',yscale='log',xlabel='Records per API invocation',ylabel='Elapsed milliseconds (median and IQR)',title=f"Public CPU kernel timing — {result['metadata']['platform']}")
    ax.legend(loc='upper left')
    records.append(export(fig,'F14_cpu_kernel_timing','Measured public-API kernel calls only: 3 warmups, 15 repetitions, one BLAS/OpenMP thread; inputs prepared outside timed region. Bars are timing IQR, not confidence intervals. Runtime-specific environment and raw summary ranges are in JSON. Not a full-pipeline benchmark, GPU result, cross-method speed claim or peak-memory measurement.',sources,'render_robustness'))
    return records


def generate(section="all"):
    require_publication_font()
    choices = {"00":render_environment,"01":render_core,"02":render_provenance,"03":render_benchmark,"04":render_robustness}
    records=[]
    for key,operation in choices.items():
        if section in (key,"all"): records.extend(operation())
    # Rebuild the gallery from every existing caption, without dropping other stages.
    captions=[json.loads(p.read_text(encoding="utf-8")) for p in sorted(DIRECTORY.glob("*.caption.json"))]
    index={"schema_version":"1.0","figures":captions,"scope":"synthetic_software_evidence_only"}
    (DIRECTORY / "figure_index.json").write_text(canonical_json(index)+"\n",encoding="utf-8")
    lines=["# S01 evidence figure gallery", "", "Synthetic software evidence only. Times New Roman (minimum 14-point text), editable SVG/PDF and 1000 dpi PNG exports accompany every figure. Embedded images are explicitly low-resolution screen previews; use the publication PNG/PDF/SVG links for submission. Captions define interpretation limits.", ""]
    for item in captions:
        lines.extend([f"## {item['id']}", "", f"![{item['id']} screen preview](previews/{item['id']}.png)", "", item["caption"], "", f"[1000 DPI PNG]({item['id']}.png) · [SVG]({item['id']}.svg) · [PDF]({item['id']}.pdf) · [Caption and source hashes]({item['id']}.caption.json)", ""])
    (DIRECTORY / "README.md").write_text("\n".join(lines),encoding="utf-8")
    return records


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--section",choices=["all","00","01","02","03","04"],default="all")
    args=parser.parse_args()
    generated=generate(args.section)
    print(f"Exported {len(generated)} figure sets to notebooks/figures")
