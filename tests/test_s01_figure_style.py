import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import s01_evidence_figures as figures


def test_publication_style_contract():
    assert figures.PNG_DPI==1000 and figures.FONT_FAMILY=='Times New Roman'
    assert figures.plt.rcParams['pdf.fonttype']==42
    assert figures.plt.rcParams['svg.fonttype']=='none'


def test_missing_times_font_never_silently_substitutes(monkeypatch):
    def unavailable(*args,**kwargs):
        assert kwargs['fallback_to_default'] is False
        raise ValueError('no font')
    monkeypatch.setattr(figures.font_manager,'findfont',unavailable)
    with pytest.raises(RuntimeError,match='no fallback'):
        figures.require_publication_font()
