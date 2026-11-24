# Next steps: Zheng et al. 2025 reproducibility project

**The project has two parts, and you need both** (Bria: the reproduction can be in Python):

1. **Reproduction.** Rerun the authors' analysis on their data and get Fig 7C. Song duration pre vs post-late, Mann-Whitney p = 1.53e-19.
2. **Simulation.** Your pooled vs per-mouse test simulation (`scripts/dataset_simulations.R`). It's mostly done; it just needs real-data inputs.

You do **not** need to translate the authors' song detection into R. Run their Python and do everything after it in R.

---

## Step 1: Set up Python (≈15 min)

```bash
conda env create -f environment.yml     # if slow: add  --solver=libmamba
conda activate zheng2025
```
The env pins `scikit-learn=1.2.1` because that version fitted the authors' pickled models. A newer sklearn may fail to load them, or load them with a warning.

Download these 3 files from https://github.com/singingmicelab/zheng-harpole-2025-vocalmodes-pag and put them in `original_paper/orig_pipeline/`:
- `segment_features_scaler.pkl`
- `segment_features_pca.pkl`
- `segment_features_gmm.pkl`

(Your notebook run stopped on these: `FileNotFoundError: segment_features_scaler.pkl`.)

## Step 2: Extract songs (≈5 min)

```bash
python scripts/extract_songs.py
```
This is the authors' notebook with only the cells needed for Fig 7C. It writes `data/songs_real.csv`, one row per song.

**✅ Checkpoint:** the printout should show **157 / 153 / 54 songs** (pre / post_early / post_late), a pre mean of ~8.37 s, a post_late mean of ~4.64 s, and p ≈ 1e-19.
If it doesn't, stop here and post the printout in the issue. Don't start the R part on wrong counts.
(We ran it on 2026-11-20 and got exactly 157 / 153 / 54, 8.369 s / 4.643 s, p = 1.53e-19.)

You'll see 8 `MISSING curated file, skipped` lines. That's expected: those hours have no curated features file, and the authors' notebook skips them too.

Look at the songs-per-mouse table it prints. **UM008 contributes 1 post-late song; MZ034 contributes 16.** This is the unequal mouse composition your simulation is about, so put it in the writeup.

Understanding the pipeline (good use of AI). Ask it to walk you through these functions in `events.py`, in order, then write one paragraph for Methods:
1. `compute_window_features`: sliding 7-note windows. A window is kept if its notes are evenly spaced (max log10 ISI ≤ −1, NRMSE ≤ 0.15).
2. `merge_stereotypy_windows`: joins kept windows into segments (gap ≤ 0.5 s / 5 notes).
3. `characterize_segments`: RANSAC line fit of note rate vs note index for each segment.
4. `classify_segments`: the authors' GMM sorts segments into S1/S2/S3. **S1 = song.**
5. `analyze_song_patterning`: song duration = fitted end − fitted start of each S1 segment.

Note: the `type` column in the CSVs is **not** used. It's an uncurated auto-label, and filtering on it is why your earlier durations came out at ~4 s instead of ~8 s.
Also: "post_early" and "post_late" are **not days**. Each post session is split at the hour where half of the male notes have occurred.

## Step 3: Reproduce Fig 7C in R (≈1–2 h)

Fill in the `___` blanks in `scripts/reproduce_fig7c.R`. Each section ends with a CHECK.
Section 4 (songs per mouse × condition) and section 5 (per-mouse test on the real data) connect the reproduction to your simulation. Don't skip them.

## Step 4: Feed real values into the simulation (≈1 h)

Section 6 of `reproduce_fig7c.R` computes `sim_inputs`. In `dataset_simulations.R`, replace:

| currently | replace with |
|---|---|
| `n_songs = c(157, 153, 54)` | `sim_inputs$n_songs` (should be the same, now from data) |
| `log(8)` | `sim_inputs$baseline_log` |
| `log(4.64 / 8.37)` | `sim_inputs$effect_late` |
| `0.09` total variance | `sim_inputs$total_sd_log^2` |
| `rgamma` mouse weights | real per-mouse song shares (`sim_inputs$mouse_weights`) |

Keep your `mouse_sd` × `mouse_cond_sd` × composition grid, but make sure it includes the values you estimated from the real data.

## Step 5: Writeup (`writeup/writeup.qmd`)

- [ ] **Intro / Methods / Measure of success** describe *both* parts. Success: (1) counts match 157/153/54 and p is of the same order as 1.53e-19; (2) simulation shows under which conditions the pooled test's false-positive rate exceeds 5%.
- [ ] Methods: one paragraph on the song pipeline (step 2 above) and a note that it was run in Python.
- [ ] Results order: **reproduction first** (table + Fig 7C side by side with the original + per-mouse table + per-mouse test), then the simulation.
- [ ] Wording: cIPAG → **clPAG**; "calls" → **songs**; "day 1 vs day 5" → **pre vs post-late**.
- [ ] Delete template placeholder text and `writeup/.RDataTmp1` (54 MB; also add it to `.gitignore`).
- [ ] The writeup reads `data/songs_real.csv`; don't rerun Python inside the qmd. Say "run `scripts/extract_songs.py` first" in the README.
- [ ] Tag `v1.0-prereg`, archive on Zenodo, submit on Canvas.

## Priority if short on time

Step 1 → Step 2 checkpoint → Step 3 sections 1–3. That alone is a complete reproduction. Everything after it strengthens the project.
