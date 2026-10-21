"""신규 쉼터 0~30곳(5곳 단위)에서 세 모형의 지표를 그린다. 발표 6-3, 6-4 장에 쓴다.

입력은 안심구역에서 반출한 모형별 지표 집계표와 선정 후보지 목록뿐이다(격자 행 없음).
반출 그림(05~07)은 0~40곳을 1곳 단위로 그렸다. 발표본은 0~30곳, 5곳 단위로 맞춘다.
색과 형식은 seoul_eda.ipynb를 따른다. 모형 색은 MCLP 파랑, 형평성 MCLP 주황, p-median 청록.
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
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": BORDER, "axes.labelcolor": INK_SUB, "text.color": INK,
    "xtick.color": INK_MUTED, "ytick.color": INK_SUB, "font.size": 11,
})

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "2_데이터").exists())
SRC = ROOT / "4_결과" / "안심구역_반출_261016"
OUT = ROOT / "4_결과" / "강남구_모형"
OUT.mkdir(parents=True, exist_ok=True)

MODELS = [("MCLP", BLUE), ("형평성 MCLP", ORANGE), ("p-median", AQUA)]
STEPS = list(range(0, 31, 5))

m = pd.read_csv(SRC / "모형별_p별_지표.csv")
m = m[m["p"].isin(STEPS)]
assert len(m) == len(STEPS) * len(MODELS), f"행 수가 {len(m)}개다"
wide = {col: m.pivot(index="p", columns="model", values=col)
        for col in ["coverage_pct", "mean_dist_m", "min_dong_pct"]}


def clean(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def legend_top(ax, handles):
    ax.legend(handles=handles, frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0),
              ncol=len(handles), fontsize=10, labelcolor=INK_SUB, borderaxespad=0.2,
              handlelength=1.4, columnspacing=1.2)


def model_handles():
    return [Line2D([], [], color=c, linewidth=2.4, marker="o", markersize=5, label=n) for n, c in MODELS]


def line_figure(col, ylabel, fname):
    fig, ax = plt.subplots(figsize=(5.4, 4.2))
    for name, color in MODELS:
        s = wide[col][name]
        ax.plot(s.index, s.values, color=color, linewidth=2.4, marker="o", markersize=5, zorder=3)
    ax.set_xticks(STEPS)
    ax.set_xlim(-1, 31)
    ax.set_xlabel("신규 쉼터 수 (곳)")
    ax.set_ylabel(ylabel)
    clean(ax)
    legend_top(ax, model_handles())
    fig.savefig(OUT / fname, dpi=200, bbox_inches="tight")
    plt.close(fig)


line_figure("coverage_pct", "커버율 (%)", "01_신규쉼터수별_커버율.png")
line_figure("mean_dist_m", "평균 보행거리 (m)", "02_신규쉼터수별_평균보행거리.png")
line_figure("min_dong_pct", "최저 행정동 커버율 (%)", "03_신규쉼터수별_최저동커버율.png")

# 5곳 더할 때마다 늘어나는 커버율
gain = wide["coverage_pct"].diff().dropna()
fig, ax = plt.subplots(figsize=(7.2, 4.2))
w = 0.26
for k, (name, color) in enumerate(MODELS):
    ax.bar([i + (k - 1) * w for i in range(len(gain))], gain[name].values, width=w, color=color, zorder=3)
ax.set_xticks(range(len(gain)), [f"{p - 5}→{p}곳" for p in gain.index])
ax.set_ylabel("늘어난 커버율 (%p)")
clean(ax)
ax.grid(axis="x", visible=False)
legend_top(ax, [Line2D([], [], color=c, linewidth=8, label=n) for n, c in MODELS])
fig.savefig(OUT / "04_5곳당_커버율증가폭.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# 규모를 5곳 늘릴 때 앞 단계 선정지가 몇 곳 남는지
sel = pd.read_csv(SRC / "p별_선정후보지.csv")
keep = {}
for name, _ in MODELS:
    s = {p: set(g["candidate_id"]) for p, g in sel[sel["model"] == name].groupby("p")}
    keep[name] = [f"{len(s[p] & s[p + 5])}/{p}" for p in STEPS[1:-1]]

print(wide["coverage_pct"].round(1).to_string())
print(wide["mean_dist_m"].round(0).to_string())
print(wide["min_dong_pct"].round(1).to_string())
print(gain.round(2).to_string())
print("앞 단계 유지:", keep)
