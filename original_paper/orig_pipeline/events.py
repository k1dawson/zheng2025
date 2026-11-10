"""
    Temporal patterning analysis of events

"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, RANSACRegressor
from sklearn.metrics import mean_squared_error
import matplotlib.pyplot as plt
from scipy.stats import linregress  


def compute_event_features(df):
    """
    Compute per-event temporal features for behavioral events in a DataFrame.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing at least 'start' and 'end' columns representing event timings.

    Returns:
    --------
    pandas.DataFrame
        DataFrame augmented with the following per-event temporal features:
            - duration: Duration of each event (end - start)
            - inter_event_interval: Time between the end of the current event and the start of the next event
            - log_inter_event_interval: Log10 of the inter-event interval
            - inter_start_interval: Time between the start of the current event and the start of the next event
            - inst_rate: Instantaneous rate (1 / inter_start_interval)
    """
    df = df.copy()
    
    # Ensure that 'start' and 'end' columns exist
    if not {'start', 'end'}.issubset(df.columns):
        raise ValueError("Input DataFrame must contain 'start' and 'end' columns.")
    
    # Sort the DataFrame by 'start' time to ensure chronological order
    df = df.sort_values(by='start').reset_index(drop=True)
    
    ### Per-Event Temporal Features ###
    
    # 1. Compute event duration
    df['duration'] = df['end'] - df['start']
    
    # Handle cases where 'end' is before 'start'
    negative_durations = df['duration'] < 0
    if negative_durations.any():
        raise ValueError("Some events have 'end' times earlier than 'start' times.")
    
    # 2. Compute inter-event interval (next_start - current_end)
    df['inter_event_interval'] = df['start'].shift(-1) - df['end']
    
    # 3. Compute log inter-event interval (log10)
    # Replace non-positive intervals with NaN to avoid log of zero or negative
    df['log_inter_event_interval'] = np.log10(df['inter_event_interval'].replace({0: np.nan}))
    
    # 4. Compute inter-start interval (next_start - current_start)
    df['inter_start_interval'] = df['start'].shift(-1) - df['start']
    
    # 5. Compute instantaneous rate (1 / inter_start_interval)
    df['inst_rate'] = 1 / df['inter_start_interval']
    
    # Handle division by zero or negative intervals in inst_rate
    df['inst_rate'] = df['inst_rate'].replace([np.inf, -np.inf], np.nan)
    
    # # Optional: Round numerical columns for readability
    # df[['duration', 'inter_event_interval', 'log_inter_event_interval', 
    #     'inter_start_interval', 'inst_rate']] = df[
    #         ['duration', 'inter_event_interval', 'log_inter_event_interval', 
    #          'inter_start_interval', 'inst_rate']
    #     ].round(6)
    
    return df

def compute_window_features(df, min_window_size=7):
    """
    Compute windowed temporal features for behavioral events in a DataFrame.

    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame containing per-event temporal features, including 'inst_rate' and 'log_inter_event_interval'.
    min_window_size : int, optional
        The size of the sliding window (number of events), by default 7.
        The regression will be performed on the first (min_window_size - 1) events within each window.

    Returns:
    --------
    pandas.DataFrame
        DataFrame where each row corresponds to a sliding window with the following columns:
            - start: Start time of the first event in the window
            - end: End time of the last event in the window
            - start_index: Index of the first event in the window
            - end_index: Index of the last event in the window
            - num_notes: Number of events in the window (should be min_window_size)
            - window_max_log_inter_event_interval: Maximum log inter-event interval within the first (min_window_size - 1) events
            - window_rate_index_slope: Slope of instantaneous rate over event indices within the first (min_window_size - 1) events
            - window_rate_index_intercept: Intercept of instantaneous rate over event indices within the first (min_window_size - 1) events
            - window_rate_index_normalized_rmse: Normalized Root Mean Square Error of the regression fit (RMSE / y_mean)
    """
    df = df.copy()
    
    # Automatically set regression_window_size
    regression_window_size = min_window_size - 1
    
    # Validate that regression_window_size is at least 1
    if regression_window_size < 1:
        raise ValueError("min_window_size must be at least 2 to perform regression on at least one event.")
    
    # Ensure that required columns exist
    required_columns = {'start', 'end', 'inst_rate', 'log_inter_event_interval'}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"Input DataFrame is missing required columns: {missing}")
    
    # Sort the DataFrame by 'start' time to ensure chronological order
    df = df.sort_values(by='start').reset_index(drop=True)
    
    ### Windowed Temporal Features ###
    
    # Initialize lists to store windowed features
    window_start_times = []
    window_end_times = []
    start_indices = []
    end_indices = []
    num_notes_list = []
    window_max_log_inter_event_interval = []
    window_rate_index_slope = []
    window_rate_index_intercept = []
    window_rate_index_normalized_rmse = []
    
    # Number of windows
    num_windows = len(df) - min_window_size + 1
    
    for i in range(num_windows):
        window_df = df.iloc[i:i+min_window_size]
        
        # Define the regression subset (first min_window_size - 1 events)
        regression_df = window_df.iloc[:regression_window_size]
        
        # Check for NaN values in inst_rate within regression_df
        if regression_df['inst_rate'].isnull().any():
            # Skip this window if any inst_rate is NaN within regression window
            continue
        
        # Extract inst_rate and event indices for regression
        X = np.arange(regression_window_size).reshape(-1, 1)  # Event indices: 0,1,...,min_window_size-2
        y = regression_df['inst_rate'].values  # Actual inst_rate
        
        # Compute y_mean
        y_mean = y.mean()
        if y_mean == 0:
            # Skip this window to avoid division by zero
            continue
        
        # Fit linear regression: inst_rate ~ event index
        model = LinearRegression()
        model.fit(X, y)
        y_pred = model.predict(X)
        
        # Compute slope and intercept
        slope = model.coef_[0]
        intercept = model.intercept_
        
        # Compute RMSE
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        
        # Compute Normalized RMSE
        normalized_rmse = rmse / y_mean
        
        # Compute window_max_log_inter_event_interval (from the regression subset)
        max_log_interval = regression_df['log_inter_event_interval'].max()
        
        # Append to lists
        window_start_times.append(window_df['start'].iloc[0])
        window_end_times.append(window_df['end'].iloc[-1])
        start_indices.append(i)
        end_indices.append(i + min_window_size - 1)
        num_notes_list.append(min_window_size)
        window_max_log_inter_event_interval.append(max_log_interval)
        window_rate_index_slope.append(slope)
        window_rate_index_intercept.append(intercept)
        window_rate_index_normalized_rmse.append(normalized_rmse)
    
    # Create the windowed DataFrame
    df_windowed_features = pd.DataFrame({
        'start': window_start_times,
        'end': window_end_times,
        'start_index': start_indices,
        'end_index': end_indices,
        'num_notes': num_notes_list,
        'window_max_log_inter_event_interval': window_max_log_inter_event_interval,
        'window_rate_index_slope': window_rate_index_slope,
        'window_rate_index_intercept': window_rate_index_intercept,
        'window_rate_index_normalized_rmse': window_rate_index_normalized_rmse
    })
    
    # Optional: Reset index for cleanliness
    df_windowed_features = df_windowed_features.reset_index(drop=True)
    
    return df_windowed_features

def merge_stereotypy_windows(
    df_windowed_features, 
    df_event_features,
    max_log_interval_threshold, 
    rmse_threshold, 
    max_gap,
    max_index_gap,
):
    """
    Merge fixed-size windows into larger segments based on "local stereotypy" criteria with relaxed merging conditions.
    
    A window is considered to exhibit "local stereotypy" if:
        - `window_max_log_inter_event_interval` <= `max_log_interval_threshold`
        - `window_rate_index_normalized_rmse` <= `rmse_threshold`
    
    Consecutive windows that meet these criteria are merged into a single segment if:
        - **Overlapping:** The current window overlaps with the previous window (i.e., the gap in time is negative).
        - **Non-Overlapping:** If not overlapping, then:
            - The gap between the previous window's `end` time and the current window's `start` time is <= `max_gap`
            - The gap between the previous window's `end_index` and the current window's `start_index` is <= `max_index_gap`
    
    Additionally, each merged segment records the number of events it contains and the maximum smoothed instantaneous rate within the segment.
    
    Parameters:
    -----------
    df_windowed_features : pandas.DataFrame
        DataFrame containing windowed temporal features, including:
            - `start`: Start time of the window
            - `end`: End time of the window
            - `start_index`: Index of the first event in the window
            - `end_index`: Index of the last event in the window
            - `window_max_log_inter_event_interval`: Maximum log inter-event interval within the window
            - `window_rate_index_normalized_rmse`: RMSE of the regression fit within the window
            - `window_rate_index_slope`: Slope from the regression fit within the window
            - `window_rate_index_intercept`: Intercept from the regression fit within the window
    
    df_event_features : pandas.DataFrame
        DataFrame containing per-event temporal features, including:
            - `start`: Start time of each event
            - `end`: End time of each event
            - Other features computed by `compute_event_features`
    
    max_log_interval_threshold : float
        Threshold for `window_max_log_inter_event_interval`. Windows with values <= this threshold are considered for merging.
    
    rmse_threshold : float
        Threshold for `window_rate_index_normalized_rmse`. Windows with values <= this threshold are considered for merging.
    
    max_gap : float
        Maximum allowed time gap (in time units) between consecutive windows for them to be merged if they do not overlap.
    
    max_index_gap : int
        Maximum allowed gap (in event indices) between consecutive windows for them to be merged if they do not overlap.
    
    Returns:
    --------
    tuple of pandas.DataFrame
        - `df_filtered`: The filtered DataFrame of windows that meet the merging criteria.
        - `df_segments`: DataFrame where each row corresponds to a merged segment with the following columns:
            - `start`: Start time of the first window in the segment
            - `end`: End time of the last window in the segment
            - `start_index`: Start index of the first window in the segment
            - `end_index`: End index of the last window in the segment
            - `num_events`: Number of events contained within the segment
    """
    # Create a copy of the input DataFrame to avoid modifying the original data
    df = df_windowed_features.copy()
    
    # Filter windows that meet the local stereotypy criteria based on log interval and RMSE thresholds
    df_filtered = df[
        (df['window_max_log_inter_event_interval'] <= max_log_interval_threshold) &
        (df['window_rate_index_normalized_rmse'] <= rmse_threshold)
    ].sort_values(by='start_index').reset_index(drop=True)

    # Initialize a list to store the merged segments
    segments = []
    
    # Initialize variables to keep track of the current segment and the previous window
    current_segment = None
    previous_window = None
    
    # Iterate over each window in the filtered DataFrame
    for _, window in df_filtered.iterrows():
        if current_segment is None:
            # Initialize a new segment with the current window's details
            current_segment = {
                'segment_start_time': window['start'],
                'segment_end_time': window['end'],
                'segment_start_index': window['start_index'],
                'segment_end_index': window['end_index'],
            }
        else:
            # Calculate the gap between the previous window's end time and the current window's start time
            gap_time = window['start'] - previous_window['end']
            
            # Calculate the gap in event indices between the previous window's end_index and the current window's start_index
            gap_index = window['start_index'] - previous_window['end_index'] - 1  # -1 because end_index is inclusive
            
            # Determine if the current window overlaps with the previous window
            if gap_time < 0:
                # Overlapping windows are merged unconditionally
                can_merge = True
            else:
                # Non-overlapping windows are merged only if both time and index gaps are within thresholds
                can_merge = (gap_time <= max_gap) and (gap_index <= max_index_gap)
            
            if can_merge:
                # Merge into current segment
                current_segment['segment_end_time'] = window['end']
                current_segment['segment_end_index'] = window['end_index']
            else:
                # Finalize the current segment and add it to the segments list
                segments.append({
                    'start': current_segment['segment_start_time'],
                    'end': current_segment['segment_end_time'],
                    'start_index': current_segment['segment_start_index'],
                    'end_index': current_segment['segment_end_index'],
                })
                
                # Initialize a new segment with the current window's details
                current_segment = {
                    'segment_start_time': window['start'],
                    'segment_end_time': window['end'],
                    'segment_start_index': window['start_index'],
                    'segment_end_index': window['end_index'],
                }
        
        # Update the reference to the previous window for the next iteration
        previous_window = window
    
    # After processing all windows, ensure the last segment is added to the segments list
    if current_segment is not None:
        segments.append({
            'start': current_segment['segment_start_time'],
            'end': current_segment['segment_end_time'],
            'start_index': current_segment['segment_start_index'],
            'end_index': current_segment['segment_end_index'],
        })
    
    # Convert the list of segments into a DataFrame
    if len(segments) > 0:
        df_segments = pd.DataFrame(segments)
    else:
        df_segments = pd.DataFrame(columns=['start', 'end', 'start_index', 'end_index'])
    
    # Calculate the number of events in each segment
    df_segments['num_events'] = df_segments['end_index'] - df_segments['start_index'] + 1

    # Also compute the duration of each segment
    df_segments['duration'] = df_segments['end'] - df_segments['start']
    
    return df_filtered, df_segments

def characterize_segments(df_events, df_segments, 
                          smoothing_window_size=5,
                          ransac_min_samples=9,
                          ransac_normalized_residual_threshold=0.15,
                          plot_ransac=False):
    """
    Characterize merged segments by computing the maximum smoothed instantaneous rate
    and applying RANSAC regression to identify linear patterns in song-like segments.

    Parameters:
    -----------
    df_events : pandas.DataFrame
        DataFrame containing per-event temporal features, including:
            - 'start': Start time of each event.
            - 'end': End time of each event.
            - 'inst_rate': Instantaneous rate of each event.
            - Other features as computed by compute_event_features().
    df_segments : pandas.DataFrame
        DataFrame containing merged segments with columns:
            - 'start': Start time of the segment.
            - 'end': End time of the segment.
            - 'start_index': Index of the first event in the segment.
            - 'end_index': Index of the last event in the segment.
            - 'num_events': Number of events in the segment.
            - Other features as computed by merge_stereotypy_windows().
    smoothing_window_size : int, optional
        Window size for the rolling median. Defaults to 5.
    song_like_pattern_min_max_rate : float, optional
        Minimum maximum smoothed instantaneous rate to consider a segment as song-like. Defaults to 15.
    ransac_min_samples : int, optional
        The minimum number of samples required to fit the RANSAC model. Defaults to 9.
    ransac_normalized_residual_threshold : float, optional
        Normalized residual threshold for RANSAC to classify inliers. Defaults to 0.15.

    Returns:
    --------
    pandas.DataFrame
        DataFrame where each row corresponds to a segment with additional columns:
            - 'max_smoothed_inst_rate': Maximum smoothed instantaneous rate within the segment.
            - 'is_song_like': Boolean flag indicating if the segment is song-like.
            - 'ransac_slope': Slope of the RANSAC-fitted line (NaN if not applicable).
            - 'ransac_intercept': Intercept of the RANSAC-fitted line (NaN if not applicable).
            - 'ransac_max_rate': Maximum predicted instantaneous rate from RANSAC inliers (NaN if not applicable).
            - 'ransac_normalized_rmse': Normalized RMSE of the RANSAC fit (NaN if not applicable).
            - 'ransac_inlier_count': Number of inliers identified by RANSAC (0 if not applicable).
            - 'ransac_start': Start time of the inlier segment (NaN if not applicable).
            - 'ransac_end': End time of the inlier segment (NaN if not applicable).
    """
    
    df_segments = df_segments.copy()

    ## STEP 1: compute the maximum smoothed instantaneous rate for each segment

    # Initialize the list to store maximum smoothed instantaneous rates
    max_smoothed_inst_rates = []

    # Iterate through each segment in df_segments
    for i, row in df_segments.iterrows():
        # Extract events that fall within the current segment
        events_in_segment = df_events[
            (df_events['start'] >= row['start']) & 
            (df_events['end'] <= row['end'])
        ]
        
        if events_in_segment.empty:
            # If no events fall within the segment, append NaN
            max_smoothed_inst_rates.append(np.nan)
            continue
        
        # Define Median filtering parameters
        window_size = smoothing_window_size  # e.g., 5

        # Apply Median filtering to 'inst_rate'
        # Note: 'inst_rate' for the last event in the segment might not have a following event, hence iloc[:-1]
        smoothed_inst_rate = events_in_segment['inst_rate'].iloc[:-1].rolling(
            window=window_size, 
            min_periods=1, 
            center=True
        ).median()
        
        # Determine the maximum smoothed inst_rate
        max_smoothed_inst_rate = smoothed_inst_rate.max()
        
        # Append the result to the list
        max_smoothed_inst_rates.append(max_smoothed_inst_rate)

    # Optionally, you can add the results back to your df_segments DataFrame
    df_segments['max_smoothed_inst_rate'] = max_smoothed_inst_rates

    ## STEP 2: Apply RANSAC to identify robust linear patterns

    # Initialize lists to store RANSAC results
    ransac_slopes = []
    ransac_intercepts = []
    ransac_max_rates = []
    ransac_min_rates = []
    ransac_normalized_rmses = []
    ransac_inlier_counts = []
    ransac_start_idxs = []
    ransac_end_idxs = []
    ransac_starts = []
    ransac_ends = []

    for i, row in df_segments.iterrows():
        events_in_segment = df_events[
            (df_events['start'] >= row['start']) & 
            (df_events['end'] <= row['end'])
        ].reset_index(drop=True)

        # Apply RANSAC
        # Define the regression subset (first min_window_size - 1 events)
        regression_window_size = len(events_in_segment) - 1
        regression_df = events_in_segment.iloc[:regression_window_size]
        
        # Extract inst_rate and event indices for regression
        X = np.arange(regression_window_size).reshape(-1, 1)  # Event indices: 0,1,...,min_window_size-2
        y = regression_df['inst_rate'].values  # Actual inst_rate

        # print(f'RANSAC residual threshold: {np.mean(y)*ransac_normalized_residual_threshold}')

        ransac = RANSACRegressor(
            min_samples=ransac_min_samples-1,
            residual_threshold=np.mean(y)*ransac_normalized_residual_threshold,
            random_state=42,
        )

        try:
            # Fit the model
            ransac.fit(X, y)
            # print(f'RANSAC TRIALS: {ransac.n_trials_}')
            
            # Predict using the fitted model
            y_pred = ransac.predict(X)

            # Identify inliers and outliers
            inlier_mask = ransac.inlier_mask_
            outlier_mask = ~inlier_mask

            # Calculate inlier count
            inlier_count = np.sum(inlier_mask)
            # Extract slope and intercept
            slope = ransac.estimator_.coef_[0]
            intercept = ransac.estimator_.intercept_
            ransac_max_rate = np.max(y_pred[inlier_mask])
            ransac_min_rate = np.min(y_pred[inlier_mask])
            # Compute RMSE
            rmse = np.sqrt(mean_squared_error(y[inlier_mask], y_pred[inlier_mask]))
            normalized_rmse = rmse / np.mean(y[inlier_mask])

            # get the preperties of the inlier segment
            ransac_start_idx = np.where(inlier_mask)[0][0]
            ransac_end_idx = np.where(inlier_mask)[0][-1]+1
            ransac_start = events_in_segment.iloc[X[inlier_mask].reshape(-1)[0]]['start']
            ransac_end = events_in_segment.iloc[X[inlier_mask].reshape(-1)[-1]+1]['end']

            # plot ransac diagnostic plots
            if plot_ransac:
                fig, ax = plt.subplots(figsize=(4,3))
                ax.scatter(X[inlier_mask], y[inlier_mask], color="tab:blue", marker=".", label="Inliers")
                ax.scatter(X[outlier_mask], y[outlier_mask], color="tab:orange", marker=".", label="Outliers")
                ax.plot(X[inlier_mask], y_pred[inlier_mask], color='red', label='RANSAC fit')
                ax.axvline(ransac_start_idx, color='r', linestyle='--')
                ax.axvline(ransac_end_idx, color='r', linestyle='--')
                ax.axvspan(0, regression_window_size, color='gray', linewidth=0, alpha=0.5)
                ax.set_xlabel('Note index')
                ax.set_ylim([0, 25])
                ax.set_ylabel('Note rate (Hz)')
                plt.legend(loc='upper right', fontsize='small')
                plt.tight_layout()
                plt.show()

            # Store the results
            ransac_slopes.append(slope)
            ransac_intercepts.append(intercept)
            ransac_max_rates.append(ransac_max_rate)
            ransac_min_rates.append(ransac_min_rate)
            ransac_normalized_rmses.append(normalized_rmse)
            ransac_inlier_counts.append(inlier_count)
            ransac_start_idxs.append(ransac_start_idx)
            ransac_end_idxs.append(ransac_end_idx)
            ransac_starts.append(ransac_start)
            ransac_ends.append(ransac_end)

        except Exception as e:
        # In case of any exception during fitting, return NaNs and False
            ransac_slopes.append(np.nan)
            ransac_intercepts.append(np.nan)
            ransac_max_rates.append(np.nan)
            ransac_min_rates.append(np.nan)
            ransac_normalized_rmses.append(np.nan)
            ransac_inlier_counts.append(0)
            ransac_start_idxs.append(np.nan)
            ransac_end_idxs.append(np.nan)
            ransac_starts.append(np.nan)
            ransac_ends.append(np.nan)

    # Add RANSAC results to df_segments
    df_segments['ransac_slope'] = ransac_slopes
    df_segments['ransac_intercept'] = ransac_intercepts
    df_segments['ransac_max_rate'] = ransac_max_rates
    df_segments['ransac_min_rate'] = ransac_min_rates
    df_segments['ransac_normalized_rmse'] = ransac_normalized_rmses
    df_segments['ransac_inlier_count'] = ransac_inlier_counts
    df_segments['ransac_start_index'] = ransac_start_idxs
    df_segments['ransac_end_index'] = ransac_end_idxs
    df_segments['ransac_start'] = ransac_starts
    df_segments['ransac_end'] = ransac_ends

    df_segments['ransac_duration'] = df_segments['ransac_end'] - df_segments['ransac_start']
    df_segments['ransac_num_events'] = df_segments['ransac_end_index'] - df_segments['ransac_start_index'] + 1

    return df_segments

def classify_segments(df_segments, scaler, pca, gmm, cluster_mapping):

    df_segments = df_segments.copy()  # To avoid modifying the original dataframe

    if df_segments.empty:
        # Optionally add an empty 'cluster' column or simply return the original DataFrame
        df_segments['cluster'] = []  
        return df_segments

    # Define the feature columns expected by the models
    features = ['ransac_num_events', 'ransac_max_rate', 'ransac_min_rate']
    
    # Ensure the dataframe contains the required features
    missing_features = [feat for feat in features if feat not in df_segments.columns]
    if missing_features:
        raise ValueError(f"Missing required features: {missing_features}")
    
    # Select and copy the relevant data
    data = df_segments[features].copy()
    
    # Apply the scaler and PCA transformations
    X_scaled = scaler.transform(data)
    X_pca = pca.transform(X_scaled)
    
    # Predict cluster labels using the GMM model
    labels = gmm.predict(X_pca)
    
    # Add the cluster labels as a new column in the dataframe
    df_segments['cluster'] = labels
    df_segments['cluster_label'] = df_segments['cluster'].map(cluster_mapping)
    
    return df_segments

def classify_notes_by_temporal_patterning(df_segments, df_notes):
    # Make a copy of df_notes to avoid modifying the original data
    df_notes = df_notes.copy()

    if df_notes.empty:
        df_notes['type_patterning'] = []  
        return df_notes
    
    # Initialize the new column with default value 'U' (for Unclassified)
    df_notes['type_patterning'] = 'U'
    
    # Iterate through each note
    for note_idx, note in df_notes.iterrows():
        note_start = note['start']
        note_end = note['end']
        
        # Look for a segment that completely contains the note
        for _, segment in df_segments.iterrows():
            if segment['ransac_start'] <= note_start and segment['ransac_end'] >= note_end:
                # Found a segment containing the note
                cluster_label = segment['cluster_label']
                df_notes.at[note_idx, 'type_patterning'] = cluster_label
                # Once a matching segment is found, break out of the inner loop
                break
                
    return df_notes

def classify_notes_by_amplitude(df_notes, amp_high_threshold):
    # Create a copy to avoid modifying the original dataframe
    df_notes = df_notes.copy()

    if df_notes.empty:
        df_notes['type_amplitude'] = []  
        return df_notes
    
    # Check if the required column exists
    if 'max_amp_high' not in df_notes.columns:
        raise ValueError("The dataframe must contain a 'max_amp_high' column.")
    
    # Classify each note based on the threshold
    df_notes['type_amplitude'] = df_notes['max_amp_high'].apply(
        lambda amp: "loud" if amp >= amp_high_threshold else "soft"
    )
    
    return df_notes

def find_vocal_bouts(df_notes, gap_threshold):
    """
    Merge consecutive intervals in df_notes separated by gaps <= gap_threshold.
    
    Parameters:
    - df_notes (pd.DataFrame): DataFrame containing 'start' and 'end' columns.
    - gap_threshold (float): Maximum allowed gap between consecutive intervals to merge them.
    
    Returns:
    - vocal_bouts (pd.DataFrame): DataFrame of merged intervals with additional info.
    - isolated_notes (pd.DataFrame): DataFrame of original intervals not merged into any vocal bout.
    """
    
    if df_notes.empty:
        # Return empty DataFrames if input is empty
        vocal_bouts = pd.DataFrame(columns=['start', 'end', 'sum_duration', 'num_notes'])
        isolated_notes = pd.DataFrame(columns=['start', 'end'])
        return vocal_bouts, isolated_notes
    
    # Create a copy of the input DataFrame to avoid modifying the original data
    df_notes = df_notes.copy()

    # Sort intervals by start time
    intervals_sorted = df_notes.sort_values(by='start').reset_index(drop=True)
    
    # Convert to list of lists for easier manipulation
    intervals = intervals_sorted[['start', 'end']].values.tolist()
    
    # Initialize merged intervals with the first interval
    merged_intervals = [intervals[0].copy()]
    sum_durations = [intervals[0][1] - intervals[0][0]]
    num_notes = [1]
    
    # Iterate through the sorted intervals and merge based on gap_threshold
    for current in intervals[1:]:
        last_merged = merged_intervals[-1]
        gap = current[0] - last_merged[1]
        
        if gap <= gap_threshold:
            # Merge the current interval with the last merged interval
            merged_intervals[-1][1] = current[1]
            sum_durations[-1] += current[1] - current[0]
            num_notes[-1] += 1
        else:
            # No merge needed; add the current interval as a new entry
            merged_intervals.append(current.copy())
            sum_durations.append(current[1] - current[0])
            num_notes.append(1)
    
    # Create a DataFrame for merged intervals
    merged_df = pd.DataFrame(merged_intervals, columns=['start', 'end'])
    merged_df['sum_duration'] = sum_durations
    merged_df['num_notes'] = num_notes
    merged_df['duration'] = merged_df['end'] - merged_df['start']
    
    # Separate merged intervals into vocal_bouts and isolated_notes
    vocal_bouts = merged_df[merged_df['num_notes'] > 1].reset_index(drop=True)
    isolated_merged = merged_df[merged_df['num_notes'] == 1].reset_index(drop=True)
    
    # To find isolated_notes, merge the original intervals that correspond to isolated_merged
    # Since isolated_merged corresponds to single original intervals, we can match them
    # based on start and end times
    if not isolated_merged.empty:
        # Merge based on 'start' and 'end' to ensure correct matching
        isolated_notes = pd.merge(isolated_merged[['start', 'end']], intervals_sorted, on=['start', 'end'], how='left')
    else:
        # If there are no isolated merged intervals, return an empty DataFrame
        isolated_notes = pd.DataFrame(columns=['start', 'end'])
    
    return vocal_bouts, isolated_notes

def analyze_song_patterning(df_song_segments, df_notes, song_final_note_occupancy=0.5):

    # Make a copy of the input DataFrames to avoid modifying the original data
    df_song_segments = df_song_segments.copy()
    df_notes = df_notes.copy()

    if df_song_segments.empty:
        # Return an empty DataFrame if there are no song segments
        return pd.DataFrame()
    
    songs = []
    for i_segment, song_segment in df_song_segments.iterrows():

        # Record song start and end times
        t_song_start = song_segment['ransac_start']
        t_song_end = song_segment['ransac_end']
        t_song_duration = t_song_end - t_song_start

        # Extract notes in song
        notes_in_song = df_notes[
            (df_notes['start'] >= t_song_start) & 
            (df_notes['end'] <= t_song_end)
        ]

        # Compute song patterning features
        xs = notes_in_song.index[:-1]-notes_in_song.index[0]
        ys = notes_in_song['inst_rate'].iloc[:-1].values

        slope, intercept, r_value, _, _ = linregress(xs, ys)
        y_preds = xs * slope + intercept
        rmse = np.sqrt(mean_squared_error(ys, y_preds))
        nrmse = rmse/np.mean(ys)
        rate_idx_rmax = 0 * slope + intercept
        rate_idx_rmin = (len(notes_in_song)-1) * slope + intercept

        # get the data r_min and r_max
        data_r_start, data_r_end = ys[0], ys[-1]

        # pred song duration from slope, r_min, r_max
        t_song_duration_pred = 1 / slope * np.log(rate_idx_rmin / rate_idx_rmax)
        # add an estimated last note duration
        t_song_duration_pred += 1 / rate_idx_rmin * song_final_note_occupancy

        # find longest note
        longest_note = notes_in_song.loc[notes_in_song['duration'].idxmax()]
        longest_note_t_start = longest_note['start']
        longest_note_duration = longest_note['duration']

        songs.append({
            'start': t_song_start,
            'end': t_song_end,
            'duration': t_song_duration,
            'num_notes': len(notes_in_song),
            'data_r_start': data_r_start,
            'data_r_end': data_r_end,
            'rate_idx_slope': slope,
            'rate_idx_intercept': intercept,
            'rate_idx_rmax': rate_idx_rmax,
            'rate_idx_rmin': rate_idx_rmin,
            'rate_idx_normalized_rmse': nrmse,
            'rate_idx_r2': r_value**2,
            'duration_pred': t_song_duration_pred,
            'longest_note_t_start': longest_note_t_start,
            'longest_note_duration': longest_note_duration,
        })

    df_songs = pd.DataFrame(songs)

    return df_songs

def get_song_social_context(df_songs, df_notes, context_duration=10):

    df_songs = df_songs.copy()
    
    num_notes_pre_song = []
    num_notes_post_song = []
    
    for i_song, song_info in df_songs.iterrows():
        t_song_start = song_info['start']
        t_song_end = song_info['end']

        t_pre_window_start = t_song_start - context_duration
        t_pre_window_end = t_song_start
        notes_in_pre_window = df_notes[
            (df_notes['start']>t_pre_window_start) &
            (df_notes['end']<t_pre_window_end)]
        
        t_post_window_start = t_song_end
        t_post_window_end = t_song_end + context_duration
        notes_in_post_window = df_notes[
            (df_notes['start']>t_post_window_start) &
            (df_notes['end']<t_post_window_end)]
        
        num_notes_pre_song.append(len(notes_in_pre_window))
        num_notes_post_song.append(len(notes_in_post_window))

    df_songs['num_notes_pre_song'] = num_notes_pre_song
    df_songs['num_notes_post_song'] = num_notes_post_song

    return df_songs

def assign_bout_duration_to_notes(df_notes, vocal_bouts):
    """
    Given the original notes and the computed vocal bouts, assign each note a new column 
    'bout_duration' such that:
      - If the note is part of a vocal bout (i.e. its start and end times fall within the 
        bout boundaries), then 'bout_duration' is the overall bout duration.
      - Otherwise, if the note is isolated, then 'bout_duration' is just the note's own duration.
    
    Parameters:
      df_notes (pd.DataFrame): DataFrame containing individual notes with at least 'start' and 'end' columns.
      vocal_bouts (pd.DataFrame): DataFrame of vocal bouts (merged intervals) with columns 
                                  'start', 'end', and 'duration' (i.e. bout duration).
    
    Returns:
      pd.DataFrame: A copy of df_notes with an added 'bout_duration' column.
    """
    # Make a copy so we do not modify the original data
    df_notes = df_notes.copy()
    
    # First, initialize bout_duration with each note's own duration.
    df_notes['bout_duration'] = df_notes['end'] - df_notes['start']
    
    # For each bout in vocal_bouts, update the bout_duration for notes that fall entirely within the bout.
    for _, bout in vocal_bouts.iterrows():
        # We assume vocal_bouts already has a 'duration' column. 
        # If not, you can compute it as: bout_duration = bout['end'] - bout['start']
        bout_duration = bout['duration']  
        
        # Create a boolean mask: note is in the bout if its start and end are within the bout boundaries.
        mask = (df_notes['start'] >= bout['start']) & (df_notes['end'] <= bout['end'])
        df_notes.loc[mask, 'bout_duration'] = bout_duration
    
    return df_notes

def characterize_song_context(df_notes, df_songs, gap_threshold):
    """
    For each song in df_songs, extend its context (song bout) by looking for note bouts
    that overlap the song. If multiple bouts overlap, the song's context is the union 
    (min start and max end) of all overlapping bouts.
    
    In addition, count how many note events (from df_notes) in the song bout occur before 
    the song and how many occur after the song.
    
    Parameters:
    - df_notes (pd.DataFrame): DataFrame of note events with 'start' and 'end' columns.
    - df_songs (pd.DataFrame): DataFrame of songs with 'start' and 'end' columns.
    - gap_threshold (float): Maximum allowed gap between consecutive notes to merge them.
    
    Returns:
    - df_songs (pd.DataFrame): A copy of df_songs with four new columns:
         'song_bout_start', 'song_bout_end', 'song_bout_notes_before', and 'song_bout_notes_after'
    """
    # Build bouts from notes.
    vocal_bouts, isolated_notes = find_vocal_bouts(df_notes, gap_threshold)
    
    # Combine both merged bouts and isolated notes.
    bouts = pd.concat(
        [
            vocal_bouts[['start', 'end']],
            isolated_notes[['start', 'end']]
        ],
        ignore_index=True
    )
    bouts = bouts.sort_values('start').reset_index(drop=True)
    
    # Prepare lists for song bout information and note counts.
    bout_starts = []
    bout_ends = []
    notes_before_counts = []
    notes_after_counts = []
    t_before = []
    t_after = []
    
    # Iterate over each song.
    for _, song in df_songs.iterrows():
        # Find all bouts that overlap the song.
        matching_bouts = bouts[(bouts['start'] <= song['end']) & (bouts['end'] >= song['start'])]
        
        if not matching_bouts.empty:
            # The song's bout is the union of all matching bouts.
            song_context_start = matching_bouts['start'].min()
            song_context_end = matching_bouts['end'].max()
            bout_starts.append(song_context_start)
            bout_ends.append(song_context_end)
            
            # Find all note events (from df_notes) that contributed to this bout.
            bout_notes = df_notes[(df_notes['start'] >= song_context_start) & (df_notes['end'] <= song_context_end)]
            
            # Count notes that finish on or before the song starts (i.e. "before" the song).
            notes_before = bout_notes[bout_notes['end'] < song['start']].shape[0]
            # Count notes that start on or after the song ends (i.e. "after" the song).
            notes_after = bout_notes[bout_notes['start'] > song['end']].shape[0]
            
            notes_before_counts.append(notes_before)
            notes_after_counts.append(notes_after)

            t_before.append(song['start'] - song_context_start)
            t_after.append(song_context_end - song['end'])
        else:
            # No overlapping bout: set bout boundaries to NaN and counts to 0.
            bout_starts.append(np.nan)
            bout_ends.append(np.nan)
            notes_before_counts.append(0)
            notes_after_counts.append(0)
            t_before.append(np.nan)
            t_after.append(np.nan)
    
    # Add new columns to the songs DataFrame.
    df_songs = df_songs.copy()
    df_songs['song_bout_start'] = bout_starts
    df_songs['song_bout_end'] = bout_ends
    df_songs['song_bout_notes_before'] = notes_before_counts
    df_songs['song_bout_notes_after'] = notes_after_counts
    df_songs['song_bout_t_before'] = t_before
    df_songs['song_bout_t_after'] = t_after

    
    return df_songs

def is_not_in_intervals(t, intervals):
    return not intervals.contains(t).any()

def find_intervals(t, gap_thr=0.01, min_dur=0.01, max_dur=0.25):
    """
    given a numpy array of time t, find the intervals that contain these t with a minimum gap threshold
    
    """
    if len(t) == 0:
        return []
    
    t_sorted = np.sort(t)  # Ensure t is sorted
    
    # Find where the difference between consecutive elements is >= gap_threshold
    gaps = np.where(np.diff(t_sorted) > gap_thr)[0]
    
    # Identify the start and end of each interval
    interval_starts = np.insert(gaps + 1, 0, 0)
    interval_ends = np.append(gaps, len(t_sorted) - 1)
    
    # Use starts and ends to create intervals
    intervals = np.vstack((t_sorted[interval_starts], t_sorted[interval_ends])).T
    
    # Calculate durations and create a mask for filtering
    durations = intervals[:, 1] - intervals[:, 0]
    mask = (durations >= min_dur) & (durations <= max_dur)
    
    # Apply the mask to filter intervals
    filtered_intervals = intervals[mask]
    
    return filtered_intervals