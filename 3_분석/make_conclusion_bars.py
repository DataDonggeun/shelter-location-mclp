"""시사점 장 II 칸의 막대 두 개. 앞 장 그림(직선/보행 비교 지도, 요일별 개방률)의 값을 슬라이드 크기에서 읽히게 줄여 그린다.

값은 이미 계산된 집계다.
- 쉼터 219m 안의 길: make_network_figure.py 출력 (강남구 보행 구간 길이 기준, 직선 36.1%, 보행 18.0%)
- 문을 여는 쉼터: seoul_eda.ipynb 6절 (서울 무더위쉼터 4,092곳, 기본·연장·추가 운영 요일 합산. 평일은 월~금 평균)
색과 형식은 seoul_eda.ipynb를 따른다.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager

installed = {f.name for f in font_manager.fontManager.ttflist}
for font_name in ["Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"]:
    if font_name in installed:
        plt.rcParams["font.family"] = font_name
        break
plt.rcParams["axes.unicode_minus"] = False

INK, INK_SUB, INK_MUTED = "#0b0b0b", "#52514e", "#898781"
SURFACE, BORDER = "#fcfcfb", "#c3c2b7"
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#b5b3aa"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "text.color": INK, "font.size": 13})

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "2_데이터").exists())
OUT = ROOT / "4_결과" / "시사점"
OUT.mkdir(parents=True, exist_ok=True)


def hbars(labels, values, colors, fname, fmt="{:.0f}%"):
    fig, ax = plt.subplots(figsize=(5.2, 0.62 * len(labels) + 0.3))
    y = range(len(labels))[::-1]
    ax.barh(list(y), values, color=colors, height=0.62)
    for yy, v in zip(y, values):
        ax.text(v + 2, yy, fmt.format(v), va="center", fontsize=14, fontweight="bold", color=INK)
    ax.set_yticks(list(y), labels, fontsize=14, color=INK_SUB)
    ax.set_xlim(0, 118)
    ax.set_xticks([])
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(BORDER)
    ax.tick_params(length=0)
    fig.savefig(OUT / fname, dpi=200, bbox_inches="tight")
    plt.close(fig)


hbars(["직선 219m", "보행 219m"], [36.1, 18.0], [GRAY, BLUE], "01_쉼터219m안의길_직선_보행.png", fmt="{:.1f}%")
weekday = round((97 + 99 + 100 + 100 + 100) / 5)
hbars(["평일 평균", "토요일", "일요일"], [weekday, 27, 23], [BLUE, ORANGE, ORANGE], "02_요일별_여는쉼터.png")
print("평일 평균", weekday)
