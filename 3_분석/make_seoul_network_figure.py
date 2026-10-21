"""서울 전역 보행 네트워크 지도. 강남구 구간만 파랑으로 칠해 '같은 틀을 다른 구로 넓힐 수 있다'를 보여 준다. 발표 시사점 장에 쓴다.

유동인구는 쓰지 않는다. 보행 네트워크와 자치구 경계(공개 자료)만 쓰므로 로컬에서 실행된다.
색과 형식은 서울_EDA.ipynb를 따른다.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

installed = {f.name for f in font_manager.fontManager.ttflist}
for font_name in ["Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"]:
    if font_name in installed:
        plt.rcParams["font.family"] = font_name
        break
plt.rcParams["axes.unicode_minus"] = False

INK, INK_SUB, INK_MUTED = "#0b0b0b", "#52514e", "#898781"
SURFACE, LAND, BORDER = "#fcfcfb", "#f3f2ee", "#c3c2b7"
BLUE, GRAY = "#2a78d6", "#c9c7bf"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "text.color": INK})

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "2_데이터").exists())
INPUT = ROOT / "2_데이터" / "서울_모형입력"
OUT = ROOT / "4_결과" / "서울_네트워크"
OUT.mkdir(parents=True, exist_ok=True)
TARGET = "강남구"

net = pd.read_csv(INPUT / "SeoulNetwork.csv", encoding="cp949", usecols=["노드링크 유형", "링크 WKT", "시군구명"],
                  dtype=str)
links = net[(net["노드링크 유형"] == "LINK") & net["링크 WKT"].notna()]
geo = gpd.GeoSeries.from_wkt(links["링크 WKT"].to_numpy(), crs=4326).to_crs(5179)
is_target = (links["시군구명"] == TARGET).to_numpy()
assert is_target.any(), f"{TARGET} 링크가 없다. 시군구명 값을 확인한다"

gu = gpd.read_file(INPUT / "SeoulBoundary.shp").to_crs(5179)


def segments(series):
    out = []
    for g in series:
        parts = g.geoms if g.geom_type == "MultiLineString" else [g]
        out.extend(np.asarray(p.coords)[:, :2] for p in parts)
    return out


fig, ax = plt.subplots(figsize=(10, 8.5))
gu.plot(ax=ax, facecolor=LAND, edgecolor="none", zorder=1)
ax.add_collection(LineCollection(segments(geo[~is_target]), colors=GRAY, linewidths=0.25, zorder=2))
ax.add_collection(LineCollection(segments(geo[is_target]), colors=BLUE, linewidths=0.35, zorder=3))
gu.boundary.plot(ax=ax, color=BORDER, linewidth=0.8, zorder=4)
ax.set_aspect("equal")
ax.set_axis_off()
ax.legend(handles=[
    Line2D([], [], color=BLUE, linewidth=2.5, label=f"보행 구간, {TARGET} (분석 완료)"),
    Line2D([], [], color=GRAY, linewidth=2.5, label="보행 구간, 다른 24개 구"),
], frameon=False, loc="lower left", fontsize=10, labelcolor=INK_SUB)
fig.savefig(OUT / "01_서울_보행네트워크.png", dpi=200, bbox_inches="tight")
plt.close(fig)

print(f"링크 {len(links):,}개, 그중 {TARGET} {is_target.sum():,}개, 자치구 {links['시군구명'].nunique()}개")
