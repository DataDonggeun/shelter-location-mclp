"""반출한 공통 선정입지 지도(p = 15)의 세 모형 공통 6곳에 번호 ①~⑥을 붙인다. 발표에서 거리뷰 사진과 짝을 맞추는 데 쓴다.

지도는 안심구역 그림을 그대로 쓰고 번호만 얹는다. 점 위치는 그림에서 세 모형 공통 색(#a83c12)을 찾아 잡고,
어느 점이 어느 시설인지는 반출한 선정 후보지 좌표와 맞춰 정한다. 번호는 북쪽부터 매긴다.
입력은 반출 그림과 시설 좌표(공개 자료)뿐이다.
"""
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image
from scipy import ndimage

installed = {f.name for f in font_manager.fontManager.ttflist}
for font_name in ["Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"]:
    if font_name in installed:
        plt.rcParams["font.family"] = font_name
        break

DARK = np.array([168, 60, 18])      # ORANGE_RAMP[2], 세 모형 공통
SURFACE = "#fcfcfb"

ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "2_데이터").exists())
SRC = ROOT / "4_결과" / "안심구역_반출_261016"
OUT = ROOT / "4_결과" / "강남구_모형"
OUT.mkdir(parents=True, exist_ok=True)

img = np.asarray(Image.open(SRC / "03_공통_선정입지_p15.png").convert("RGB")).astype(int)
h, w, _ = img.shape
mask = np.abs(img - DARK).sum(axis=2) < 60
lab, n = ndimage.label(mask)
blobs = [b for b in ndimage.find_objects(lab) if (b[0].stop - b[0].start) > 10]
centers = np.array([[(b[1].start + b[1].stop) / 2, (b[0].start + b[0].stop) / 2] for b in blobs])
centers = centers[centers[:, 1] < h * 0.75]          # 왼쪽 아래 범례의 점은 뺀다
assert len(centers) == 6, f"지도에서 찾은 점이 {len(centers)}개다"

common = pd.read_csv(SRC / "공통_선정입지_p15.csv")
common = common[common["모형수"] == 3]
xy = (pd.read_csv(SRC / "p별_선정후보지.csv")[["candidate_id", "위도", "경도"]].drop_duplicates("candidate_id"))
common = common.merge(xy, on="candidate_id", validate="one_to_one")
pts = gpd.GeoSeries(gpd.points_from_xy(common["경도"], common["위도"]), crs=4326).to_crs(5179)
geo = np.column_stack([pts.x, pts.y])

# 지도는 축척이 같은 정방향 그림이라 픽셀 = s * (x, -y) + t 로 맞는다. 6! 가지 짝 중 잔차가 가장 작은 것을 고른다.
src = np.column_stack([geo[:, 0], -geo[:, 1]])
best = None
for perm in permutations(range(6)):
    dst = centers[list(perm)]
    sc, dc = src - src.mean(0), dst - dst.mean(0)
    s = (sc * dc).sum() / (sc ** 2).sum()
    res = np.abs(dst - (s * src + (dst.mean(0) - s * src.mean(0)))).max()
    if best is None or res < best[0]:
        best = (res, perm)
res, perm = best
assert res < 8, f"좌표와 점이 맞지 않는다 (최대 오차 {res:.1f}px)"
common["px"], common["py"] = centers[list(perm), 0], centers[list(perm), 1]
common = common.sort_values("py").reset_index(drop=True)      # 북쪽부터 번호
common["no"] = range(1, 7)

fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.imshow(img.astype(np.uint8))
ax.set_axis_off()
for r in common.itertuples():
    ax.scatter(r.px, r.py, s=1000, color=tuple(DARK / 255), edgecolors=SURFACE, linewidths=2.6, zorder=3)
    ax.text(r.px, r.py + 1, str(r.no), color="white", fontsize=20, fontweight="bold", ha="center", va="center", zorder=4)
fig.savefig(OUT / "05_공통_선정입지_p15_번호.png", dpi=100, facecolor=SURFACE)
plt.close(fig)

print(f"최대 오차 {res:.1f}px")
print(common[["no", "candidate_id", "시설명", "위도", "경도"]].to_string(index=False))
