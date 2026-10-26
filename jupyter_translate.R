#Trying to recreate the pag.telc analysis from the paper in R instead of Jupyter Notebook, using the same exact data from the paper

library(tidyverse)


# load the sessions.csv and session_curation.csv ----
sessions_info <- read_csv(file.choose())
sessions_curated_hours_info <- read_csv(file.choose())



# change basepath entries ----
data_dir <- dirname(file.choose())
sessions_info <- sessions_info %>%
  mutate(
    basepath = file.path(data_dir, session)
  )

sessions_curated_hours_info <- sessions_curated_hours_info %>%
  mutate(
    basepath = file.path(data_dir, session)
  )


# save corrected files as new csvs ----
write_csv(
  sessions_info,
  file.path(data_dir, "pag_telc_sessions_updated.csv")
)

write_csv(
  sessions_curated_hours_info,
  file.path(data_dir, "pag_telc_curation_updated.csv")
)

# ----
#look at one session file from the data (all_notes_corrected_features)
notes <- read_csv(file.choose())

glimpse(notes)
names(notes)
head(notes)

# load_notes function for gathering data from all sessions and combining with metadata ----
load_notes <- function(folder, session_id, file_idx,
                       mouse_1, mouse_2,
                       curated = FALSE) {
  
  filenames <- filenames <- c(
    "all_notes_corrected_features.csv",
    "all_notes_corrected.csv",
    "all_notes.csv"
  )
  
  paths <- file.path(folder, filenames)
  existing <- paths[file.exists(paths)]
  
  if (length(existing) == 0) {
    warning("Missing acoustic file: ", folder)
    return(NULL)
  }
  
  filepath <- existing[1]
  
  notes <- read_csv(filepath, show_col_types = FALSE)
  
  # Drop saved CSV index column, if present
  if (names(notes)[1] %in% c("...1", "X", "Unnamed: 0")) {
    notes <- notes[, -1]
  }
  
  # Match Python's drop_duplicates(keep = "last")
  notes <- notes %>%
    mutate(.row_id = row_number()) %>%
    group_by(start, end) %>%
    slice_max(.row_id, n = 1, with_ties = FALSE) %>%
    ungroup() %>%
    select(-.row_id) %>%
    arrange(start, end) %>%
    mutate(
      session_id = as.character(session_id),
      file_idx = as.character(file_idx)
    )
  
  left_notes <- notes %>%
    filter(code == 0) %>%
    mutate(
      mouse_id = as.character(mouse_1),
      mouse_side = "mouse_1"
    )
  
  right_notes <- notes %>%
    filter(code == 1) %>%
    mutate(
      mouse_id = as.character(mouse_2),
      mouse_side = "mouse_2"
    )
  
  list(
    all_notes = notes,
    left_notes = left_notes,
    right_notes = right_notes,
    filepath = filepath
  )
}

# create all_sessions list of all data in pag.telc ----
all_sessions <- list()

