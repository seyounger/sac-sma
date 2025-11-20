#!/usr/bin/env python3
"""
Generate comparisons plots for SAC-SMA branch outputs ran in standalone mode.

Reads outputs from all branches in config.yaml and creates visualizations
for each variable to compare distributions and differences across branches.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import yaml
from typing import Dict, List
from scipy import stats


# Paths
REPO_PATH = Path(__file__).parent.parent
TEST_CASES_PATH = REPO_PATH / "test_cases"


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_test_case_path(branch: str, template_case: str) -> Path:
    """Get the path to a branch's test case directory."""
    test_case_name = f"{template_case}_{branch.replace('/', '_')}"
    return TEST_CASES_PATH / test_case_name


def get_plot_title(branch: str, plot_titles: dict) -> str:
    """Get custom plot title for a branch, or use branch name."""
    return plot_titles.get(branch, branch)


def read_output_file(branch: str, template_case: str) -> pd.DataFrame:
    """Read the output file for a branch (auto-detects filename)."""
    test_case_path = get_test_case_path(branch, template_case)
    output_dir = test_case_path / "output"
    
    # Auto-detect output file
    output_files = list(output_dir.glob("output.sacbmi.*.txt"))
    if not output_files:
        raise FileNotFoundError(f"No output files found in {output_dir}")
    
    # Read with high precision
    return pd.read_csv(output_files[0], sep=r'\s+', float_precision='round_trip')


def read_state_file(branch: str, template_case: str) -> pd.DataFrame:
    """Read the state file for a branch (auto-detects filename)."""
    test_case_path = get_test_case_path(branch, template_case)
    state_dir = test_case_path / "state"
    
    # Auto-detect state file
    state_files = list(state_dir.glob("sac_states.*.txt"))
    if not state_files:
        raise FileNotFoundError(f"No state files found in {state_dir}")
    
    # Read with high precision
    return pd.read_csv(state_files[0], sep=r'\s+', float_precision='round_trip')


def load_all_branch_data(config: dict) -> Dict[str, pd.DataFrame]:
    """Load output data from all branches."""
    branches = config['branches']
    template_case = config['template_case']
    
    data = {}
    for branch in branches:
        try:
            df = read_output_file(branch, template_case)
            data[branch] = df
        except Exception as e:
            print(f"Failed to load {branch}: {e}")
    
    return data


def load_all_branch_states(config: dict) -> Dict[str, pd.DataFrame]:
    """Load state data from all branches."""
    branches = config['branches']
    template_case = config['template_case']
    
    data = {}
    for branch in branches:
        try:
            df = read_state_file(branch, template_case)
            data[branch] = df
        except Exception as e:
            print(f"Failed to load state for {branch}: {e}")
    
    return data


def get_numeric_columns(data: Dict[str, pd.DataFrame]) -> List[str]:
    """Get list of numeric columns common to all branches."""
    # Variables to exclude from plotting
    exclude_vars = {'year'}
    
    # Get columns from first branch
    first_branch = list(data.keys())[0]
    all_cols = set(data[first_branch].columns)
    
    # Find common columns across all branches
    for df in data.values():
        all_cols &= set(df.columns)
    
    # Filter to numeric columns only, excluding specified variables
    numeric_cols = []
    for col in sorted(all_cols):
        if col not in exclude_vars and data[first_branch][col].dtype in [np.float64, np.float32, np.int64, np.int32]:
            numeric_cols.append(col)
    
    return numeric_cols


