"""FP&A analysis of Aramex FY2025 vs FY2024 from the company's published results.

What an FP&A analyst would produce after year-end:
  1. Revenue bridge by segment (where did the +AED 35.5m come from?)
  2. Gross-profit bridge split into VOLUME (segment grew or shrank) and MARGIN RATE
     (segment's margin moved) effects, plus the group MIX effect behind the margin drop
  3. Price vs volume for the Express products, using shipment counts
  4. P&L cascade and one-off items (reported vs normalized)
  5. Driver-based 2026 scenarios (ILLUSTRATIVE assumptions, not company guidance)
  6. An automatic variance memo whose every number is computed here, never typed by hand
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "aramex_fy2025_fy2024.csv"
T = ROOT / "outputs" / "tables"
T.mkdir(parents=True, exist_ok=True)
SEGMENTS = ["International Express", "Domestic Express", "Freight Forwarding", "Logistics"]


def load() -> pd.DataFrame:
    return pd.read_csv(DATA, comment="#")


def get(d, item, metric, col="fy2025"):
    return float(d[(d["item"] == item) & (d["metric"] == metric)][col].iloc[0])


def segments(d) -> pd.DataFrame:
    """Segment table with an 'Other / eliminations' line so segments add up to the group."""
    rows = []
    for s in SEGMENTS:
        rows.append({"segment": s, "rev_24": get(d, s, "revenue", "fy2024"), "rev_25": get(d, s, "revenue"),
                     "gp_24": get(d, s, "gross_profit", "fy2024"), "gp_25": get(d, s, "gross_profit")})
    t = pd.DataFrame(rows)
    other = {"segment": "Other / eliminations",
             "rev_24": get(d, "Group", "revenue", "fy2024") - t.rev_24.sum(), "rev_25": get(d, "Group", "revenue") - t.rev_25.sum(),
             "gp_24": get(d, "Group", "gross_profit", "fy2024") - t.gp_24.sum(), "gp_25": get(d, "Group", "gross_profit") - t.gp_25.sum()}
    t = pd.concat([t, pd.DataFrame([other])], ignore_index=True)
    t["rev_change"] = t.rev_25 - t.rev_24
    t["rev_growth_pct"] = 100 * t.rev_change / t.rev_24
    t["gm_24_pct"] = 100 * t.gp_24 / t.rev_24
    t["gm_25_pct"] = 100 * t.gp_25 / t.rev_25
    t["share_24_pct"] = 100 * t.rev_24 / t.rev_24.sum()
    t["share_25_pct"] = 100 * t.rev_25 / t.rev_25.sum()
    # GP bridge per segment: volume effect at last year's margin + margin-rate effect on this year's revenue
    t["gp_volume_effect"] = t.rev_change * t.gp_24 / t.rev_24
    t["gp_margin_effect"] = t.rev_25 * (t.gp_25 / t.rev_25 - t.gp_24 / t.rev_24)
    t["gp_change"] = t.gp_25 - t.gp_24
    return t


def mix_vs_rate(t: pd.DataFrame) -> dict:
    """Split the group gross-margin change (pp) into MIX (shift between segments) and RATE (margins within segments)."""
    s = t[t.segment != "Other / eliminations"]
    w24, w25 = s.rev_24 / s.rev_24.sum(), s.rev_25 / s.rev_25.sum()
    m24, m25 = s.gp_24 / s.rev_24, s.gp_25 / s.rev_25
    mix = float(((w25 - w24) * m24).sum() * 100)
    rate = float((w25 * (m25 - m24)).sum() * 100)
    g24 = float((s.gp_24.sum() / s.rev_24.sum()) * 100)
    g25 = float((s.gp_25.sum() / s.rev_25.sum()) * 100)
    return {"segments_margin_24_pct": g24, "segments_margin_25_pct": g25, "change_pp": g25 - g24,
            "mix_effect_pp": mix, "rate_effect_pp": rate}


def price_volume(d) -> pd.DataFrame:
    rows = []
    for s in ["International Express", "Domestic Express"]:
        r24, r25 = get(d, s, "revenue", "fy2024"), get(d, s, "revenue")
        v24, v25 = get(d, s, "shipments_m", "fy2024"), get(d, s, "shipments_m")
        p24, p25 = r24 / v24 / 1000, r25 / v25 / 1000  # AED per shipment (revenue in thousands, volume in millions)
        rows.append({"segment": s, "shipments_24_m": v24, "shipments_25_m": v25, "rev_per_shipment_24": p24,
                     "rev_per_shipment_25": p25, "volume_effect": (v25 - v24) * p24 * 1000,
                     "price_mix_effect": v25 * (p25 - p24) * 1000, "rev_change": r25 - r24})
    return pd.DataFrame(rows)


def pnl(d) -> pd.DataFrame:
    rows = []
    for m in ["revenue", "gross_profit", "ebitda", "normalized_ebit", "ebit", "normalized_net_profit", "net_profit"]:
        a, b = get(d, "Group", m, "fy2024"), get(d, "Group", m)
        rows.append({"metric": m, "fy2024": a, "fy2025": b, "change": b - a, "change_pct": 100 * (b - a) / a})
    p = pd.DataFrame(rows)
    p["margin_24_pct"] = 100 * p.fy2024 / get(d, "Group", "revenue", "fy2024")
    p["margin_25_pct"] = 100 * p.fy2025 / get(d, "Group", "revenue")
    return p


def one_offs(d) -> dict:
    opex_24 = get(d, "Group", "gross_profit", "fy2024") - get(d, "Group", "normalized_ebit", "fy2024")
    opex_25 = get(d, "Group", "gross_profit") - get(d, "Group", "normalized_ebit")
    return {"one_off_ebit": get(d, "Group", "normalized_ebit") - get(d, "Group", "ebit"),
            "one_off_net": get(d, "Group", "normalized_net_profit") - get(d, "Group", "net_profit"),
            "normalized_opex_24": opex_24, "normalized_opex_25": opex_25,
            "normalized_opex_change_pct": 100 * (opex_25 - opex_24) / opex_24}


# Illustrative 2026 drivers per segment: (revenue growth %, gross margin %). NOT company guidance.
SCENARIOS = {
    "Downside": {"International Express": (-15, 31.0), "Domestic Express": (5, 21.0), "Freight Forwarding": (0, 12.0), "Logistics": (10, 18.5)},
    "Base": {"International Express": (-8, 31.6), "Domestic Express": (8, 22.0), "Freight Forwarding": (4, 12.5), "Logistics": (15, 19.5)},
    "Upside": {"International Express": (-3, 32.0), "Domestic Express": (10, 23.0), "Freight Forwarding": (6, 13.0), "Logistics": (18, 20.5)},
}
OPEX_GROWTH_PCT = 0.0   # normalized overheads held flat, as in 2025 ("broadly in line with the prior year")


def scenarios(t, oo) -> pd.DataFrame:
    other = t[t.segment == "Other / eliminations"].iloc[0]
    rows = []
    for name, drv in SCENARIOS.items():
        rev = gp = 0.0
        for s, (g, m) in drv.items():
            r = float(t[t.segment == s].rev_25.iloc[0]) * (1 + g / 100)
            rev += r; gp += r * m / 100
        rev += other.rev_25; gp += other.gp_25          # other held flat
        opex = oo["normalized_opex_25"] * (1 + OPEX_GROWTH_PCT / 100)
        rows.append({"scenario": name, "revenue": rev, "gross_profit": gp, "gross_margin_pct": 100 * gp / rev,
                     "normalized_opex": opex, "normalized_ebit": gp - opex, "ebit_margin_pct": 100 * (gp - opex) / rev})
    return pd.DataFrame(rows)


def memo(t, mvr, pv, p, oo, sc) -> str:
    """Variance memo built only from computed numbers."""
    m = lambda x: f"AED {x / 1000:,.1f}m"
    seg = t[t.segment != "Other / eliminations"].set_index("segment")
    g = p.set_index("metric")
    ie, de = pv.set_index("segment").loc["International Express"], pv.set_index("segment").loc["Domestic Express"]
    best = seg.rev_change.idxmax(); worst = seg.rev_change.idxmin()
    base = sc.set_index("scenario")
    lines = [
        "# Variance memo: Aramex FY2025 vs FY2024",
        "",
        "*Generated by `src/fpa.py` from the published results. Every figure below is computed, not typed.*",
        "",
        "## Headline",
        f"- Revenue {m(g.loc['revenue','fy2025'])}, {g.loc['revenue','change_pct']:+.1f}% ({m(g.loc['revenue','change'])}).",
        f"- Gross profit {m(g.loc['gross_profit','fy2025'])}, {g.loc['gross_profit','change_pct']:+.1f}%; gross margin {g.loc['gross_profit','margin_24_pct']:.1f}% -> {g.loc['gross_profit','margin_25_pct']:.1f}%.",
        f"- Normalized EBIT {m(g.loc['normalized_ebit','fy2025'])}, {g.loc['normalized_ebit','change_pct']:+.1f}%; reported EBIT {m(g.loc['ebit','fy2025'])} after {m(oo['one_off_ebit'])} of one-off costs.",
        f"- Reported net profit {m(g.loc['net_profit','fy2025'])} ({g.loc['net_profit','change_pct']:+.0f}%); normalized {m(g.loc['normalized_net_profit','fy2025'])}.",
        "",
        "## Revenue: what moved",
        f"- Biggest gain: {best} {m(seg.loc[best,'rev_change'])} ({seg.loc[best,'rev_growth_pct']:+.1f}%). Biggest drop: {worst} {m(seg.loc[worst,'rev_change'])} ({seg.loc[worst,'rev_growth_pct']:+.1f}%).",
        f"- International Express: shipments {ie.shipments_24_m:.1f}m -> {ie.shipments_25_m:.1f}m. Volume alone would have cut revenue by {m(-ie.volume_effect)}; higher revenue per shipment (AED {ie.rev_per_shipment_24:.1f} -> {ie.rev_per_shipment_25:.1f}) recovered {m(ie.price_mix_effect)}.",
        f"- Domestic Express: shipments {de.shipments_24_m:.1f}m -> {de.shipments_25_m:.1f}m added {m(de.volume_effect)}; revenue per shipment AED {de.rev_per_shipment_24:.2f} -> {de.rev_per_shipment_25:.2f}.",
        "",
        "## Gross margin: mix vs rate",
        f"- Across the four products, gross margin moved {mvr['change_pp']:+.2f} pp. Of that, **mix** (revenue shifting from high-margin International Express to lower-margin products) explains {mvr['mix_effect_pp']:+.2f} pp and **rate** (margins changing within products) {mvr['rate_effect_pp']:+.2f} pp.",
        f"- International Express lost {m(-seg.loc['International Express','gp_change'])} of gross profit: {m(-seg.loc['International Express','gp_volume_effect'])} from lower revenue and {m(-seg.loc['International Express','gp_margin_effect'])} from a lower margin rate.",
        f"- Logistics added {m(seg.loc['Logistics','gp_change'])}: {m(seg.loc['Logistics','gp_volume_effect'])} from growth and {m(seg.loc['Logistics','gp_margin_effect'])} from a better margin ({seg.loc['Logistics','gm_24_pct']:.1f}% -> {seg.loc['Logistics','gm_25_pct']:.1f}%).",
        f"- Domestic Express grew revenue but its margin fell ({seg.loc['Domestic Express','gm_24_pct']:.1f}% -> {seg.loc['Domestic Express','gm_25_pct']:.1f}%), costing {m(-seg.loc['Domestic Express','gp_margin_effect'])}.",
        f"- Freight Forwarding's margin dip ({seg.loc['Freight Forwarding','gm_24_pct']:.1f}% -> {seg.loc['Freight Forwarding','gm_25_pct']:.1f}%) is mainly an accounting reclassification of transaction fees from overheads into direct costs, according to the company, so not a real deterioration.",
        "",
        "## Overheads",
        f"- Normalized overheads (gross profit minus normalized EBIT) were {m(oo['normalized_opex_25'])} vs {m(oo['normalized_opex_24'])} ({oo['normalized_opex_change_pct']:+.1f}%), so the EBIT decline is a gross-profit problem, not a cost-control problem.",
        "",
        "## 2026 scenarios (illustrative drivers, not guidance)",
    ] + [f"- {r.scenario}: revenue {m(r.revenue)}, gross margin {r.gross_margin_pct:.1f}%, normalized EBIT {m(r.normalized_ebit)} ({r.ebit_margin_pct:.1f}%)." for r in sc.itertuples()] + [
        "",
        "## So what",
        f"- More than half of the margin decline is mix ({mvr['mix_effect_pp'] / mvr['change_pp']:.0%}): the high-margin long-haul business is shrinking while regional products grow. Watch International Express revenue per shipment and Domestic Express margin recovery.",
        "- Logistics is the profit engine to scale: highest growth and the biggest margin improvement.",
    ]
    return "\n".join(lines) + "\n"


def run():
    d = load()
    t = segments(d); mvr = mix_vs_rate(t); pv = price_volume(d); p = pnl(d); oo = one_offs(d); sc = scenarios(t, oo)
    t.to_csv(T / "segment_bridge.csv", index=False)
    pd.Series(mvr).to_csv(T / "mix_vs_rate.csv", header=["value"])
    pv.to_csv(T / "express_price_volume.csv", index=False)
    p.to_csv(T / "pnl_cascade.csv", index=False)
    pd.Series(oo).to_csv(T / "one_offs.csv", header=["value"])
    sc.to_csv(T / "scenarios_2026.csv", index=False)
    text = memo(t, mvr, pv, p, oo, sc)
    (ROOT / "docs" / "variance_memo.md").write_text(text)
    return d, t, mvr, pv, p, oo, sc, text


if __name__ == "__main__":
    *_, text = run()
    print(text)
