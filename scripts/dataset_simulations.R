##This script tests the validity of the original authors' statistical approach by generating datasets with different variabilities

# Load Libraries ----
library(tidyverse)
set.seed(123)



# Function for creating song duration datasets with different variation parameters 
# takes effect of treatment, inter-mouse variation, and inter-condition (timepoint) variation per mouse
simulate_songs <- function(effect_silence, mouse_sd, mouse_cond_sd, composition = "redrawn") {
  
  # Sampling weights shared across conditions
  fixed_weights <- rgamma(5, shape = 2)
  
  mice <- c("sMZ034", "sUM008", "sMZ045", "sUM007", "sUM006") #5 mice from orig paper
  
  conditions <- tibble( #generate table of conditions and effect, song n taken from paper
    condition = c("pre_injection", "post_early", "post_late"),
    n_songs = c(157, 153, 54),
    effect = c(0, 0, effect_silence)
  )
  
  if (mouse_sd^2 + mouse_cond_sd^2 > 0.09) { #stops simulation if variable parameters don't make sense
    stop("Mouse SD and mouse-condition SD exceed total variance")
  }
  
  song_sd <- sqrt(0.09 - mouse_sd^2 - mouse_cond_sd^2) #calc song deviation within session for each mouse using mouse variation and cond effect for each mouse
  
  mouse_effects <- tibble( #tibble of mouse effects for each mouse
    mouse_id = mice,
    mouse_effect = rnorm(5, mean = 0, sd = mouse_sd)
  )
  
  mouse_condition_effects <- expand_grid( #calc condition variation for each mouse
    mouse_id = mice,
    condition = conditions$condition
  ) %>%
    mutate(
      mouse_cond_effect = rnorm(n(), 0, mouse_cond_sd)
    )
  
  songs <- conditions %>% #generate song durations with variability
    mutate(
      data = map(n_songs, ~ tibble(
        mouse_id = sample(
          mice,
          size = .x,
          replace = TRUE,
          prob = if (composition == "fixed") {
            fixed_weights
          } else {
            rgamma(5, shape = 2)
          }
        )
      ))
    ) %>%
    unnest(data) %>%
    left_join(mouse_effects, by = "mouse_id") %>%
    left_join(
      mouse_condition_effects,
      by = c("mouse_id", "condition")
    ) %>%
    mutate(
      song_duration = exp(
        log(8) +
          effect +
          mouse_effect +
          mouse_cond_effect +
          rnorm(n(), 0, song_sd)
      )
    ) %>%
    select(mouse_id, condition, song_duration)
  
  return(songs)
}


#Function that runs tests on pooled data and individual mice (compare author vs my method)
analyze_songs <- function(d) {
  
  # Keep only pre and post-late songs
  d <- d %>%
    filter(condition %in% c("pre_injection", "post_late"))
  
  # Test 1: pooled Mann-Whitney
  pooled_p <- wilcox.test(
    song_duration ~ condition,
    data = d,
    exact = FALSE
  )$p.value
  
  # Calculate mean log duration for each mouse
  mouse_means <- d %>%
    group_by(mouse_id, condition) %>%
    summarise(
      mean_log_duration = mean(log(song_duration)),
      .groups = "drop"
    ) %>%
    pivot_wider(
      names_from = condition,
      values_from = mean_log_duration
    )
  
  if (anyNA(mouse_means$pre_injection) ||
      anyNA(mouse_means$post_late) ||
      nrow(mouse_means) != 5) {
    stop("Missing mouse-condition observations")
  }
  
  # Test 2: paired t-test using mouse means
  mouse_p <- t.test(
    mouse_means$pre_injection,
    mouse_means$post_late,
    paired = TRUE
  )$p.value
  
  tibble(
    pooled_p = pooled_p,
    mouse_p = mouse_p
  )
}


# Test that both functions work in creating a dummy dataset ----
sim1 <- simulate_songs(0, 0.1, 0.1)
sim1 |> count(mouse_id, condition)
analyze_songs(sim1)

