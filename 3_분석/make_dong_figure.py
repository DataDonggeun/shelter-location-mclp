"""강남구 행정동 경계 지도(02)와 행정동별 기존 무더위쉼터 수 지도(01).

공개 자료만 쓴다(행정동 경계, 기존 쉼터 위치). 색과 형식은 seoul_eda.ipynb를 따르고 제목은 넣지 않는다.
"""
from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

installed = {f.name for f in font_manager.fontManager.ttflist}
for font_name in ["Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"]:
    if font_name in installed:
        plt.rcParams["font.family"] = font_name
        break
plt.rcParams["axes.unicode_minus"] = False

INK, INK_SUB = "#0b0b0b", "#52514e"
SURFACE, BORDER = "#ffffff", "#c3c2b7"   # 흰 카드 위에 바로 얹으므로 배경을 흰색으로 둔다
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#2a78d6", "#104281"]
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "text.color": INK})

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "2_데이터").exists())
INPUT = ROOT / "2_데이터" / "강남구_반입"
OUT = ROOT / "4_결과" / "강남구_행정동"
OUT.mkdir(parents=True, exist_ok=True)


def read_csv_any(path):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"{path}를 읽지 못했다")


dong = gpd.read_file(INPUT / "GangnamBoundary.shp").to_crs(5179).rename(columns={"ADM_NM": "dong"})
shelter = read_csv_any(INPUT / "GangnamCoolingCenter.csv").dropna(subset=["경도", "위도"])
shelter = gpd.GeoDataFrame(shelter, geometry=gpd.points_from_xy(shelter["경도"], shelter["위도"]),
                           crs=4326).to_crs(5179)
joined = gpd.sjoin(shelter, dong[["dong", "geometry"]], predicate="within")
dong["n"] = dong["dong"].map(joined.groupby("dong").size()).fillna(0).astype(int)
assert dong["n"].sum() == len(joined), "동에 붙지 않은 쉼터가 있다"

BINS = [(1, 1, "1곳"), (2, 2, "2곳"), (3, 4, "3~4곳"), (5, 6, "5~6곳"), (7, 99, "7곳 이상")]
dong["cls"] = dong["n"].map(lambda v: next(i for i, (lo, hi, _) in enumerate(BINS) if lo <= v <= hi))

fig, ax = plt.subplots(figsize=(10, 9))
dong.plot(ax=ax, color=[BLUE_RAMP[c] for c in dong["cls"]], edgecolor="white", linewidth=1.2, zorder=1)
ax.scatter(shelter.geometry.x, shelter.geometry.y, s=9, color=INK, edgecolors="white", linewidths=0.4, zorder=3)
for name, n, pt in zip(dong["dong"], dong["n"], dong.representative_point()):
    ax.text(pt.x, pt.y, f"{name}\n{n}곳", fontsize=8.5, color=INK, ha="center", va="center", zorder=4,
            linespacing=1.2, path_effects=[pe.withStroke(linewidth=2.6, foreground="white")])
ax.set_aspect("equal")
ax.set_axis_off()
handles = [Patch(color=BLUE_RAMP[i], label=lab) for i, (_, _, lab) in enumerate(BINS)]
handles.append(Line2D([], [], marker="o", linestyle="", markersize=5, color=INK, label=f"기존 쉼터 ({len(joined)}곳)"))
ax.legend(handles=handles, title="행정동별 기존 쉼터 수", frameon=False, loc="lower left", fontsize=10,
          title_fontsize=10, labelcolor=INK_SUB)
fig.savefig(OUT / "01_행정동별_기존쉼터수.png", dpi=200, bbox_inches="tight")
print(dong.sort_values("n")[["dong", "n"]].to_string(index=False))

# 02. 경계만 그린 지도. 데이터 소개 장에서 자료 자체를 보여 줄 때 쓴다.
LAND = "#eef3fa"
fig, ax = plt.subplots(figsize=(10, 9))
dong.plot(ax=ax, facecolor=LAND, edgecolor="#7f9bc4", linewidth=1.3, zorder=1)
for name, pt in zip(dong["dong"], dong.representative_point()):
    ax.text(pt.x, pt.y, name, fontsize=9.5, color="#223a65", ha="center", va="center", zorder=4,
            path_effects=[pe.withStroke(linewidth=2.6, foreground=LAND)])
ax.set_aspect("equal")
ax.set_axis_off()
fig.savefig(OUT / "02_행정동_경계.png", dpi=200, bbox_inches="tight")
