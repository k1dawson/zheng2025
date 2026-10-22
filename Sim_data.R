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