# Generate 500 datasets where there is no treatment effect (of ciPAG silencing), outputs 2 test results per dataset ----
null_results <- map_dfr(1:500, function(i) {
  
  d <- simulate_songs(
    effect_silence = 0,
    mouse_sd = 0.1,
    mouse_cond_sd = 0.1
  )
  
  analyze_songs(d)
})

null_results %>%
  summarise(
    pooled_FPR = mean(pooled_p < 0.05),
    mouse_FPR = mean(mouse_p < 0.05)
  )

# Generate simulated results with different input values for levels of variation to test when authors' test is invalid ----
settings <- crossing(
  mouse_sd = c(0, 0.1, 0.2, 0.28),
  mouse_cond_sd = c(0, 0.05, 0.1, 0.2),
  composition = c("fixed", "redrawn"),
  effect_silence = c(0, log(0.85))
) %>%
  filter(mouse_sd^2 + mouse_cond_sd^2 <= 0.09)
  

set.seed(123)

results <- pmap_dfr(
  settings,
  function(mouse_sd, mouse_cond_sd,
           composition, effect_silence) {
    
    map_dfr(1:500, function(i) {
      
      d <- simulate_songs(
        effect_silence = effect_silence,
        mouse_sd = mouse_sd,
        mouse_cond_sd = mouse_cond_sd,
        composition = composition
      )
      
      analyze_songs(d) %>%
        mutate(
          simulation = i,
          mouse_sd = mouse_sd,
          mouse_cond_sd = mouse_cond_sd,
          composition = composition,
          effect_silence = effect_silence
        )
    })
  }
)

write_csv(results, "simulation_results_revised.csv")

#write_csv(results, "simulation_results.csv")

# Summarize results of simulated dataset analysis ----
summary_results <- results %>%
  mutate(
    scenario = if_else(
      effect_silence == 0,
      "Null: false positive rate",
      "Effect: rejection rate"
    )
  ) %>%
  group_by(
    scenario,
    mouse_sd,
    mouse_cond_sd,
    composition
  ) %>%
  summarise(
    pooled_rate = mean(pooled_p < 0.05, na.rm = TRUE),
    mouse_rate = mean(mouse_p < 0.05, na.rm = TRUE),
    .groups = "drop"
  )

summary_results


# Plot ----
summary_results %>%
  filter(scenario == "Null: false positive rate") %>%
  pivot_longer(
    cols = c(pooled_rate, mouse_rate),
    names_to = "test",
    values_to = "false_positive_rate"
  ) %>%
  ggplot(aes(
    x = mouse_cond_sd,
    y = false_positive_rate,
    color = test
  )) +
  geom_line() +
  geom_point(size = 2) +
  geom_hline(
    yintercept = 0.05,
    linetype = "dashed"
  ) +
  facet_grid(
    composition ~ mouse_sd,
    labeller = label_both
  ) +
  labs(
    x = "Mouse-condition SD (log scale)",
    y = "False positive rate",
    color = "Statistical test"
  ) +
  theme_classic()

# Plot for isolating composition effect ----
summary_results %>%
  filter(
    scenario == "Null: false positive rate",
    mouse_cond_sd == 0
  ) %>%
  pivot_longer(
    cols = c(pooled_rate, mouse_rate),
    names_to = "test",
    values_to = "false_positive_rate"
  ) %>%
  ggplot(aes(
    x = mouse_sd,
    y = false_positive_rate,
    color = test,
    linetype = composition,
    group = interaction(test, composition)
  )) +
  geom_line() +
  geom_point(size = 3) +
  geom_hline(
    yintercept = 0.05,
    linetype = "dashed",
    color = "grey50"
  ) +
  labs(
    x = "Between-mouse SD (log scale)",
    y = "False positive rate",
    color = "Statistical test",
    linetype = "Mouse composition"
  ) +
  theme_classic()

