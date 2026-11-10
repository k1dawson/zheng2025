"""
Utility functions


"""

import numpy as np
from scipy.stats import (
    gaussian_kde,
)
from scipy.signal import (
    find_peaks,
    peak_prominences,
)
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle
from scipy.interpolate import interp1d

def compute_1d_kde(data, xmin=None, xmax=None, bw_method='scott', gridsize=1000):
    """
    Compute the 1D KDE for given data and return grid values and density estimates.

    Parameters:
    - data: 1D array-like, shape (N,)
    - xmin: float or None, minimum value for the grid. If None, set to data.min() - 1.
    - xmax: float or None, maximum value for the grid. If None, set to data.max() + 1.
    - bw_method: str or scalar, bandwidth method for gaussian_kde ('scott', 'silverman', or scalar)
    - gridsize: int, number of points in the grid

    Returns:
    - x_grid: 1D array of grid points
    - density: 1D array of density estimates corresponding to grid points
    """
    # Remove NaN and Inf values
    data = np.asarray(data)
    data = data[np.isfinite(data)]
    
    if data.size == 0:
        raise ValueError("Input data must contain at least one finite value.")
    
    # Define grid boundaries
    if xmin is None:
        xmin = data.min() - 1  # Extend range for better visualization
    if xmax is None:
        xmax = data.max() + 1
    
    if xmin >= xmax:
        raise ValueError("xmin must be less than xmax.")
    
    # Perform KDE
    kde = gaussian_kde(data, bw_method=bw_method)
    
    # Define grid over specified range
    x_grid = np.linspace(xmin, xmax, gridsize)
    
    # Evaluate KDE on grid
    density = kde(x_grid)
    
    return x_grid, density


def compute_2d_kde(data, x_min, x_max, y_min, y_max, bw_method='scott', gridsize=100):
    """
    Compute the 2D KDE for given data and return grid coordinates and density values.

    Parameters:
    - data: 2D array-like, shape (2, N)
    - x_min, x_max, y_min, y_max: float, boundaries for the grid
    - bw_method: bw_method argument for gaussian_kde
    - gridsize: int, number of points in each dimension

    Returns:
    - X, Y: 2D meshgrid arrays
    - Z: 2D array of density values
    """
    # Convert data to a NumPy array
    data = np.asarray(data)

    # Validate data shape
    if data.ndim != 2 or data.shape[0] != 2:
        raise ValueError("Input 'data' must be a 2D array with shape (2, N) where N is the number of samples.")

    # Remove columns (samples) with any Inf or NaN values
    valid_mask = np.isfinite(data).any(axis=0)
    data_clean = data[:, valid_mask]

    # Check if any valid data points remain
    if data_clean.shape[1] == 0:
        raise ValueError("No valid data points remain after removing NaNs.")
    
    # Create grid
    x, y = np.mgrid[x_min:x_max:gridsize*1j, y_min:y_max:gridsize*1j]
    positions = np.vstack([x.ravel(), y.ravel()])
    
    # Perform KDE
    kernel = gaussian_kde(data_clean, bw_method=bw_method)
    
    Z = np.reshape(kernel(positions).T, x.shape)
    
    return x, y, Z

def find_threshold_between_peaks(x, density, num_peaks=2):
    # Find all peaks in the density
    peaks, _ = find_peaks(density)
    
    if len(peaks) < num_peaks:
        raise ValueError(f"Expected at least {num_peaks} peaks, but found {len(peaks)}.")
    
    # Compute prominences of all peaks
    prominences = peak_prominences(density, peaks)[0]
    
    # Sort peaks based on prominence
    sorted_indices = np.argsort(prominences)[::-1]
    top_peaks = peaks[sorted_indices[:num_peaks]]
    top_peaks = np.sort(top_peaks)
    
    if len(top_peaks) < num_peaks:
        raise ValueError(f"Could not identify {num_peaks} distinct peaks in the distribution.")
    
    # Find the valley between the two top peaks
    peak1, peak2 = top_peaks[:num_peaks]
    if peak1 == peak2:
        raise ValueError("The two top peaks are the same. Unable to determine a valley.")
    
    # Ensure peak1 is to the left of peak2
    if peak1 > peak2:
        peak1, peak2 = peak2, peak1
    
    # Extract the region between the two peaks
    density_between = density[peak1:peak2]
    x_between = x[peak1:peak2]
    
    # Find the minimum in this region
    valley_index = np.argmin(density_between) + peak1
    threshold = x[valley_index]
    
    return threshold, x[valley_index], valley_index

