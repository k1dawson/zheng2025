"""
extract_songs.py: Part 1 of the project (reproduction), Python half.

Runs the authors' song-detection pipeline (Zheng et al. 2025, pag_telc.ipynb)
on the TeLC data in this repo and writes one row per song to
data/songs_real.csv. Everything after that (Fig 7C, stats, simulation)
happens in R.

This is a stripped-down copy of notebook cells 7, 10, 11, 13, 21, 22, 38 and 40,
with plotting removed and paths made relative. The analysis logic is unchanged.

Run from the repo root:
    conda activate zheng2025
    python scripts/extract_songs.py

Expected output (paper, Fig 7C): 157 / 153 / 54 songs (pre / post_early / post_late)
with mean durations of about 8.37 s (pre) and 4.64 s (post_late).
"""

import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

# ---- paths (relative to the repo root, so this runs on anyone's machine) ----
REPO = Path(__file__).resolve().parents[1]
CODE_DIR = REPO / "original_paper" / "orig_pipeline"   # events.py, utils.py, *.pkl
DATA_DIR = REPO / "original_paper" / "telc_data" / "pag_telc"
OUT_CSV = REPO / "data" / "songs_real.csv"

sys.path.insert(0, str(CODE_DIR))
from events import (  # noqa: E402  (authors' code, unchanged)
    compute_event_features,
    compute_window_features,
    merge_stereotypy_windows,
    characterize_segments,
    classify_segments,
    classify_notes_by_temporal_patterning,
    analyze_song_patterning,
)

# ---- parameters: copied verbatim from notebook cell 7 ----
min_window_size = 7
window_max_log_isi_threshold = -1
window_rmse_threshold = 0.15
segment_max_time_gap = 0.5
segment_max_index_gap = 5
cluster_mapping = {0: "S2", 1: "S3", 2: "S1"}
final_type_mapping = {"S1": "song", "S2": "proto-song", "S3": "USV", "U": "USV"}
song_final_note_occupancy = 0.5

# Authors' fitted models (from their GitHub repo). Need scikit-learn 1.2.1.
models = {}
for name in ["scaler", "pca", "gmm"]:
    with open(CODE_DIR / f"segment_features_{name}.pkl", "rb") as f:
        models[name] = pickle.load(f)

# ---- metadata (cells 10-11) ----
sessions_info = pd.read_csv(DATA_DIR / "pag_telc_sessions.csv")
sessions_info = sessions_info[sessions_info["condition"].isin(["pre", "post"])].reset_index(drop=True)
curation = pd.read_csv(DATA_DIR / "pag_telc_curation.csv")


def load_hour(session_id, condition, file_idx):
    """Load one curated hour and return the male (code == 0) notes (cell 13)."""
    audio_dir = "process_audio" if condition == "pre" else "original_audio"
    fp = DATA_DIR / session_id / audio_dir / "all_notes" / f"{file_idx:07d}" / "all_notes_corrected_features.csv"
    if not fp.exists():
        print(f"  MISSING curated file, skipped: {fp.relative_to(REPO)}")
        return None
    notes = pd.read_csv(fp, header=0, index_col=0)
    notes = notes.drop_duplicates(subset=["start", "end"], keep="last")
    notes = notes.sort_values(by=["start", "end"]).reset_index(drop=True)
    return notes[notes["code"] == 0].copy().reset_index(drop=True)


def songs_in_hour(l_notes):
    """Notebook cell 21: notes -> windows -> segments -> S1 segments -> songs."""
    df_events = compute_event_features(l_notes)
    df_windows = compute_window_features(df_events, min_window_size=min_window_size)
    _, df_segments = merge_stereotypy_windows(
        df_windows, df_events,
        max_log_interval_threshold=window_max_log_isi_threshold,
        rmse_threshold=window_rmse_threshold,
        max_gap=segment_max_time_gap,
        max_index_gap=segment_max_index_gap,
    )
    df_segments = characterize_segments(
        df_events, df_segments,
        ransac_min_samples=min_window_size,
        ransac_normalized_residual_threshold=window_rmse_threshold,
    )
    df_segments = classify_segments(df_segments, models["scaler"], models["pca"], models["gmm"],
                                    cluster_mapping=cluster_mapping)
    df_events = classify_notes_by_temporal_patterning(df_segments, df_events)
    df_events["type_final"] = df_events["type_patterning"].map(final_type_mapping)
    if df_segments.empty:
        return pd.DataFrame()
    s1 = df_segments[df_segments["cluster_label"] == "S1"]
    return analyze_song_patterning(s1, df_events, song_final_note_occupancy=song_final_note_occupancy)


# ---- main loop ----
all_songs = []
for _, s in sessions_info.iterrows():
    session_id, condition, mouse = s["session"], s["condition"], s["mouse_1"]
    hours = curation.loc[curation["session"] == session_id, "hr"].tolist()  # curated hours, file order
    print(f"{session_id} ({mouse}, {condition}): {len(hours)} curated hours")

    hour_rows = []
    for hr in hours:
        l_notes = load_hour(session_id, condition, hr)
        if l_notes is None:
            continue
        songs = songs_in_hour(l_notes)
        songs = songs.assign(mouse_id=mouse, condition=condition, session_id=session_id, file_idx=hr)
        hour_rows.append({"file_idx": hr, "l_num_notes": len(l_notes), "songs": songs})

    # cell 22: split post sessions into early/late at the halfway point of male notes.
    # The hour that crosses the halfway point counts as "early".
    if condition == "post":
        cs = np.cumsum([h["l_num_notes"] for h in hour_rows])
        crossing = int(np.argmax(cs >= cs[-1] / 2))
        for i, h in enumerate(hour_rows):
            h["songs"]["full_condition"] = "post_early" if i <= crossing else "post_late"
    else:
        for h in hour_rows:
            h["songs"]["full_condition"] = "pre"

    all_songs += [h["songs"] for h in hour_rows if len(h["songs"])]

songs = pd.concat(all_songs, ignore_index=True)
OUT_CSV.parent.mkdir(exist_ok=True)
songs.to_csv(OUT_CSV, index=False)
print(f"\nWrote {len(songs)} songs to {OUT_CSV.relative_to(REPO)}")

# ---- check against the paper (cell 40 + the Fig 7C test) ----
order = ["pre", "post_early", "post_late"]
print("\nSong duration by condition (paper: n = 157 / 153 / 54; mean pre 8.37 s, post_late 4.64 s)")
print(songs.groupby("full_condition")["duration"].agg(["count", "mean", "sem"]).reindex(order).round(3))
print("\nSongs per mouse x condition (who contributes to each condition?)")
print(pd.crosstab(songs["mouse_id"], songs["full_condition"])[order])

pre = songs.loc[songs["full_condition"] == "pre", "duration"]
late = songs.loc[songs["full_condition"] == "post_late", "duration"]
res = mannwhitneyu(pre, late, alternative="two-sided")
print(f"\nMann-Whitney U pre vs post_late: U = {res.statistic:.0f}, p = {res.pvalue:.3g}  (paper: p = 1.53e-19)")
