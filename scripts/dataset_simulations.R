##This script tests the validity of the original authors' statistical approach by generating datasets with different variabilities

# Load Libraries ----
library(tidyverse)
library(assertthat)
library(here)
set.seed(123)

sim_inputs <- readRDS( #read in the weights for each mouse from the real study, convert into form legible for simulate_songs
  here("data/sim_inputs.rds")
)

n_songs = desc$n[
  match(
    c("pre", "post_early", "post_late"),
    as.character(desc$full_condition)
  )
]
empirical_weights <- sim_inputs$mouse_weights |>
  mutate(
    condition = recode(
      as.character(full_condition),
      "pre" = "pre_injection"
    ),
    mouse_id = paste0("s", mouse_id)
  ) |>
  select(condition, mouse_id, weight)

# Function for creating song duration datasets with different variation parameters 
# takes effect of treatment, inter-mouse variation, and inter-condition (timepoint) variation per mouse
simulate_songs <- function(
    effect_silence,
    mouse_sd,
    mouse_cond_sd,
    composition = "observed",
    sim_inputs
) {
  
  # Sampling weights shared across conditions
  fixed_weights <- rgamma(5, shape = 2)
  
  mice <- c("sMZ034", "sUM008", "sMZ045", "sUM007", "sUM006") #5 mice from orig paper
  
  conditions <- tibble( #generate table of conditions and effect, song n taken from paper
    condition = c("pre_injection", "post_early", "post_late"),
    n_songs = sim_inputs$n_songs,
    effect = c(0, 0, effect_silence)
  )
  
  if (mouse_sd^2 + mouse_cond_sd^2 > sim_inputs$total_sd_log^2) {
    stop("Mouse SD and mouse-condition SD exceed total variance")
  }
  
  song_sd <- sqrt(
    sim_inputs$total_sd_log^2 -
      mouse_sd^2 -
      mouse_cond_sd^2
  ) #calc song deviation within session for each mouse using mouse variation and cond effect for each mouse
  
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
  
  songs <- conditions %>%
    mutate(
      data = map2(condition, n_songs, function(cond, n) {
        
        if (composition == "observed") {
          
          weights <- sim_inputs$mouse_weights %>%
            mutate(
              condition = recode(
                as.character(full_condition),
                "pre" = "pre_injection"
              ),
              mouse_id = paste0("s", mouse_id)
            ) %>%
            filter(condition == cond) %>%
            slice(match(mice, mouse_id)) %>%
            pull(weight)
          
        } else if (composition == "fixed") {
          
          weights <- fixed_weights
          
        } else if (composition == "redrawn") {
          
          weights <- rgamma(5, shape = 2)
          
        } else {
          stop("Unknown composition")
        }
        
        stopifnot(
          length(weights) == length(mice),
          all(is.finite(weights)),
          all(weights >= 0),
          sum(weights) > 0
        )
        
        tibble(
          mouse_id = c(
            mice,
            sample(
              mice,
              size = n - length(mice),
              replace = TRUE,
              prob = weights
            )
          )
        )
      })
    ) %>%
    unnest(data) %>%
    left_join(mouse_effects, by = "mouse_id") %>%
    left_join(
      mouse_condition_effects,
      by = c("mouse_id", "condition")
    ) %>%
    mutate(
      song_duration = exp(
        sim_inputs$baseline_log +
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
sim1 <- simulate_songs(
  effect_silence = 0,
  mouse_sd = 0.1,
  mouse_cond_sd = 0.1,
  composition = "observed",
  sim_inputs = sim_inputs
)

sim1 %>%
  count(condition, mouse_id) %>%
  group_by(condition) %>%
  mutate(weight = n / sum(n)) %>%
  ungroup()

analyze_songs(sim1)

# Generate 500 datasets where there is no treatment effect (of ciPAG silencing), outputs 2 test results per dataset ----
null_results <- map_dfr(1:10, function(i) {
  
  d <- simulate_songs(
    effect_silence = 0,
    mouse_sd = 0.1,
    mouse_cond_sd = 0.1,
    composition = "observed",
    sim_inputs = sim_inputs
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
  composition = c("observed", "fixed", "redrawn"),
  effect_silence = c(
    0,
    log(0.85),
    sim_inputs$effect_late
  )
) %>%
  filter(
    mouse_sd^2 + mouse_cond_sd^2 <= sim_inputs$total_sd_log^2
  ) 
  

set.seed(123)

results <- pmap_dfr(
  settings,
  function(mouse_sd, mouse_cond_sd,
           composition, effect_silence) {
    
    map_dfr(1:10, function(i) {
      
      d <- simulate_songs(
        effect_silence = effect_silence,
        mouse_sd = mouse_sd,
        mouse_cond_sd = mouse_cond_sd,
        composition = composition,
        sim_inputs = sim_inputs
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


write_csv(results, file = here("data/simulation_results.csv"))

# Summarize results of simulated dataset analysis ----
summary_results <- results %>%
  mutate(
    scenario = case_when(
      effect_silence == 0 ~ "Null: false positive rate",
      effect_silence == log(0.85) ~ "15% reduction",
      TRUE ~ "Observed reduction (44.6%)"
    )
  ) %>%
  group_by(
    scenario,
    effect_silence,
    mouse_sd,
    mouse_cond_sd,
    composition
  ) %>%
  summarise(
    pooled_rate = mean(pooled_p < 0.05),
    mouse_rate = mean(mouse_p < 0.05),
    n_simulations = n(),
    .groups = "drop"
  )

write_csv(summary_results, file = here("data/simulation_results_summary.csv"))

# Assert that both tests produce valid false positive results ----
assert_that(
  all(summary_results$pooled_rate >= 0 &
        summary_results$pooled_rate <= 1),
  all(summary_results$mouse_rate >= 0 &
        summary_results$mouse_rate <= 1)
)

# Plot False Positive ----
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








# worst figures ever ----
plot_data <- results %>%
  filter(effect_silence == 0) %>%
  mutate(
    total_variation = sqrt(mouse_sd^2 + mouse_cond_sd^2)
  ) %>%
  pivot_longer(
    cols = c(pooled_p, mouse_p),
    names_to = "test",
    values_to = "p_value"
  )

ggplot(plot_data, aes(
  x = total_variation,
  y = p_value,
  color = test
)) +
  geom_jitter(
    width = 0.003,
    height = 0,
    alpha = 0.25,
    size = 1
  ) +
  geom_hline(
    yintercept = 0.05,
    linetype = "dashed"
  ) +
  scale_color_manual(
    values = c(
      "pooled_p" = "#E69F00",
      "mouse_p" = "#0072B2"
    ),
    labels = c(
      "pooled_p" = "Pooled Mann-Whitney",
      "mouse_p" = "Mouse-level paired t-test"
    )
  ) +
  labs(
    title = "Distribution of P-values Under the Null Hypothesis",
    x = "Combined between-mouse and condition variation",
    y = "P-value",
    color = "Statistical test"
  ) +
  theme_classic()


results %>%
  filter(effect_silence == 0) %>%
  pivot_longer(
    cols = c(pooled_p, mouse_p),
    names_to = "test",
    values_to = "p_value"
  ) %>%
  ggplot(aes(
    x = -log10(pmax(p_value, .Machine$double.xmin)),
    y = mouse_sd,
    color = test
  )) +
  geom_jitter(width = 0.002, alpha = 0.3) +
  geom_hline(
    yintercept = -log10(0.05),
    linetype = "dashed"
  ) +
  labs(
    x = "Total variance",
    y = "-log10(p-value)",
    color = "Statistical test",
    title = "Statistical Significance Across Simulated Variability"
  ) +
  theme_classic()
