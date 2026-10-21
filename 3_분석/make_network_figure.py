"""강남구 보행 네트워크에서 직선 219m와 보행 219m 커버 범위를 비교하는 지도.

유동인구는 쓰지 않는다. 보행 네트워크, 기존 쉼터, 행정동 경계만 쓰므로 로컬에서 실행된다.
그래프 구성과 스냅은 GangnamAnalysis.ipynb 2절과 같다. 색과 형식은 seoul_eda.ipynb를 따른다.

링크 색
- 파랑: 가장 가까운 쉼터까지 보행거리 219m 이내
- 주황: 직선거리로는 219m 이내지만 보행거리는 219m 밖
- 회색: 둘 다 219m 밖
거리는 링크 중간점 기준이다.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from scipy.spatial import cKDTree
from shapely import wkt
from shapely.geometry import Point

installed = {f.name for f in font_manager.fontManager.ttflist}
for font_name in ["Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"]:
    if font_name in installed:
        plt.rcParams["font.family"] = font_name
        break
plt.rcParams["axes.unicode_minus"] = False

INK, INK_SUB, INK_MUTED = "#0b0b0b", "#52514e", "#898781"
SURFACE, LAND, BORDER, GRID = "#fcfcfb", "#f3f2ee", "#c3c2b7", "#e1e0d9"
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#b5b3aa"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "text.color": INK})

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "2_데이터").exists())
INPUT = ROOT / "2_데이터" / "강남구_반입"
OUT = ROOT / "4_결과" / "강남구_네트워크"
OUT.mkdir(parents=True, exist_ok=True)
T = 219


def read_csv_any(path, **kw):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"{path}를 읽지 못했다")


# 그래프. 같은 노드 쌍이면 짧은 링크를 남기고 가장 큰 연결요소만 쓴다.
net = read_csv_any(INPUT / "GangnamNetwork.csv", dtype=str, low_memory=False)
links = net[net["노드링크 유형"] == "LINK"].copy()
links["length"] = pd.to_numeric(links["링크 길이"], errors="coerce")
links = links[np.isfinite(links["length"]) & (links["length"] > 0)]
node_rows = net[(net["노드링크 유형"] == "NODE") & net["노드 WKT"].notna()]
node_pt = dict(zip(node_rows["노드 ID"], node_rows["노드 WKT"].map(wkt.loads)))

G = nx.Graph()
for u, v, length, g in zip(links["시작노드 ID"], links["종료노드 ID"], links["length"], links["링크 WKT"]):
    if u == v or not isinstance(g, str):
        continue
    line = wkt.loads(g)
    parts = list(line.geoms) if line.geom_type == "MultiLineString" else [line]
    node_pt.setdefault(u, Point(parts[0].coords[0]))
    node_pt.setdefault(v, Point(parts[-1].coords[-1]))
    if not G.has_edge(u, v) or length < G[u][v]["length"]:
        G.add_edge(u, v, length=float(length), geom=line)
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()

ids = np.array(list(G.nodes))
node_geo = gpd.GeoSeries([node_pt[n] for n in ids], crs=4326).to_crs(5179)
node_xy = dict(zip(ids, zip(node_geo.x, node_geo.y)))
tree = cKDTree(np.column_stack([node_geo.x, node_geo.y]))

shelter = read_csv_any(INPUT / "GangnamCoolingCenter.csv").dropna(subset=["경도", "위도"])
shelter = gpd.GeoDataFrame(shelter, geometry=gpd.points_from_xy(shelter["경도"], shelter["위도"]),
                           crs=4326).to_crs(5179)
_, idx = tree.query(np.column_stack([shelter.geometry.x, shelter.geometry.y]))
shelter["node"] = ids[idx]
shelter = shelter.drop_duplicates("node")

near = nx.multi_source_dijkstra_path_length(G, shelter["node"].tolist(), weight="length")
sh_tree = cKDTree(np.column_stack([shelter.geometry.x, shelter.geometry.y]))

# 링크 중간점의 보행거리와 직선거리
edges = list(G.edges(data=True))
mid = np.array([[(node_xy[u][0] + node_xy[v][0]) / 2, (node_xy[u][1] + node_xy[v][1]) / 2] for u, v, _ in edges])
net_d = np.array([min(near[u], near[v]) + d["length"] / 2 for u, v, d in edges])
str_d, _ = sh_tree.query(mid)
length = np.array([d["length"] for *_, d in edges])
cls = np.where(net_d <= T, 0, np.where(str_d <= T, 1, 2))   # 0 보행 안, 1 직선만 안, 2 밖

geoms = gpd.GeoSeries([d["geom"] for *_, d in edges], crs=4326).to_crs(5179)
segs = [np.asarray(g.coords) if g.geom_type == "LineString" else np.vstack([np.asarray(p.coords) for p in g.geoms])
        for g in geoms]

dong = gpd.read_file(INPUT / "GangnamBoundary.shp").to_crs(5179)

fig, ax = plt.subplots(figsize=(10, 9))
dong.plot(ax=ax, facecolor=LAND, edgecolor=BORDER, linewidth=0.6, zorder=1)
for c, color, lw, z in [(2, GRAY, 0.35, 2), (1, ORANGE, 0.9, 3), (0, BLUE, 0.9, 4)]:
    ax.add_collection(LineCollection([s for s, k in zip(segs, cls) if k == c], colors=color, linewidths=lw, zorder=z))
ax.scatter(shelter.geometry.x, shelter.geometry.y, s=14, color=INK, edgecolors=SURFACE, linewidths=0.6, zorder=5)
ax.set_aspect("equal")
ax.set_axis_off()
ax.legend(handles=[
    Line2D([], [], color=BLUE, linewidth=2.5, label=f"보행 {T}m 이내"),
    Line2D([], [], color=ORANGE, linewidth=2.5, label=f"직선 {T}m 이내, 보행 {T}m 밖"),
    Line2D([], [], color=GRAY, linewidth=2.5, label=f"둘 다 {T}m 밖"),
    Line2D([], [], marker="o", linestyle="", markersize=6, color=INK, label=f"기존 쉼터 ({len(shelter)}곳)"),
], title="가장 가까운 쉼터까지 거리", frameon=False, loc="lower left", fontsize=10, title_fontsize=10,
    labelcolor=INK_SUB)
fig.savefig(OUT / "01_직선_보행_219m_비교.png", dpi=200, bbox_inches="tight")

km = lambda m: m.sum() / 1000
in_str = cls <= 1
print(f"링크 {len(edges):,}개, 총 {km(length):.0f}km, 기존 쉼터 노드 {len(shelter)}곳")
print(f"보행 {T}m 이내 {km(length[cls == 0]):.0f}km ({length[cls == 0].sum() / length.sum() * 100:.1f}%)")
print(f"직선 {T}m 이내 {km(length[in_str]):.0f}km ({length[in_str].sum() / length.sum() * 100:.1f}%)")
print(f"직선 {T}m 이내 길 중 보행 {T}m 밖: {length[cls == 1].sum() / length[in_str].sum() * 100:.1f}%")