for (i in seq_len(nrow(sessions_info))) {
  
  info <- sessions_info[i, ]
  
  session_id <- as.character(info$session)
  condition <- as.character(info$condition)
  mouse_1 <- info$mouse_1
  mouse_2 <- info$mouse_2
  
  # Use your corrected session path
  session_basepath <- as.character(info$basepath)
  
  cat("Processing session:", session_id, "\n")
  
  # Choose the correct acoustic data folder
  audio_dir <- if (condition == "pre") {
    "process_audio"
  } else {
    "original_audio"
  }
  
  notes_dir <- file.path(
    session_basepath,
    audio_dir,
    "all_notes"
  )
  
  if (!dir.exists(notes_dir)) {
    warning("Directory not found: ", notes_dir)
    next
  }
  
  # Identify all recording folders
  file_indices <- sort(
    list.dirs(
      notes_dir,
      recursive = FALSE,
      full.names = FALSE
    )
  )
  
  # Find curated recordings for this session
  curated_indices <- sessions_curated_hours_info %>%
    filter(session == session_id) %>%
    pull(hr) %>%
    as.integer()
  
  cat("Number of recording files:",
      length(file_indices), "\n")
  
  cat("Number of curated files:",
      length(curated_indices), "\n")
  
  # Load all recording files
  hours <- map(
    file_indices,
    function(file_idx) {
      load_notes(
        folder = file.path(notes_dir, file_idx),
        session_id = session_id,
        file_idx = file_idx,
        mouse_1 = mouse_1,
        mouse_2 = mouse_2
      )
    }
  )
  
  # Load curated recording files
  curated_hours <- map(
    curated_indices,
    function(file_idx) {
      load_notes(
        folder = file.path(
          notes_dir,
          sprintf("%07d", file_idx)
        ),
        session_id = session_id,
        file_idx = file_idx,
        mouse_1 = mouse_1,
        mouse_2 = mouse_2,
        curated = TRUE
      )
    }
  )
  
  # Keep successfully loaded files
  hours <- compact(hours)
  curated_hours <- compact(curated_hours)
  
  # Create recording-level metadata
  hours_info <- imap_dfr(
    hours,
    function(h, j) {
      tibble(
        i_file = match(
          h$all_notes$file_idx[1],
          file_indices
        ) - 1L,
        file_idx = h$all_notes$file_idx[1],
        all_notes_filepath = h$filepath,
        l_num_notes = nrow(h$left_notes),
        r_num_notes = nrow(h$right_notes)
      )
    }
  )
  
# create tibble from all_sessions ----  
  curated_hours_info <- map_dfr(
    curated_hours,
    function(h) {
      idx <- h$all_notes$file_idx[1]
      
      tibble(
        i_file = match(
          as.integer(idx),
          as.integer(file_indices)
        ) - 1L,
        file_idx = idx,
        all_notes_filepath = h$filepath,
        l_num_notes = nrow(h$left_notes),
        r_num_notes = nrow(h$right_notes)
      )
    }
  )
  
  # Store the session
  session <- list(
    session_id = session_id,
    project_dir = session_basepath,
    session_basepath = session_basepath,
    condition = condition,
    anchor_file_idx = info$anchor_file_idx,
    num_post_days = info$num_post_days,
    num_vocal_days = info$num_vocal_days,
    mouse_1 = mouse_1,
    mouse_2 = mouse_2,
    num_files = length(file_indices),
    num_curated_files = length(curated_indices),
    
    hours_info = hours_info,
    hours_all_notes = map(hours, "all_notes"),
    hours_l_notes = map(hours, "left_notes"),
    hours_r_notes = map(hours, "right_notes"),
    
    curated_hours_info = curated_hours_info,
    curated_hours_all_notes =
      map(curated_hours, "all_notes"),
    curated_hours_l_notes =
      map(curated_hours, "left_notes"),
    curated_hours_r_notes =
      map(curated_hours, "right_notes")
  )
  
  all_sessions[[length(all_sessions) + 1]] <- session
}

# Cell 14: Combine curated acoustic recordings ----

curated_notes <- purrr::map_dfr(
  all_sessions,
  function(s) {
    
    purrr::map_dfr(
      s$curated_hours_all_notes,
      function(notes) {
        
        # Skip empty recordings
        if (nrow(notes) == 0) {
          return(NULL)
        }
        
        notes %>%
          mutate(
            # Standardize column types
            type = as.character(type),
            across(
              any_of(c(
                "start", "end", "duration",
                "maxfreq", "min", "code"
              )),
              as.numeric
            ),
            
            # Add session metadata
            session = s$session_id,
            condition = s$condition,
            mouse_1 = as.character(s$mouse_1),
            mouse_2 = as.character(s$mouse_2),
            
            # Assign notes to mice
            mouse_id = case_when(
              code == 0 ~ mouse_1,
              code == 1 ~ mouse_2,
              TRUE ~ NA_character_
            )
          )
      }
    )
  }
)

# Cell 15: Check unassigned vocalizations and filter notes for male vocalizations ----

curated_notes %>%
  filter(is.na(mouse_id)) %>%
  count(session, code)
male_notes_all <- curated_notes |>
  filter(code == 0) |>
  distinct(session_id, file_idx, start, end, .keep_all = TRUE) |>
  arrange(session_id, file_idx, start, end)
#filter for only male songs (those receiving treatment)
#male_notes <- curated_notes %>%
  #filter(mouse_id == mouse_1 & type == 'song')

