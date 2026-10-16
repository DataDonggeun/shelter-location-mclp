"""데이터안심구역 유동인구 자료와 같은 형식의 모의 CSV를 만든다.

안심구역 원자료는 반출할 수 없어서, 로컬에서 코드를 개발할 때 쓸 가짜 자료가 필요하다.
열 이름, 좌표계(EPSG:5179, 50m 격자), 행 수만 실제와 맞추고 값은 전부 난수다.
분석 결과로 쓰면 안 된다.

만드는 파일 (2_데이터/모의/, 월마다 한 벌):
    seoul_flow_age_YYYYMM.csv     성별ㆍ연령대   217,630행  구분자 |
    seoul_flow_time_YYYYMM.csv    시간대         217,432행  구분자 |
    seoul_flow_day_YYYYMM.csv     요일           217,630행  구분자 |
    seoul_flow_merged_YYYYMM.csv  세 파일 병합   217,630행  구분자 ,

실행: python 3_분석/make_mock_flow_population.py
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "2_데이터" / "원본"
PROC = ROOT / "2_데이터" / "가공"
OUT = ROOT / "2_데이터" / "모의"

MONTHS = [202401, 202412]
N_AGE, N_TIME, N_DAY = 217_630, 217_432, 217_630

# 격자 원점. 안심구역 자료의 X_COORD가 935083.9918처럼 50m 간격으로 떨어진다.
GRID_M = 50
X0, Y0 = 935083.9918, 1950929.0

AGES = ["10G", "20G", "30G", "40G", "50G", "60GU"]
AGE_COLS = [f"{g}_FLOW_POP_CNT_{a}" for g in ("MAN", "WMAN") for a in AGES]
TIME_COLS = [f"THST_{h:02d}" for h in range(24)]
DAY_COLS = [f"FLOW_POP_CNT_{d}" for d in ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")]
KEYS = ["STD_YM", "X_COORD", "Y_COORD"]


def facility_xy():
    """서울 쉼터와 후보시설 좌표. 격자를 시가지 쪽에 깔기 위한 기준점이다."""
    shelter = pd.read_csv(RAW / "서울시_무더위쉼터.csv", encoding="cp949")
    cand = pd.read_csv(PROC / "서울시_후보시설.csv", encoding="utf-8-sig")
    lonlat = pd.concat([shelter[["경도", "위도"]], cand[["경도", "위도"]]]).apply(
        pd.to_numeric, errors="coerce").dropna()
    lonlat = lonlat[lonlat["경도"].between(126.7, 127.3) & lonlat["위도"].between(37.4, 37.75)]
    to_5179 = Transformer.from_crs(4326, 5179, always_xy=True)
    x, y = to_5179.transform(lonlat["경도"].to_numpy(), lonlat["위도"].to_numpy())
    return np.column_stack([x, y])


def make_grid(pts, n):
    """시설에서 가까운 순으로 50m 격자 n개를 고른다."""
    pad = 1500
    i0 = np.floor((pts[:, 0].min() - pad - X0) / GRID_M)
    i1 = np.ceil((pts[:, 0].max() + pad - X0) / GRID_M)
    j0 = np.floor((pts[:, 1].min() - pad - Y0) / GRID_M)
    j1 = np.ceil((pts[:, 1].max() + pad - Y0) / GRID_M)
    gx, gy = np.meshgrid(X0 + GRID_M * np.arange(i0, i1 + 1), Y0 + GRID_M * np.arange(j0, j1 + 1))
    xy = np.column_stack([gx.ravel(), gy.ravel()])
    dist, _ = cKDTree(pts).query(xy)
    if len(xy) < n:
        raise ValueError(f"격자 {len(xy)}개로는 {n}행을 채울 수 없다")
    keep = np.sort(np.argsort(dist, kind="stable")[:n])
    return xy[keep], dist[keep]


def to_gdf(df):
    """노트북과 같은 절차로 lon, lat, geometry를 붙인다."""
    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["X_COORD"], df["Y_COORD"]),
                         crs="EPSG:5179").to_crs("EPSG:4326")
    g["lon"] = g.geometry.x
    g["lat"] = g.geometry.y
    return g


def make_month(std_ym, xy, dist):
    rng = np.random.default_rng(std_ym)
    key = pd.DataFrame({"STD_YM": std_ym, "X_COORD": xy[:, 0].round(4), "Y_COORD": xy[:, 1].round(4)})

    # 격자별 기본 규모. 시설에서 멀수록 작게 둔다.
    base = rng.lognormal(np.log(6), 1.0, N_AGE) * (0.3 + np.exp(-dist / 400))

    def table(cols, share, noise):
        v = base[:, None] * np.asarray(share)[None, :] * rng.lognormal(0, noise, (N_AGE, len(cols)))
        return pd.concat([key, pd.DataFrame(v.round(2), columns=cols)], axis=1)

    age_share = np.array([.03, .08, .09, .09, .09, .12, .03, .08, .08, .09, .10, .15])
    time_share = 0.15 + np.exp(-((np.arange(24) - 13) / 5.0) ** 2)
    day_share = np.array([1.0, 1.0, 1.02, 1.02, 1.08, 0.95, 0.85])

    age = table(AGE_COLS, age_share / age_share.sum(), 0.3)
    time = table(TIME_COLS, time_share / time_share.sum(), 0.25)
    day = table(DAY_COLS, day_share, 0.1)

    # 시간대 파일만 행이 적다. 병합하면 그 격자의 THST 열이 비게 된다.
    time = time.drop(index=rng.choice(N_AGE, N_AGE - N_TIME, replace=False)).reset_index(drop=True)
    assert (len(age), len(time), len(day)) == (N_AGE, N_TIME, N_DAY)

    age.to_csv(OUT / f"seoul_flow_age_{std_ym}.csv", sep="|", index=False)
    time.to_csv(OUT / f"seoul_flow_time_{std_ym}.csv", sep="|", index=False)
    day.to_csv(OUT / f"seoul_flow_day_{std_ym}.csv", sep="|", index=False)

    on = KEYS + ["geometry", "lon", "lat"]
    merged = to_gdf(age).merge(to_gdf(time), on=on, how="left").merge(to_gdf(day), on=on, how="left")
    assert len(merged) == N_AGE
    merged.to_csv(OUT / f"seoul_flow_merged_{std_ym}.csv", index=False)
    print(std_ym, "병합 결과:", merged.shape, "THST 결측 행:", int(merged["THST_00"].isna().sum()))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    xy, dist = make_grid(facility_xy(), N_AGE)
    for std_ym in MONTHS:
        make_month(std_ym, xy, dist)
    print("저장:", OUT)


if __name__ == "__main__":
    main()
