"""Build an Excel FP&A model with LIVE formulas: change a driver and every result updates.

Sheets
  Inputs     published FY2024 / FY2025 figures (blue = hard-coded input)
  Bridge     revenue and gross-profit bridge by segment (formulas)
  Scenarios  2026 driver-based forecast: edit growth and margin cells (yellow)
"""
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import fpa

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "aramex_fpa_model.xlsx"

BLUE = Font(color="1F4E9E"); BOLD = Font(bold=True); WHITE = Font(bold=True, color="FFFFFF")
HEAD = PatternFill("solid", fgColor="1F3864"); YELLOW = PatternFill("solid", fgColor="FFF2CC"); GREY = PatternFill("solid", fgColor="F2F4F7")
THIN = Border(bottom=Side(style="thin", color="D0D7E2"))
K = '#,##0;(#,##0)'; PCT = '0.0%'


def header(ws, row, labels):
    for i, h in enumerate(labels, 1):
        c = ws.cell(row=row, column=i, value=h); c.font = WHITE; c.fill = HEAD; c.alignment = Alignment(horizontal="center", wrap_text=True)


def build():
    d = fpa.load()
    t = fpa.segments(d)
    oo = fpa.one_offs(d)
    wb = Workbook()

    # ---------------- Inputs
    ws = wb.active; ws.title = "Inputs"
    ws["A1"] = "Aramex PJSC: published results (AED thousands)"; ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "Source: Aramex FY2025 results press release, 10 Feb 2026. Blue = input transcribed from the release."
    header(ws, 4, ["Segment", "Revenue FY2024", "Revenue FY2025", "Gross profit FY2024", "Gross profit FY2025"])
    names = list(t.segment)
    for i, r in enumerate(t.itertuples(), start=5):
        ws.cell(row=i, column=1, value=r.segment)
        for j, v in enumerate([r.rev_24, r.rev_25, r.gp_24, r.gp_25], start=2):
            c = ws.cell(row=i, column=j, value=round(v)); c.font = BLUE; c.number_format = K
    last = 4 + len(names)
    tot = last + 1
    ws.cell(row=tot, column=1, value="Group").font = BOLD
    for j in range(2, 6):
        col = get_column_letter(j)
        c = ws.cell(row=tot, column=j, value=f"=SUM({col}5:{col}{last})"); c.font = BOLD; c.number_format = K
    ws.cell(row=tot + 2, column=1, value="Normalized EBIT")
    for j, v in [(2, fpa.get(d, "Group", "normalized_ebit", "fy2024")), (3, fpa.get(d, "Group", "normalized_ebit"))]:
        c = ws.cell(row=tot + 2, column=j, value=round(v)); c.font = BLUE; c.number_format = K
    ws.cell(row=tot + 3, column=1, value="Normalized overheads (GP - normalized EBIT)")
    ws.cell(row=tot + 3, column=2, value=f"=D{tot}-B{tot + 2}").number_format = K
    ws.cell(row=tot + 3, column=3, value=f"=E{tot}-C{tot + 2}").number_format = K
    ws.column_dimensions["A"].width = 42
    for col in "BCDE":
        ws.column_dimensions[col].width = 18

    # ---------------- Bridge
    b = wb.create_sheet("Bridge")
    b["A1"] = "FY2024 -> FY2025 bridge (formulas reference Inputs)"; b["A1"].font = Font(bold=True, size=14)
    header(b, 3, ["Segment", "Revenue change", "Growth %", "GM FY2024", "GM FY2025", "GP volume effect", "GP margin effect", "GP change", "Check"])
    for i in range(len(names)):
        r = 4 + i; src = 5 + i
        b.cell(row=r, column=1, value=f"=Inputs!A{src}")
        b.cell(row=r, column=2, value=f"=Inputs!C{src}-Inputs!B{src}").number_format = K
        b.cell(row=r, column=3, value=f"=B{r}/Inputs!B{src}").number_format = PCT
        b.cell(row=r, column=4, value=f"=Inputs!D{src}/Inputs!B{src}").number_format = PCT
        b.cell(row=r, column=5, value=f"=Inputs!E{src}/Inputs!C{src}").number_format = PCT
        b.cell(row=r, column=6, value=f"=B{r}*D{r}").number_format = K
        b.cell(row=r, column=7, value=f"=Inputs!C{src}*(E{r}-D{r})").number_format = K
        b.cell(row=r, column=8, value=f"=Inputs!E{src}-Inputs!D{src}").number_format = K
        b.cell(row=r, column=9, value=f'=IF(ABS(F{r}+G{r}-H{r})<1,"OK","CHECK")')
    br = 4 + len(names)
    b.cell(row=br, column=1, value="Group").font = BOLD
    for col in "BFGH":
        c = b[f"{col}{br}"]; c.value = f"=SUM({col}4:{col}{br - 1})"; c.font = BOLD; c.number_format = K
    b.column_dimensions["A"].width = 26
    for col in "BCDEFGHI":
        b.column_dimensions[col].width = 16

    # ---------------- Scenarios
    s = wb.create_sheet("Scenarios")
    s["A1"] = "2026 driver-based scenarios (edit the yellow cells)"; s["A1"].font = Font(bold=True, size=14)
    s["A2"] = "Illustrative assumptions, not company guidance. Other / eliminations held at FY2025."
    row = 4
    summary_rows = {}
    for name, drv in fpa.SCENARIOS.items():
        s.cell(row=row, column=1, value=name).font = Font(bold=True, size=12)
        header(s, row + 1, ["Segment", "FY2025 revenue", "Growth % 2026", "Revenue 2026", "Gross margin % 2026", "Gross profit 2026"])
        first = row + 2
        for i, seg in enumerate(fpa.SEGMENTS):
            r = first + i; src = 5 + names.index(seg)
            g, m = drv[seg]
            s.cell(row=r, column=1, value=seg)
            s.cell(row=r, column=2, value=f"=Inputs!C{src}").number_format = K
            c = s.cell(row=r, column=3, value=g / 100); c.fill = YELLOW; c.number_format = PCT
            s.cell(row=r, column=4, value=f"=B{r}*(1+C{r})").number_format = K
            c = s.cell(row=r, column=5, value=m / 100); c.fill = YELLOW; c.number_format = PCT
            s.cell(row=r, column=6, value=f"=D{r}*E{r}").number_format = K
        r = first + len(fpa.SEGMENTS)
        osrc = 5 + names.index("Other / eliminations")
        s.cell(row=r, column=1, value="Other / eliminations")
        s.cell(row=r, column=4, value=f"=Inputs!C{osrc}").number_format = K
        s.cell(row=r, column=6, value=f"=Inputs!E{osrc}").number_format = K
        tr = r + 1
        s.cell(row=tr, column=1, value="Total").font = BOLD
        for col in "DF":
            c = s[f"{col}{tr}"]; c.value = f"=SUM({col}{first}:{col}{r})"; c.font = BOLD; c.number_format = K
        s.cell(row=tr + 1, column=1, value="Normalized overheads (FY2025 x (1 + growth))")
        c = s.cell(row=tr + 1, column=3, value=fpa.OPEX_GROWTH_PCT / 100); c.fill = YELLOW; c.number_format = PCT
        s.cell(row=tr + 1, column=6, value=f"=Inputs!C{tot + 3}*(1+C{tr + 1})").number_format = K
        s.cell(row=tr + 2, column=1, value="Normalized EBIT").font = BOLD
        c = s.cell(row=tr + 2, column=6, value=f"=F{tr}-F{tr + 1}"); c.font = BOLD; c.number_format = K
        s.cell(row=tr + 3, column=1, value="EBIT margin")
        s.cell(row=tr + 3, column=6, value=f"=F{tr + 2}/D{tr}").number_format = PCT
        summary_rows[name] = (tr, tr + 2)
        row = tr + 5
    s.column_dimensions["A"].width = 44
    for col in "BCDEF":
        s.column_dimensions[col].width = 18

    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    print("written", build())
