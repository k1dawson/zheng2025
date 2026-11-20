# reproduce_fig7c.R: Part 1 of the project (reproduction), R half.
#
# Input:  data/songs_real.csv  (made by scripts/extract_songs.py; run that first)
# Output: the Fig 7C reproduction (plot + Mann-Whitney) and real-data values
#         to plug into the simulation (Part 2).
#
# Fill in every TODO. Each section ends with a CHECK so you know you're on track.

library(tidyverse)
library(here)

songs <- read_csv(here("data/songs_real.csv")) |>
  mutate(full_condition = factor(full_condition,
                                 levels = c("pre", "post_early", "post_late")))

# 1. Descriptives ---------------------------------------------------------------
# TODO: count songs and get mean / SEM of `duration` for each full_condition.
desc <- songs |>
  group_by(full_condition) |>
  summarise(n = ___, mean_dur = ___, sem_dur = ___)
desc
# CHECK: n = 157 / 153 / 54 and mean pre ~ 8.37 s, post_late ~ 4.64 s.
#        If the counts are off, stop and fix the Python step first.

# 2. Key test (the paper's analysis) --------------------------------------------
# TODO: two-sided Mann-Whitney (wilcox.test) of duration, pre vs post_late only.
#       Use exact = FALSE (there are ties/large n, and it matches scipy's default).
key_test <- songs |>
  filter(full_condition %in% c(___, ___)) |>
  wilcox.test(duration ~ full_condition, data = _, exact = FALSE)
key_test
# CHECK: p should be on the order of 1e-19 (paper: 1.53e-19).
#        Also run pre vs post_early and post_early vs post_late for completeness.

# 3. Fig 7C, side by side with the original -------------------------------------
# TODO: violin (or box + jitter) of duration by full_condition, y limits 0-16 s,
#       same colors as the paper (pre = blue, post_early = orange, post_late = green).
fig7c <- ggplot(songs, aes(x = full_condition, y = duration, fill = full_condition)) +
  ___ +
  labs(x = NULL, y = "Song duration (s)") +
  theme_classic()
ggsave(here("images/fig7c_reproduced.png"), fig7c, width = 3, height = 3)
# In writeup.qmd, show images/figure7c.png (original) next to this one.

# 4. Where do the songs come from? (key input to the simulation) ----------------
# TODO: count songs per mouse x full_condition. Are all 5 mice in post_late?
per_mouse <- songs |> count(mouse_id, full_condition) |>
  pivot_wider(names_from = full_condition, values_from = n, values_fill = 0)
per_mouse
# Write 2-3 sentences in the writeup about what this table implies for a pooled
# Mann-Whitney that treats every song as independent.

# 5. Per-mouse analysis on the REAL data ----------------------------------------
# Same test as analyze_songs() in dataset_simulations.R: mean log duration per
# mouse, then a paired t-test pre vs post_late (n = number of mice with both).
# TODO: compute mouse_means and run the paired test. Drop mice missing post_late
#       and SAY SO in the writeup. Note: UM008 has only 1 post-late song, so its
#       "mean" is a single value. Mention this, and consider a mixed model as a
#       robustness check: lme4::lmer(log(duration) ~ full_condition + (1 | mouse_id))
mouse_means <- songs |>
  filter(full_condition %in% c("pre", "post_late")) |>
  group_by(mouse_id, full_condition) |>
  summarise(mean_log_dur = mean(log(duration)), .groups = "drop") |>
  pivot_wider(names_from = full_condition, values_from = mean_log_dur) |>
  drop_na()
# t.test(___, ___, paired = TRUE)

# 6. Generating values for the simulation (Part 2) ------------------------------
# Replace the guessed values in simulate_songs() with these:
sim_inputs <- list(
  n_songs        = desc$n,                                   # replaces c(157, 153, 54)
  baseline_log   = mean(log(songs$duration[songs$full_condition == "pre"])),  # replaces log(8)
  effect_late    = ___,  # TODO: mean log(post_late) - mean log(pre)  (paper ratio: log(4.64/8.37))
  total_sd_log   = ___,  # TODO: SD of log(duration) within pre; replaces sqrt(0.09) = 0.3
  mouse_sd       = ___,  # TODO: SD of per-mouse mean log duration in pre
  mouse_weights  = ___   # TODO: per-mouse share of songs in each condition (from per_mouse)
)
sim_inputs
# Then in dataset_simulations.R, center your parameter grid on these values.
