"""자치구별로 서울 고령 거주인구와 고령 유동인구에서 차지하는 비중을 나란히 그린다.

유동인구는 같은 사람이 여러 번 잡히는 집계라 인원끼리 비교하지 않고 서울 합계 대비 비중으로 비교한다.
입력은 자치구 단위 집계표 두 개뿐이다(격자 행 없음). 색과 형식은 서울_EDA.ipynb를 따른다.
"""
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D

installed = {f.name for f in font_manager.fontManager.ttflist}
for font_name in ["Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"]:
    if font_name in installed:
        plt.rcParams["font.family"] = font_name
        break
plt.rcParams["axes.unicode_minus"] = False

INK, INK_SUB, INK_MUTED = "#0b0b0b", "#52514e", "#898781"
SURFACE, BORDER, GRID = "#fcfcfb", "#c3c2b7", "#e1e0d9"
BLUE, ORANGE = "#2a78d6", "#eb6834"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": BORDER, "axes.labelcolor": INK_SUB, "text.color": INK,
    "xtick.color": INK_MUTED, "ytick.color": INK_SUB,
})

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "2_데이터").exists())
RES = ROOT / "4_결과" / "서울_EDA_거주인구" / "03_자치구별_고령거주인구_커버율.csv"
FLOW = ROOT / "4_결과" / "안심구역_반출_261016" / "01_자치구별_쉼터와_유동인구.csv"
OUT = ROOT / "4_결과" / "서울_EDA_거주인구" / "04_자치구별_거주_유동_비중.png"

res = pd.read_csv(RES)[["gu", "거주인구_고령"]]
flow = pd.read_csv(FLOW)[["gu", "유동인구_60대이상"]]
d = res.merge(flow, on="gu", validate="one_to_one")
assert len(d) == 25, f"자치구가 {len(d)}개다"
d["res"] = d["거주인구_고령"] / d["거주인구_고령"].sum() * 100
d["flow"] = d["유동인구_60대이상"] / d["유동인구_60대이상"].sum() * 100
d = d.assign(gap=d["flow"] - d["res"]).sort_values("gap").reset_index(drop=True)

fig, ax = plt.subplots(figsize=(8, 9))
y = range(len(d))
ax.hlines(y, d[["res", "flow"]].min(axis=1), d[["res", "flow"]].max(axis=1), color=GRID, linewidth=3, zorder=1)
ax.scatter(d["res"], y, s=46, color=BLUE, zorder=3)
ax.scatter(d["flow"], y, s=46, color=ORANGE, zorder=3)
ax.set_yticks(list(y), d["gu"])
for lab in ax.get_yticklabels():
    if lab.get_text() == "강남구":
        lab.set_fontweight("bold")
        lab.set_color(INK)
ax.set_xlabel("서울 합계 대비 비중 (%)")
ax.set_ylim(-0.7, len(d) - 0.3)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
ax.tick_params(length=0)
ax.legend(handles=[
    Line2D([], [], marker="o", linestyle="", color=BLUE, markersize=7, label="60세 이상 거주인구"),
    Line2D([], [], marker="o", linestyle="", color=ORANGE, markersize=7, label="60대 이상 유동인구"),
], frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2, fontsize=9, labelcolor=INK_SUB,
    borderaxespad=0.2)
fig.savefig(OUT, dpi=200, bbox_inches="tight")
print(d[["gu", "res", "flow", "gap"]].round(2).tail(5).to_string())
