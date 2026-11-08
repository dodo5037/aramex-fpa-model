"""The figures were typed in by hand from the press release. These tests catch typos by checking
every number against the margins and growth rates PRINTED in the same release, and check the maths."""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import fpa  # noqa: E402

D = fpa.load()


def rows_with(col):
    return D[D[col].notna()].itertuples()


@pytest.mark.parametrize("r", list(rows_with("printed_fy_yoy_pct")), ids=lambda r: f"{r.item}-{r.metric}")
def test_yoy_growth_matches_printed(r):
    assert round(100 * (r.fy2025 - r.fy2024) / r.fy2024) == pytest.approx(r.printed_fy_yoy_pct, abs=1)


@pytest.mark.parametrize("r", [x for x in rows_with("printed_fy2025_margin_pct")], ids=lambda r: f"{r.item}-{r.metric}")
def test_margins_match_printed(r):
    rev = fpa.get(D, r.item, "revenue"); rev24 = fpa.get(D, r.item, "revenue", "fy2024")
    assert 100 * r.fy2025 / rev == pytest.approx(r.printed_fy2025_margin_pct, abs=0.06)
    assert 100 * r.fy2024 / rev24 == pytest.approx(r.printed_fy2024_margin_pct, abs=0.06)


def test_express_subtotal_matches_printed_consolidated():
    # The release prints consolidated Express revenue 3,987,498 (FY2025) and 4,098,083 (FY2024)
    ie, de = "International Express", "Domestic Express"
    assert fpa.get(D, ie, "revenue") + fpa.get(D, de, "revenue") == 3_987_498
    assert fpa.get(D, ie, "revenue", "fy2024") + fpa.get(D, de, "revenue", "fy2024") == 4_098_083
    assert fpa.get(D, ie, "gross_profit") + fpa.get(D, de, "gross_profit") == pytest.approx(1_082_914, abs=1)


def test_segments_plus_other_equal_group():
    t = fpa.segments(D)
    assert t.rev_25.sum() == pytest.approx(fpa.get(D, "Group", "revenue"))
    assert t.gp_24.sum() == pytest.approx(fpa.get(D, "Group", "gross_profit", "fy2024"))


def test_gp_bridge_effects_add_up():
    t = fpa.segments(D)
    assert (t.gp_volume_effect + t.gp_margin_effect - t.gp_change).abs().max() < 1e-6


def test_mix_plus_rate_equals_total_margin_change():
    m = fpa.mix_vs_rate(fpa.segments(D))
    assert m["mix_effect_pp"] + m["rate_effect_pp"] == pytest.approx(m["change_pp"], abs=1e-9)


def test_price_volume_adds_up():
    pv = fpa.price_volume(D)
    assert ((pv.volume_effect + pv.price_mix_effect) - pv.rev_change).abs().max() < 1e-6


def test_base_scenario_close_to_2025_when_drivers_are_flat():
    """Sanity: with 0% growth and FY2025 margins, the model must reproduce FY2025 normalized EBIT."""
    t = fpa.segments(D); oo = fpa.one_offs(D)
    saved = fpa.SCENARIOS
    try:
        fpa.SCENARIOS = {"Flat": {s: (0, float(t[t.segment == s].gm_25_pct.iloc[0])) for s in fpa.SEGMENTS}}
        sc = fpa.scenarios(t, oo)
    finally:
        fpa.SCENARIOS = saved
    assert sc.normalized_ebit.iloc[0] == pytest.approx(fpa.get(D, "Group", "normalized_ebit"), abs=1)