def draw_ellipse(position, covariance, ax, n_std=1.0, **kwargs):
    """
    Draw an ellipse representing the covariance matrix centered at position.
    `position`: The center of the ellipse (mean of the Gaussian).
    `covariance`: 2x2 covariance matrix of the Gaussian.
    `ax`: Matplotlib Axes object to draw the ellipse on.
    `n_std`: The number of standard deviations for the ellipse radius.
    Additional keyword arguments are passed to Ellipse patch.
    """
    if covariance.shape == (2, 2):
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)
        order = eigenvalues.argsort()[::-1]
        eigenvalues, eigenvectors = eigenvalues[order], eigenvectors[:, order]
        angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
        
        # Adjust width and height for the desired number of std deviations
        width, height = 2 * n_std * np.sqrt(eigenvalues)
    else:
        angle = 0
        width = height = 2 * n_std * np.sqrt(covariance)

    ell = Ellipse(xy=position, width=width, height=height, angle=angle, **kwargs)
    ax.add_patch(ell)

def plot_skeleton(ax, location_frame, skeleton, color):

    xs = location_frame[:,0].astype(float)
    ys = location_frame[:,1].astype(float)

    # plot joints
    for i_joint in range(skeleton.shape[0]):
        index1, index2 = skeleton[i_joint, 0], skeleton[i_joint, 1]
        ax.plot([xs[index1], xs[index2]], 
                [ys[index1], ys[index2]],
                color=color, linewidth=1, linestyle='-')

    # plot points
    for j in range(location_frame.shape[0]):
        ax.add_patch(Circle([xs[j], ys[j]], radius=2, color=color, zorder=2))


def fill_missing(Y, kind="linear"):
    """Fills missing values independently along each dimension after the first."""

    # Store initial shape.
    initial_shape = Y.shape

    # Flatten after first dim.
    Y = Y.reshape((initial_shape[0], -1))

    # Interpolate along each slice.
    for i in range(Y.shape[-1]):
        y = Y[:, i]

        # Build interpolant.
        x = np.flatnonzero(~np.isnan(y))
        f = interp1d(x, y[x], kind=kind, fill_value=np.nan, bounds_error=False)

        # Fill missing
        xq = np.flatnonzero(np.isnan(y))
        y[xq] = f(xq)
        
        # Fill leading or trailing NaNs with the nearest non-NaN values
        mask = np.isnan(y)
        y[mask] = np.interp(np.flatnonzero(mask), np.flatnonzero(~mask), y[~mask])

        # Save slice
        Y[:, i] = y

    # Restore to initial shape.
    Y = Y.reshape(initial_shape)

    return Y

def compute_moving_event_rate(events_df, start_time=0, end_time=3600, window_size=10, step_size=10):
    """
    Computes the event rate (counts) in a sliding window over the duration of a session,
    returning NumPy arrays for window start times and counts.
    
    Parameters:
        events_df (pd.DataFrame): DataFrame containing event data with a 'start' column.
        start_time (float): Start time of the session.
        end_time (float): End time of the session.
        window_size (float): Size of the sliding window in seconds.
        step_size (float): Step size to slide the window in seconds.
        
    Returns:
        window_starts (np.ndarray): Array of window start times.
        counts (np.ndarray): Array of event counts in each window.
    """
    # Create an array of window start times from start_time to end_time such that window fits within end_time
    window_starts = np.arange(start_time, end_time - window_size + step_size, step_size)
    window_midpoints = window_starts + window_size / 2.0
    counts = np.empty_like(window_starts, dtype=int)
    
    # Loop through each window and count events
    for i, t in enumerate(window_starts):
        window_end = t + window_size
        # Count events where the start time falls within the current window
        count = events_df[(events_df['start'] >= t) & (events_df['start'] < window_end)].shape[0]
        counts[i] = count
        
    return window_midpoints, counts