def create_boxplot_comparison(data: Dict[str, pd.DataFrame], variable: str, 
                              plot_titles: dict, pdf_page=None):
    """Create boxplot comparison for a single variable across all branches.
    
    Args:
        data: Dictionary of branch name to DataFrame
        variable: Variable name to plot
        plot_titles: Dictionary mapping branch names to display titles
        pdf_page: PdfPages object to save to (if None, returns False)
    
    Returns:
        True if plot was created, False if skipped
    """
    # Prepare data for boxplot
    box_data = []
    labels = []
    
    for branch, df in data.items():
        if variable in df.columns:
            box_data.append(df[variable].values)
            labels.append(get_plot_title(branch, plot_titles))
    
    if not box_data:
        print(f"  [WARN] Skipping {variable}: not found in any branch")
        return False
    
    # Check if all branches have identical values
    if len(box_data) > 1:
        # First check if all arrays have the same length
        all_same_length = all(len(box_data[0]) == len(box_data[i]) 
                              for i in range(1, len(box_data)))
        
        # Only compare values if lengths match
        if all_same_length:
            # Compare all arrays - if all identical, skip
            all_identical = all(np.allclose(box_data[0], box_data[i], rtol=1e-15, atol=0) 
                               for i in range(1, len(box_data)))
            if all_identical:
                print(f"  [SKIP] Skipping {variable}: identical across all branches")
                return False
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create boxplot
    bp = ax.boxplot(box_data, tick_labels=labels, patch_artist=True)
    
    # Customize appearance
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
        patch.set_alpha(0.7)
    
    for whisker in bp['whiskers']:
        whisker.set(linewidth=1.5)
    
    for median in bp['medians']:
        median.set(color='red', linewidth=2)
    
    # Add labels and title
    ax.set_ylabel(variable, fontsize=12)
    ax.set_title(f'{variable} Distribution Across Branches', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Rotate x-axis labels if needed
    plt.xticks(rotation=45, ha='right')
    
    # Add statistics text box
    stats_text = []
    for i, (branch, values) in enumerate(zip(labels, box_data)):
        median_val = np.median(values)
        mean_val = np.mean(values)
        std_val = np.std(values)
        stats_text.append(f'{branch}: μ={mean_val:.6e}, σ={std_val:.6e}')
    
    # Place stats below the plot
    stats_str = '\n'.join(stats_text)
    fig.text(0.5, 0.02, stats_str, ha='center', fontsize=9, 
             family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout(rect=[0, 0.15, 1, 1])  # Make room for stats
    
    # Save to PDF
    if pdf_page:
        pdf_page.savefig(fig, dpi=150, bbox_inches='tight')
    
    plt.close()
    
    return True


def generate_all_boxplots(config: dict, data: Dict[str, pd.DataFrame]):
    """Generate boxplot comparisons for all variables in a single PDF."""
    # Create output directory
    plot_dir = REPO_PATH / "tests" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    # Get variables to plot
    variables = get_numeric_columns(data)
    plot_titles = config.get('plot_titles', {})
    template_case = config['template_case']
    
    # Output PDF path
    pdf_path = plot_dir / f"boxplots_{template_case}.pdf"
    
    success_count = 0
    
    # Create multi-page PDF
    with PdfPages(pdf_path) as pdf:
        for variable in variables:
            if create_boxplot_comparison(data, variable, plot_titles, pdf):
                success_count += 1
    
    print(f"Generated {success_count} boxplots: {pdf_path.relative_to(REPO_PATH)}")


def generate_mass_balance_timeseries(config: dict, data: Dict[str, pd.DataFrame]):
    """Generate mass_balance timeseries plot with one panel per branch."""
    from matplotlib.ticker import FuncFormatter
    import matplotlib.dates as mdates
    
    plot_dir = REPO_PATH / "tests" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    plot_titles = config.get('plot_titles', {})
    template_case = config['template_case']
    
    # Filter branches that have mass_balance data
    available_branches = []
    for branch, df in data.items():
        if 'mass_balance' in df.columns:
            available_branches.append(branch)
    
    if len(available_branches) == 0:
        return
    
    # Create figure with one subplot per branch
    n_branches = len(available_branches)
    fig, axes = plt.subplots(n_branches, 1, figsize=(14, 4 * n_branches))
    
    # Handle single branch case
    if n_branches == 1:
        axes = [axes]
    
    # Custom formatter for y-axis with embedded scientific notation
    def sci_formatter(x, pos):
        if x == 0:
            return '0'
        else:
            exp = int(np.floor(np.log10(abs(x))))
            coeff = x / 10**exp
            if abs(coeff - 1.0) < 0.01:
                return f'$10^{{{exp}}}$'
            else:
                return f'${coeff:.1f}\\times10^{{{exp}}}$'
    
    # Plot each branch in its own panel
    for idx, branch in enumerate(available_branches):
        ax = axes[idx]
        df = data[branch]
        
        # Create datetime index from year, mo, dy, hr columns
        if all(col in df.columns for col in ['year', 'mo', 'dy', 'hr']):
            dates = pd.to_datetime(df[['year', 'mo', 'dy', 'hr']].rename(
                columns={'year': 'year', 'mo': 'month', 'dy': 'day', 'hr': 'hour'}
            ))
            x_values = dates
            x_label = 'Year'
        else:
            # Fallback to timesteps if date columns not available
            x_values = np.arange(len(df))
            x_label = 'Timestep'
        
        ax.plot(x_values, df['mass_balance'], linewidth=1.5, color='black')
        
        ax.set_xlabel(x_label, fontsize=11)
        ax.set_ylabel('Mass Balance (mm)', fontsize=11)
        
        # Use custom plot title from config if available
        plot_title = get_plot_title(branch, plot_titles)
        ax.set_title(plot_title, fontsize=12, fontweight='bold')
        
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
        
        # Format x-axis for dates if using datetime
        if x_label == 'Year':
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax.xaxis.set_major_locator(mdates.YearLocator(5))  # Major ticks every 5 years
            ax.xaxis.set_minor_locator(mdates.YearLocator(1))  # Minor ticks every year
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')
            # Set x-axis limits with minimal padding (2% of range on each side)
            x_range = x_values.max() - x_values.min()
            if pd.notna(x_range) and hasattr(x_range, 'days') and not pd.isna(x_range.days):
                padding = pd.Timedelta(days=x_range.days * 0.01)
                ax.set_xlim(x_values.min() - padding, x_values.max() + padding)
        
        # Calculate statistics
        mb_values = df['mass_balance']
        max_val = mb_values.max()
        min_val = mb_values.min()
        std_val = mb_values.std()
        
        # Check for NaN values and skip if data is invalid
        if pd.isna(max_val) or pd.isna(min_val) or pd.isna(std_val):
            continue
        
        # Set y-axis limits based on data range
        data_range = max_val - min_val
        if pd.isna(data_range):
            continue
        elif data_range == 0:
            # All values identical
            if max_val == 0:
                ax.set_ylim(-1e-15, 1e-15)
            else:
                ax.set_ylim(max_val - abs(max_val) * 0.5, max_val + abs(max_val) * 0.5)
        elif data_range < 1e-20:  # Very small range - tighten y-axis
            center = (max_val + min_val) / 2
            padding = max(data_range * 0.5, abs(center) * 0.05, 1e-28)
            ax.set_ylim(center - padding, center + padding)
        else:
            # Add padding to y-axis limits
            padding = data_range * 0.1
            ax.set_ylim(min_val - padding, max_val + padding)
        
        # Format values with appropriate precision
        def format_val(val):
            if abs(val) < 1e-20:
                return f'{val:.2e}'
            else:
                return f'{val:.1e}'
        
        # Add statistics box in lower left
        stats_text = f'Max: {format_val(max_val)}\nMin: {format_val(min_val)}\nStd: {format_val(std_val)}'
        ax.text(0.02, 0.08, stats_text, 
               transform=ax.transAxes,
               verticalalignment='bottom', horizontalalignment='left',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
               fontsize=11, family='monospace')
        
        # Format y-axis with embedded scientific notation
        ax.yaxis.set_major_formatter(FuncFormatter(sci_formatter))
    
    plt.tight_layout()
    
    # Save plot
    plot_path = plot_dir / f"mass_balance_timeseries_{template_case}.png"
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Mass balance timeseries: {plot_path.relative_to(REPO_PATH)}")


def generate_mass_balance_combined_logscale(config: dict, data: Dict[str, pd.DataFrame]):
    """Generate combined mass_balance plot with all branches on log scale."""
    import matplotlib.dates as mdates
    
    plot_dir = REPO_PATH / "tests" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    plot_titles = config.get('plot_titles', {})
    template_case = config['template_case']
    
    # Filter branches that have mass_balance data
    available_branches = []
    for branch, df in data.items():
        if 'mass_balance' in df.columns:
            available_branches.append(branch)
    
    if len(available_branches) == 0:
        return
    
    # Create single plot with all branches
    fig, ax = plt.subplots(1, 1, figsize=(14, 6))
    
    # Plot each branch on the same axes
    colors = plt.cm.tab10(np.linspace(0, 1, len(available_branches)))
    
    for idx, branch in enumerate(available_branches):
        df = data[branch]
        
        # Create datetime index from year, mo, dy, hr columns
        if all(col in df.columns for col in ['year', 'mo', 'dy', 'hr']):
            dates = pd.to_datetime(df[['year', 'mo', 'dy', 'hr']].rename(
                columns={'year': 'year', 'mo': 'month', 'dy': 'day', 'hr': 'hour'}
            ))
            x_values = dates
            x_label = 'Year'
        else:
            # Fallback to timesteps if date columns not available
            x_values = np.arange(len(df))
            x_label = 'Timestep'
        
        # Get plot title for legend
        plot_title = get_plot_title(branch, plot_titles)
        
        # Plot absolute value for log scale (mass balance can be positive or negative)
        abs_mb = np.abs(df['mass_balance'])
        ax.plot(x_values, abs_mb, linewidth=1.5, color=colors[idx], 
                label=plot_title, alpha=0.8)
    
    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel('|Mass Balance| (mm)', fontsize=12)
    ax.set_title('Mass Balance Comparison (Log Scale)', fontsize=14, fontweight='bold')
    
    # Set log scale for y-axis
    ax.set_yscale('log')
    
    # Format x-axis for dates if using datetime
    if x_label == 'Year':
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator(5))  # Major ticks every 5 years
        ax.xaxis.set_minor_locator(mdates.YearLocator(1))  # Minor ticks every year
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')
        # Set x-axis limits with minimal padding (2% of range on each side)
        x_range = x_values.max() - x_values.min()
        if pd.notna(x_range) and hasattr(x_range, 'days') and not pd.isna(x_range.days):
            padding = pd.Timedelta(days=x_range.days * 0.02)
            ax.set_xlim(x_values.min() - padding, x_values.max() + padding)
    
    ax.grid(True, alpha=0.3, which='both')
    ax.legend(loc='best', framealpha=0.9)
    
    plt.tight_layout()
    
    # Save plot
    plot_path = plot_dir / f"mass_balance_combined_logscale_{template_case}.png"
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Mass balance combined (log scale): {plot_path.relative_to(REPO_PATH)}")


def generate_summary_statistics(config: dict, data: Dict[str, pd.DataFrame]):
    """Generate summary statistics table for all variables."""
    plot_dir = REPO_PATH / "tests" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    variables = get_numeric_columns(data)
    plot_titles = config.get('plot_titles', {})
    template_case = config['template_case']
    
    # Create summary CSV
    summary_rows = []
    
    for variable in variables:
        for branch, df in data.items():
            if variable in df.columns:
                values = df[variable]
                summary_rows.append({
                    'variable': variable,
                    'branch': get_plot_title(branch, plot_titles),
                    'min': values.min(),
                    'max': values.max(),
                    'mean': values.mean(),
                    'median': values.median(),
                    'std': values.std(),
                    'q25': values.quantile(0.25),
                    'q75': values.quantile(0.75)
                })
    
    summary_df = pd.DataFrame(summary_rows)
    summary_path = plot_dir / f"summary_statistics_{template_case}.csv"
    summary_df.to_csv(summary_path, index=False)
    
    print(f"Summary statistics: {summary_path.relative_to(REPO_PATH)}")


def convert_tci_to_cms(tci_mm: float, area_km2: float, timestep_sec: float) -> float:
    """Convert TCI from mm/timestep to cubic meters per second.
    
    Args:
        tci_mm: Total channel inflow in millimeters per timestep
        area_km2: Watershed area in square kilometers
        timestep_sec: Model timestep in seconds
        
    Returns:
        Flow rate in cubic meters per second (cms)
    """
    tci_m = tci_mm / 1000.0  # mm to meters
    area_m2 = area_km2 * 1e6  # km² to m²
    volume_m3 = tci_m * area_m2  # m³
    flow_cms = volume_m3 / timestep_sec  # m³/s
    return flow_cms


def read_watershed_area(template_case: str) -> float:
    """Read total watershed area from parameter file.
    
    Args:
        template_case: Name of template case (e.g., 'drsw1')
        
    Returns:
        Total watershed area in square kilometers
    """
    # Look for parameter file in template case
    param_dir = TEST_CASES_PATH / template_case / "input" / "params"
    param_files = list(param_dir.glob("sac_params.*.txt"))
    
    if not param_files:
        raise FileNotFoundError(f"No parameter file found in {param_dir}")
    
    param_file = param_files[0]
    
    with open(param_file, 'r') as f:
        lines = f.readlines()
    
    # Find hru_area line (should be second line)
    for line in lines:
        if line.strip().startswith('hru_area'):
            areas = [float(x) for x in line.split()[1:]]
            return sum(areas)
    
    raise ValueError(f"Could not find hru_area in {param_file}")


def read_hru_output_file(branch: str, template_case: str, hru_num: int) -> pd.DataFrame:
    """Read the output file for a specific HRU.
    
    Args:
        branch: Branch name
        template_case: Template case name
        hru_num: HRU number (1-based)
        
    Returns:
        DataFrame with HRU output data
    """
    test_case_path = get_test_case_path(branch, template_case)
    output_dir = test_case_path / "output"
    
    # Auto-detect HRU output file
    output_files = list(output_dir.glob(f"output.sacbmi.*-{hru_num}.txt"))
    if not output_files:
        raise FileNotFoundError(f"No HRU-{hru_num} output files found in {output_dir}")
    
    # Read with high precision
    return pd.read_csv(output_files[0], sep=r'\s+', float_precision='round_trip')


def compare_tci_to_infw(config: dict, data: Dict[str, pd.DataFrame]):
    """Compare TCI from each branch to INFW reference data for total and individual HRUs.
    
    Args:
        config: Configuration dictionary
        data: Dictionary of branch name to DataFrame
    """
    template_case = config['template_case']
    plot_titles = config.get('plot_titles', {})
    
    # Create output directory
    plot_dir = REPO_PATH / "tests" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate number of branches with TCI data
    branches_with_tci = [b for b, df in data.items() if 'tci' in df.columns]
    n_branches = len(branches_with_tci)
    
    if n_branches == 0:
        print("  No branches with TCI data found")
        return
    
    # Check for HRU files
    hru_files = []
    for hru_num in [1, 2]:
        infw_file = TEST_CASES_PATH / template_case / "output" / f"INFW_{template_case.upper()}-{hru_num}.csv"
        if infw_file.exists():
            hru_files.append((hru_num, infw_file))
    
    # Determine grid layout: total + HRUs
    n_plots = 1 + len(hru_files)  # Total + individual HRUs
    
    # Process total watershed first - try multiple file names
    infw_file_total = TEST_CASES_PATH / template_case / "output" / f"INFW_{template_case.upper()}.csv"
    if not infw_file_total.exists():
        # Try alternative name: INFW_weighted_avg.csv
        infw_file_total = TEST_CASES_PATH / template_case / "output" / "INFW_weighted_avg.csv"
    if infw_file_total.exists():
        print(f"\nComparing TCI to INFW reference data...")
        infw_df_total = pd.read_csv(infw_file_total)
        
        # Create figure with one row per plot type (total, HRU1, HRU2)
        fig, axes = plt.subplots(n_plots, n_branches, figsize=(6 * n_branches, 5 * n_plots))
        
        # Handle single branch or single plot case
        if n_branches == 1 and n_plots == 1:
            axes = np.array([[axes]])
        elif n_branches == 1:
            axes = axes.reshape(-1, 1)
        elif n_plots == 1:
            axes = axes.reshape(1, -1)
        
        # Plot total watershed comparison (row 0)
        for idx, branch in enumerate(branches_with_tci):
            ax = axes[0, idx]
            df = data[branch]
            
            # Get TCI in mm (same units as INFW)
            tci_values_mm = df['tci'].values
            
            # Align data by timestep (assuming same length and order)
            min_len = min(len(tci_values_mm), len(infw_df_total))
            tci_values = tci_values_mm[:min_len]
            infw_values = infw_df_total['infw_mm_per_6hr'].values[:min_len]
            
            # Calculate R²
            slope, intercept, r_value, p_value, std_err = stats.linregress(infw_values, tci_values)
            r2 = r_value ** 2
            
            # Calculate other metrics
            mae = np.mean(np.abs(tci_values - infw_values))
            rmse = np.sqrt(np.mean((tci_values - infw_values) ** 2))
            bias = np.mean(tci_values - infw_values)
            
            # Scatter plot
            ax.scatter(infw_values, tci_values, alpha=0.3, s=5, color='steelblue')
            
            # 1:1 line
            max_val = max(infw_values.max(), tci_values.max())
            min_val = min(infw_values.min(), tci_values.min())
            ax.plot([min_val, max_val], [min_val, max_val], 'k--', 
                   linewidth=1.5, label='1:1 Line')
            
            # Regression line
            x_line = np.array([min_val, max_val])
            y_line = slope * x_line + intercept
            ax.plot(x_line, y_line, 'r-', linewidth=1.5, alpha=0.7,
                   label=f'Fit: y={slope:.3f}x+{intercept:.3f}')
            
            # Labels and title
            plot_title = get_plot_title(branch, plot_titles)
            ax.set_xlabel('CHPS INFW [mm/6hr]', fontsize=11)
            ax.set_ylabel('SAC-SMA TCI [mm/6hr]', fontsize=11)
            ax.set_title(f'{plot_title} - TCI vs INFW', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left', fontsize=9)
            
            # Add statistics text box
            stats_text = (
                f'R² = {r2:.4f}\n'
                f'MAE = {mae:.4f} mm\n'
                f'RMSE = {rmse:.4f} mm\n'
                f'Bias = {bias:.4f} mm\n'
                f'n = {min_len}'
            )
            ax.text(0.98, 0.02, stats_text,
                   transform=ax.transAxes,
                   verticalalignment='bottom',
                   horizontalalignment='right',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                   fontsize=9, family='monospace')
            
            print(f"  Total {plot_title}: R² = {r2:.4f}, RMSE = {rmse:.4f} mm")
        
        # Plot HRU comparisons (subsequent rows)
        for plot_idx, (hru_num, infw_file_hru) in enumerate(hru_files, start=1):
            print(f"\n  Processing HRU-{hru_num}...")
            infw_df_hru = pd.read_csv(infw_file_hru)
            
            for idx, branch in enumerate(branches_with_tci):
                ax = axes[plot_idx, idx]
                
                try:
                    # Read HRU-specific output
                    df_hru = read_hru_output_file(branch, template_case, hru_num)
                    
                    # Get TCI in mm (same units as INFW)
                    tci_values_mm = df_hru['tci'].values
                    
                    # Align data by timestep
                    min_len = min(len(tci_values_mm), len(infw_df_hru))
                    tci_values = tci_values_mm[:min_len]
                    infw_values = infw_df_hru['infw_mm_per_6hr'].values[:min_len]
                    
                    # Calculate R²
                    slope, intercept, r_value, p_value, std_err = stats.linregress(infw_values, tci_values)
                    r2 = r_value ** 2
                    
                    # Calculate other metrics
                    mae = np.mean(np.abs(tci_values - infw_values))
                    rmse = np.sqrt(np.mean((tci_values - infw_values) ** 2))
                    bias = np.mean(tci_values - infw_values)
                    
                    # Scatter plot
                    ax.scatter(infw_values, tci_values, alpha=0.3, s=5, color='coral')
                    
                    # 1:1 line
                    max_val = max(infw_values.max(), tci_values.max())
                    min_val = min(infw_values.min(), tci_values.min())
                    ax.plot([min_val, max_val], [min_val, max_val], 'k--', 
                           linewidth=1.5, label='1:1 Line')
                    
                    # Regression line
                    x_line = np.array([min_val, max_val])
                    y_line = slope * x_line + intercept
                    ax.plot(x_line, y_line, 'r-', linewidth=1.5, alpha=0.7,
                           label=f'Fit: y={slope:.3f}x+{intercept:.3f}')
                    
                    # Labels and title
                    plot_title = get_plot_title(branch, plot_titles)
                    ax.set_xlabel('CHPS INFW [mm/6hr]', fontsize=11)
                    ax.set_ylabel('SAC-SMA TCI [mm/6hr]', fontsize=11)
                    ax.set_title(f'{plot_title} - HRU{hru_num} TCI vs INFW', fontsize=12, fontweight='bold')
                    ax.grid(True, alpha=0.3)
                    ax.legend(loc='upper left', fontsize=9)
                    
                    # Add statistics text box
                    stats_text = (
                        f'R² = {r2:.4f}\n'
                        f'MAE = {mae:.4f} mm\n'
                        f'RMSE = {rmse:.4f} mm\n'
                        f'Bias = {bias:.4f} mm\n'
                        f'n = {min_len}'
                    )
                    ax.text(0.98, 0.02, stats_text,
                           transform=ax.transAxes,
                           verticalalignment='bottom',
                           horizontalalignment='right',
                           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                           fontsize=9, family='monospace')
                    
                    print(f"    HRU-{hru_num} {plot_title}: R² = {r2:.4f}, RMSE = {rmse:.4f} mm")
                    
                except FileNotFoundError as e:
                    print(f"    Warning: {e}")
                    ax.text(0.5, 0.5, f'HRU-{hru_num} data\nnot available',
                           transform=ax.transAxes,
                           ha='center', va='center', fontsize=12)
                    ax.set_xlabel('CHPS INFW [mm/6hr]', fontsize=11)
                    ax.set_ylabel('SAC-SMA TCI [mm/6hr]', fontsize=11)
                    plot_title = get_plot_title(branch, plot_titles)
                    ax.set_title(f'{plot_title} - HRU{hru_num} TCI vs INFW', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        
        # Save plot
        plot_path = plot_dir / f"tci_vs_infw_{template_case}.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"\nTCI vs INFW comparison saved to: {plot_path.relative_to(REPO_PATH)}")
    else:
        print(f"\nINFW file not found: {infw_file_total} - skipping TCI comparison")




def generate_state_boxplots(config: dict, state_data: Dict[str, pd.DataFrame]):
    """Generate boxplot comparisons for state variables."""
    if len(state_data) == 0:
        print("No state data available for comparison")
        return
    
    # Create output directory
    plot_dir = REPO_PATH / "tests" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    # Get variables to plot (exclude datehr)
    variables = get_numeric_columns(state_data)
    variables = [v for v in variables if v != 'datehr']
    
    plot_titles = config.get('plot_titles', {})
    template_case = config['template_case']
    
    # Output PDF path
    pdf_path = plot_dir / f"boxplots_states_{template_case}.pdf"
    
    success_count = 0
    
    # Create multi-page PDF
    with PdfPages(pdf_path) as pdf:
        for variable in variables:
            if create_boxplot_comparison(state_data, variable, plot_titles, pdf):
                success_count += 1
    
    print(f"Generated {success_count} state variable boxplots: {pdf_path.relative_to(REPO_PATH)}")


def generate_tci_1to1_plots(config: dict, data: Dict[str, pd.DataFrame]):
    """Generate 1:1 scatter plots comparing TCI between branches.
    
    Args:
        config: Configuration dictionary
        data: Dictionary of branch name to DataFrame
    """
    # Filter branches that have TCI data
    branches_with_tci = [b for b, df in data.items() if 'tci' in df.columns]
    
    if len(branches_with_tci) < 2:
        print("Need at least 2 branches with TCI data for 1:1 comparisons")
        return
    
    from matplotlib.ticker import FuncFormatter
    
    plot_dir = REPO_PATH / "tests" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    plot_titles = config.get('plot_titles', {})
    template_case = config['template_case']
    
    # Get watershed area for unit conversion if available
    try:
        area_km2 = read_watershed_area(template_case)
        timestep_sec = 21600  # 6 hours
        use_cms = True
        units = 'm³/s'
    except Exception as e:
        print(f"Warning: Could not read watershed area, using mm units: {e}")
        use_cms = False
        units = 'mm'
    
    # Use first branch as reference
    ref_branch = branches_with_tci[0]
    ref_title = get_plot_title(ref_branch, plot_titles)
    
    # Compare all other branches to the reference
    compare_branches = branches_with_tci[1:]
    n_compare = len(compare_branches)
    
    # Create figure with subplots for each comparison
    fig, axes = plt.subplots(1, n_compare, figsize=(6 * n_compare, 5))
    if n_compare == 1:
        axes = [axes]
    
    fig.suptitle(f'TCI 1:1 Comparison vs {ref_title}', 
                fontsize=14, fontweight='bold', y=1.02)
    
    # Get reference data
    ref_data = data[ref_branch]['tci'].values
    if use_cms:
        ref_data = np.array([convert_tci_to_cms(x, area_km2, timestep_sec) for x in ref_data])
    
    for idx, comp_branch in enumerate(compare_branches):
        ax = axes[idx]
        comp_title = get_plot_title(comp_branch, plot_titles)
        comp_data = data[comp_branch]['tci'].values
        
        if use_cms:
            comp_data = np.array([convert_tci_to_cms(x, area_km2, timestep_sec) for x in comp_data])
        
        # Ensure same length
        min_len = min(len(ref_data), len(comp_data))
        ref_subset = ref_data[:min_len]
        comp_subset = comp_data[:min_len]
        
        # Scatter plot
        ax.scatter(ref_subset, comp_subset, alpha=0.3, s=5, color='steelblue')
        
        # 1:1 line
        all_values = np.concatenate([ref_subset, comp_subset])
        min_val = np.min(all_values)
        max_val = np.max(all_values)
        
        ax.plot([min_val, max_val], [min_val, max_val], 'k--', 
               linewidth=1.5, label='1:1 Line')
        
        # Calculate statistics
        diff = comp_subset - ref_subset
        mae = np.mean(np.abs(diff))
        rmse = np.sqrt(np.mean(diff ** 2))
        max_abs_diff = np.max(np.abs(diff))
        
        # Pearson correlation
        if np.std(ref_subset) > 0 and np.std(comp_subset) > 0:
            corr = np.corrcoef(ref_subset, comp_subset)[0, 1]
        else:
            corr = 1.0 if np.allclose(ref_subset, comp_subset) else 0.0
        
        # Calculate R² using linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(ref_subset, comp_subset)
        r2 = r_value ** 2
        
        # Plot regression line
        x_line = np.array([min_val, max_val])
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, 'r-', linewidth=1.5, alpha=0.5,
               label=f'Fit: y={slope:.3f}x+{intercept:.2f}')
        
        # Labels
        ax.set_xlabel(f'{ref_title} TCI ({units})', fontsize=11)
        ax.set_ylabel(f'{comp_title} TCI ({units})', fontsize=11)
        ax.set_title(comp_title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        
        # Add statistics text box
        stats_text = (
            f'R² = {r2:.6f}\n'
            f'R = {corr:.6f}\n'
            f'MAE = {mae:.4f} {units}\n'
            f'RMSE = {rmse:.4f} {units}\n'
            f'Max |Δ| = {max_abs_diff:.4f} {units}\n'
            f'n = {min_len}'
        )
        ax.text(0.98, 0.02, stats_text,
               transform=ax.transAxes,
               verticalalignment='bottom',
               horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
               fontsize=9, family='monospace')
        
        # Equal aspect ratio for 1:1 comparison
        ax.set_aspect('equal', adjustable='box')
    
    plt.tight_layout()
    
    # Save plot
    plot_path = plot_dir / f"tci_1to1_{template_case}.png"
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"TCI 1:1 plots: {plot_path.relative_to(REPO_PATH)}")


def generate_state_1to1_plots(config: dict, state_data: Dict[str, pd.DataFrame]):
    """Generate 1:1 scatter plots comparing state variables between branches.
    
    All state variable comparisons are saved to a single PDF file.
    """
    if len(state_data) < 2:
        print("Need at least 2 branches for 1:1 state comparisons")
        return
    
    from matplotlib.ticker import FuncFormatter
    
    # Create output directory
    plot_dir = REPO_PATH / "tests" / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    # Get variables to plot (exclude datehr)
    variables = get_numeric_columns(state_data)
    variables = [v for v in variables if v != 'datehr']
    
    plot_titles = config.get('plot_titles', {})
    template_case = config['template_case']
    branches = list(state_data.keys())
    
    # Use first branch as reference
    ref_branch = branches[0]
    ref_title = get_plot_title(ref_branch, plot_titles)
    
    # Compare all other branches to the reference
    compare_branches = branches[1:]
    
    # Create PDF file for all state 1:1 plots
    output_file = plot_dir / f"state_1to1_{template_case}.pdf"
    
    with PdfPages(output_file) as pdf:
        # Custom formatter for scientific notation
        def sci_formatter(x, pos):
            if x == 0:
                return '0'
            else:
                exp = int(np.floor(np.log10(abs(x))))
                coeff = x / 10**exp
                if abs(coeff - 1.0) < 0.01:
                    return f'$10^{{{exp}}}$'
                else:
                    return f'${coeff:.1f}\\times10^{{{exp}}}$'
        
        for variable in variables:
            n_compare = len(compare_branches)
            
            # Create figure with subplots for each comparison
            fig, axes = plt.subplots(1, n_compare, figsize=(6 * n_compare, 5))
            if n_compare == 1:
                axes = [axes]
            
            fig.suptitle(f'{variable} - 1:1 Comparison vs {ref_title}', 
                        fontsize=14, fontweight='bold', y=1.02)
            
            ref_data = state_data[ref_branch][variable].values
            
            for idx, comp_branch in enumerate(compare_branches):
                ax = axes[idx]
                comp_title = get_plot_title(comp_branch, plot_titles)
                comp_data = state_data[comp_branch][variable].values
                
                # Ensure same length
                min_len = min(len(ref_data), len(comp_data))
                ref_subset = ref_data[:min_len]
                comp_subset = comp_data[:min_len]
                
                # Scatter plot
                ax.scatter(ref_subset, comp_subset, alpha=0.3, s=5, color='steelblue')
                
                # 1:1 line
                all_values = np.concatenate([ref_subset, comp_subset])
                min_val = np.min(all_values)
                max_val = np.max(all_values)
                
                ax.plot([min_val, max_val], [min_val, max_val], 'k--', 
                       linewidth=1.5, label='1:1 Line')
                
                # Calculate statistics
                diff = comp_subset - ref_subset
                mae = np.mean(np.abs(diff))
                rmse = np.sqrt(np.mean(diff ** 2))
                max_abs_diff = np.max(np.abs(diff))
                
                # Pearson correlation
                if np.std(ref_subset) > 0 and np.std(comp_subset) > 0:
                    corr = np.corrcoef(ref_subset, comp_subset)[0, 1]
                else:
                    corr = 1.0 if np.allclose(ref_subset, comp_subset) else 0.0
                
                # Labels
                ax.set_xlabel(f'{ref_title} ({variable})', fontsize=11)
                ax.set_ylabel(f'{comp_title} ({variable})', fontsize=11)
                ax.set_title(comp_title, fontsize=12, fontweight='bold')
                ax.grid(True, alpha=0.3)
                ax.legend(loc='upper left')
                
                # Add statistics text box
                stats_text = (
                    f'R = {corr:.6f}\n'
                    f'MAE = {mae:.2e}\n'
                    f'RMSE = {rmse:.2e}\n'
                    f'Max |Δ| = {max_abs_diff:.2e}\n'
                    f'n = {min_len}'
                )
                ax.text(0.98, 0.02, stats_text,
                       transform=ax.transAxes,
                       verticalalignment='bottom',
                       horizontalalignment='right',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                       fontsize=9, family='monospace')
                
                # Equal aspect ratio for 1:1 comparison
                ax.set_aspect('equal', adjustable='box')
            
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
    
    print(f"State 1:1 plots saved to: {output_file.relative_to(REPO_PATH)}")


def main():
    """Main entry point."""
    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"ERROR: {e}")
        return 1
    
    # Load data from all branches
    data = load_all_branch_data(config)
    
    if len(data) < 2:
        print("ERROR: Need at least 2 branches with output data")
        return 1
    
    # Generate output visualizations
    generate_all_boxplots(config, data)
    generate_mass_balance_timeseries(config, data)
    generate_mass_balance_combined_logscale(config, data)
    generate_tci_1to1_plots(config, data)
    generate_summary_statistics(config, data)
    compare_tci_to_infw(config, data)
    
    # Load and visualize state data
    print("\nLoading state data...")
    state_data = load_all_branch_states(config)
    if len(state_data) >= 2:
        generate_state_boxplots(config, state_data)
        generate_state_1to1_plots(config, state_data)
    else:
        print("Skipping state visualizations (need at least 2 branches with state data)")
    
    return 0


if __name__ == "__main__":
    exit(main())
