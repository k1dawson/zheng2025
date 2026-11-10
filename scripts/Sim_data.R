library(tidyverse)


set.seed(123)



# Parameters from Figure 7
parameters <- tibble(
  condition = c("Pre", "Post-early", "Post-late"),
  n_songs = c(157, 153, 54),
  mean_duration = c(8.37, 6.22, 4.64),
  sem_duration = c(0.20, 0.15, 0.20)
)

# Convert SEM to SD
parameters <- parameters %>%
  mutate(
    sd_duration = sem_duration * sqrt(n_songs)
  )

# Simulate individual song durations
sim_data <- parameters %>%
  uncount(n_songs) %>%
  group_by(condition) %>%
  mutate(
    song_id = row_number(),
    duration = rnorm(
      n(),
      mean = first(mean_duration),
      sd = first(sd_duration)
    )
  ) %>%
  ungroup() %>%
  filter(duration > 0)

head(sim_data)
# Simulate baseline differences between mice
mouse_effects <- tibble(
  mouse = 1:5,
  mouse_effect = rnorm(5, mean = 0, sd = 0.15)
)

sim_data_mice <- sim_data %>%
  mutate(
    mouse = sample(1:5, n(), replace = TRUE)
  ) %>%
  left_join(mouse_effects, by = "mouse") %>%
  mutate(
    duration = duration * exp(mouse_effect)
  )


# Plot simulated song durations ----

sim_data_mice <- sim_data_mice %>%
  mutate(
    condition = factor(
      condition,
      levels = c("Pre", "Post-early", "Post-late")
    )
  )


#violin plot of simulated mouse data (pseudobulked)
ggplot(sim_data_mice,
       aes(x = condition, y = duration, fill = condition)) +
  geom_violin(trim = TRUE, alpha = 0.9) +
  geom_boxplot(
    width = 0.15,
    fill = "grey40",
    color = "grey40",
    alpha = 0.7,
    outlier.shape = NA
  ) +
  scale_fill_manual(values = c(
    "Pre" = "#1f77b4",
    "Post-early" = "#ff7f0e",
    "Post-late" = "#2ca02c"
  )) +
  labs(
    x = NULL,
    y = "Song duration (s)",
    title = "Simulated song durations"
  ) +
  scale_y_continuous(breaks = seq(0, 16, by = 1)) +
  coord_cartesian(ylim = c(0, 16)) +
  theme_classic() +
  theme(
    legend.position = "none",
    axis.text = element_text(size = 12),
    axis.title = element_text(size = 13)
  )

#box plots of individual mice for within-subjects comparisons
ggplot(sim_data_mice,
       aes(x = condition, y = duration, fill = condition)) +
  geom_boxplot() +
  facet_wrap(~ mouse) +
  scale_fill_manual(values = c(
    "Pre" = "#1f77b4",
    "Post-early" = "#ff7f0e",
    "Post-late" = "#2ca02c"
  )) +
  labs(
    x = "Condition",
    y = "Song duration (s)",
    title = "Simulated song durations by mouse"
  ) +
  theme_classic() +
  theme(legend.position = "none")