# make male event features tibble ----
male_event_features <- male_notes_all |>
  group_by(mouse_id, session_id, file_idx) |>
  arrange(start, end, .by_group = TRUE) |>
  mutate(
    duration = end - start,
    inter_event_interval = lead(start) - end,
    inter_start_interval = lead(start) - start,
    inst_rate = if_else(
      inter_start_interval > 0,
      1 / inter_start_interval,
      NA_real_
    ),
    log_inter_event_interval =
      log10(if_else(
        inter_event_interval > 0,
        inter_event_interval,
        NA_real_
      ))
  ) |>
  ungroup()

# define windows for organizing vocalization bouts ----
window_features <- function(df) {
  if (nrow(df) < 7L) return(tibble::tibble())
  
  dplyr::bind_rows(lapply(seq_len(nrow(df) - 6L), function(i) {
    idx <- i:(i + 5L)
    rates <- df$inst_rate[idx]
    
    if (any(!is.finite(rates))) return(NULL)
    
    x <- 0:5
    fit <- lm(rates ~ x)
    
    gaps <- df$log_inter_event_interval[idx]
    max_gap <- if (all(is.na(gaps))) NA_real_ else max(gaps, na.rm = TRUE)
    
    tibble::tibble(
      start = df$start[i],
      end = df$end[i + 6L],
      start_index = i,
      end_index = i + 6L,
      max_log_interval = max_gap,
      slope = unname(coef(fit)[2]),
      intercept = unname(coef(fit)[1]),
      normalized_rmse =
        sqrt(mean(residuals(fit)^2)) / mean(rates)
    )
  }))
}

male_windows <- male_event_features |>
  group_by(mouse_id, session_id, file_idx) |>
  group_modify(~ window_features(.x)) |>
  ungroup() |>
  mutate(
    qualifies = coalesce(
      max_log_interval <= -1 & normalized_rmse <= 0.15,
      FALSE
    )
  )

# Cell 16: Explore vocalization durations ----

male_duration_summary <- male_notes %>%
  filter(!is.na(mouse_id), !is.na(duration)) %>%
  group_by(mouse_id, condition) %>%
  summarise(
    n_notes = n(),
    mean_duration = mean(duration),
    median_duration = median(duration),
    .groups = "drop"
  )

View(male_duration_summary)

# Plot of mean note duration for male songs ----
ggplot(male_duration_summary,
       aes(x = condition, y = mean_duration,
           group = mouse_id)) +
  geom_line(alpha = 0.5) +
  geom_point(size = 2) +
  theme_classic() +
  labs(
    x = "Treatment condition",
    y = "Mean note duration (seconds)",
    title = "Vocalization duration before and after TeLC"
  )

# calculate male song bouts ----
male_song_notes <- male_notes |>
  filter(type == "song") |>
  group_by(mouse_id, session_id, file_idx) |>
  arrange(start, end, .by_group = TRUE) |>
  mutate(
    # Running maximum also handles overlapping notes.
    previous_end = lag(cummax(end)),
    new_song = is.na(previous_end) |
      start - previous_end > 0.1,
    song_id = cumsum(new_song)
  ) |>
  ungroup()

male_songs <- male_song_notes |>
  group_by(mouse_id, session_id, file_idx, condition, song_id) |>
  summarise(
    song_start = min(start),
    song_end = max(end),
    song_duration = song_end - song_start,
    num_notes = n(),
    .groups = "drop"
  )
mouse_means <- male_songs |>
  mutate(condition = factor(condition, levels = c("pre", "post"))) |>
  group_by(mouse_id, condition) |>
  summarise(
    mean_duration = mean(song_duration, na.rm = TRUE),
    n_songs = n(),
    .groups = "drop"
  )

ggplot(mouse_means,
       aes(x = condition, y = mean_duration,
           group = mouse_id, color = factor(mouse_id))) +
  geom_line(linewidth = 0.7) +
  geom_point(size = 3) +
  labs(
    x = "Condition",
    y = "Mean song duration (s)",
    color = "Mouse"
  ) +
  theme_classic()
male_songs |>
  group_by(condition) |>
  summarise(
    n_bouts = n(),
    mean_duration = mean(song_duration, na.rm = TRUE),
    median_duration = median(song_duration, na.rm = TRUE),
    median_notes = median(num_notes),
    fraction_single_note = mean(num_notes == 1),
    .groups = "drop"
  )
