#!/usr/bin/env python3
"""Spike for US-415: percentile aggregation correctness res9 -> res7/8.

Compares:
  (a) average raw lims_score per parent then percentile rank at parent level (correct)
  (b) percentile rank at res9 then average parent percentile (naive)

Run: python scripts/measure_percentile_agg.py --cities nyc chicago --out-metrics /tmp/percentile_metrics.json
"""

import argparse
import json
import random
import math
from collections import defaultdict

import h3

from src.spatial.city_registry import REGISTRY, CityId
from src.spatial.h3_indexer import H3SpatialIndexer

# copy from snapshot_builder.py:102
def _percentile_ranks(values: list[float]) -> list[float]:
    count = len(values)
    if count == 0:
        return []
    if count == 1:
        return [100.0]
    order = sorted(range(count), key=lambda i: values[i])
    ranks = [0.0]*count
    start=0
    while start < count:
        end=start
        while end+1 < count and values[order[end+1]] == values[order[start]]:
            end+=1
        percentile = round(((start+end)/2)/(count-1)*100.0, 2)
        for pos in range(start, end+1):
            ranks[order[pos]] = percentile
        start=end+1
    return ranks

def cells_for_city_broken(city_id: str, k_ring: int=1):
    reg = REGISTRY[CityId(city_id)]
    cells=set()
    for meta in reg.submarkets.values():
        center = H3SpatialIndexer.latlng_to_h3(meta.lat, meta.lng, resolution=9)
        cells.update(H3SpatialIndexer.get_k_ring(center, k=k_ring))
    return cells

def synth_scores(cells: set[str], city: str):
    reg = REGISTRY[CityId(city)]
    # assign each cell score = base_lims of nearest submarket + noise, to get realistic spatial variance
    # simplify: assign random 60-95 plus city offset
    scores={}
    for c in cells:
        # use base_lims of random submarket as proxy for spatial cluster
        # instead deterministic hash of cell
        h = hash(c) & 0xffff
        base = 70 + (h % 25)  # 70-95
        scores[c]= float(base) + random.uniform(-3,3)
    return scores

def aggregate_avg_raw(cells: set[str], scores: dict[str,float], to_res: int):
    parent_to_vals = defaultdict(list)
    for c, v in scores.items():
        p = h3.cell_to_parent(c, to_res)
        parent_to_vals[p].append(v)
    parent_avg = {p: sum(vals)/len(vals) for p, vals in parent_to_vals.items()}
    return parent_avg

def aggregate_avg_percentile(cells: set[str], scores: dict[str,float], to_res: int, national_ranks: dict[str,float]):
    parent_to_ranks = defaultdict(list)
    for c in cells:
        p = h3.cell_to_parent(c, to_res)
        parent_to_ranks[p].append(national_ranks[c])
    return {p: sum(ranks)/len(ranks) for p, ranks in parent_to_ranks.items()}

def spearman(a: list[float], b: list[float]) -> float:
    # rank correlation
    n=len(a)
    if n<2:
        return 1.0
    # get ranks
    def rank(vals):
        order=sorted(range(n), key=lambda i: vals[i])
        r=[0]*n
        for pos, idx in enumerate(order):
            r[idx]=pos
        return r
    ra=rank(a); rb=rank(b)
    # pearson on ranks
    ma=sum(ra)/n; mb=sum(rb)/n
    num=sum((ra[i]-ma)*(rb[i]-mb) for i in range(n))
    den=math.sqrt(sum((ra[i]-ma)**2 for i in range(n))*sum((rb[i]-mb)**2 for i in range(n)))
    return num/den if den else 0

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--cities", nargs="*", default=["nyc","chicago"])
    parser.add_argument("--out-metrics", default="/tmp/percentile_metrics.json")
    args=parser.parse_args()
    random.seed(42)

    all_cells=set()
    city_cells={}
    for city in args.cities:
        cells=cells_for_city_broken(city, k_ring=1)
        city_cells[city]=cells
        all_cells.update(cells)
    # national percentile at res9 (method A input)
    scores_all = {}
    for city, cells in city_cells.items():
        scores_all.update(synth_scores(cells, city))
    vals = [scores_all[c] for c in all_cells]
    ranks = _percentile_ranks(vals)
    national_ranks = {c: r for c, r in zip(all_cells, ranks)}

    metrics={}
    for to_res in [7,8]:
        parent_avg_raw = aggregate_avg_raw(all_cells, scores_all, to_res)
        # method A: rank parent avgs nationally
        parent_vals = list(parent_avg_raw.values())
        parent_ranks_A = _percentile_ranks(parent_vals)
        parent_rank_A_map = {p: r for p, r in zip(parent_avg_raw.keys(), parent_ranks_A)}
        # method B: average child percentiles
        parent_rank_B_map = aggregate_avg_percentile(all_cells, scores_all, to_res, national_ranks)
        # align
        common = sorted(set(parent_avg_raw.keys()) & set(parent_rank_B_map.keys()))
        A = [parent_rank_A_map[p] for p in common]
        B = [parent_rank_B_map[p] for p in common]
        rho = spearman(A,B)
        # variance compression check
        var_A = sum((x - sum(A)/len(A))**2 for x in A)/len(A) if A else 0
        var_B = sum((x - sum(B)/len(B))**2 for x in B)/len(B) if B else 0
        metrics[f"res{to_res}"]={
            "parents": len(common),
            "spearman_A_vs_B": round(rho,3),
            "var_A": round(var_A,2),
            "var_B": round(var_B,2),
            "var_compression_B_over_A": round(var_B/var_A,3) if var_A else None,
            "example_A": A[:5],
            "example_B": B[:5],
        }
        print(f"res{to_res}: parents={len(common)} spearman={rho:.3f} var_A={var_A:.1f} var_B={var_B:.1f} compression={var_B/var_A:.3f}" if var_A else "no var")

    with open(args.out_metrics,"w") as f:
        json.dump(metrics,f,indent=2)
    print(f"Wrote {args.out_metrics}")

if __name__=="__main__":
    main()
