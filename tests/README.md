# SAC-SMA Automated Testing

## Quick Start

```bash
# Setup (first time only)
./tests/setup_testing.sh

# Run branch tests (automatically generates visualizations)
source .venv/bin/activate
python tests/run_branch_tests.py
```

To generate only visualizations (after tests have run):
```bash
python tests/visualize_comparisons.py
```

## Configuration

Edit `tests/config.yaml`:

```yaml
template_case: ex1
branches:
  - branch1
  - branch2
plot_titles:
  branch1: "Display Name 1"
  branch2: "Display Name 2"
```

## Output

### Branch Test Results
- Model outputs: `test_cases/{template}_{branch}/output/`

### Visualizations
- Boxplots: `tests/plots/boxplots_{template}.pdf` (multi-page PDF)
- Mass Balance Timeseries: `tests/plots/mass_balance_timeseries_{template}.png`
- Statistics: `tests/plots/summary_statistics_{template}.csv`
