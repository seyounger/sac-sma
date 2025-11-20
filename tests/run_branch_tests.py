#!/usr/bin/env python3
"""
Automated test runner for comparing SAC-SMA branch outputs in standalone mode.

Switches to each branch, rebuilds the model, runs with template data,
and saves outputs in branch-specific directories.
"""

import subprocess
import shutil
from pathlib import Path
import sys
import yaml


class BranchTestRunner:
    """Test runner for different SAC-SMA branches."""
    
    def __init__(self, repo_path: str, template_case: str, branches: list):
        self.repo_path = Path(repo_path).resolve()
        self.template_case = template_case
        self.template_path = self.repo_path / "test_cases" / template_case
        self.build_path = self.repo_path / "build"
        self.bin_path = self.repo_path / "bin"
        self.branches = branches
        
        if not self.template_path.exists():
            raise ValueError(f"Template case does not exist: {self.template_path}")
    
    def run_command(self, cmd: list, cwd: Path = None, env: dict = None) -> bool:
        """Run command and return success status."""
        result = subprocess.run(cmd, cwd=cwd or self.repo_path, 
                              capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            print(f"ERROR: Command failed: {' '.join(cmd)}")
            print(f"  Exit code: {result.returncode}")
            if result.stderr:
                print(f"  {result.stderr[:200]}")
        
        return result.returncode == 0
    
    def setup_test_case(self, branch: str) -> Path:
        """Set up branch-specific test case directory from template."""
        test_case_name = f"{self.template_case}_{branch.replace('/', '_')}"
        test_case_path = self.repo_path / "test_cases" / test_case_name
        
        # Remove and recreate
        if test_case_path.exists():
            shutil.rmtree(test_case_path)
        shutil.copytree(self.template_path, test_case_path)
        
        # Clear output and state directories
        for dir_name in ["output", "state"]:
            dir_path = test_case_path / dir_name
            if dir_path.exists():
                for file in dir_path.glob("*"):
                    if file.is_file():
                        file.unlink()
        
        return test_case_path
    
    def run_model(self, test_case_path: Path) -> bool:
        """Run the SAC-SMA model for a test case."""
        run_dir = test_case_path / "run"
        
        # Find namelist file
        namelist_files = list(run_dir.glob("namelist.bmi.*"))
        if not namelist_files:
            print(f"ERROR: No namelist.bmi.* file found in {run_dir}")
            return False
        
        exe_path = self.bin_path / "sac.exe"
        return self.run_command([str(exe_path.resolve()), namelist_files[0].name], cwd=run_dir)
    
    def run_test_for_branch(self, branch: str) -> bool:
        """Run complete test for a single branch."""
        print(f"Testing: {branch}...", end=" ", flush=True)
        
        # Set up environment with FC=gfortran for make commands
        # This is needed because some branches (e.g., origin/RCode) have Makefiles
        # that use implicit make rules which default to 'f77' compiler if FC is not set.
        import os
        make_env = os.environ.copy()
        make_env['FC'] = 'gfortran'
        
        # Checkout
        if not self.run_command(["git", "checkout", branch]):
            print("FAILED (checkout)")
            return False
        
        # Build
        if not (self.run_command(["make", "clean"], cwd=self.build_path, env=make_env) and
                self.run_command(["make"], cwd=self.build_path, env=make_env) and
                (self.bin_path / "sac.exe").exists()):
            print("FAILED (build)")
            return False
        
        # Setup test case
        test_case_path = self.setup_test_case(branch)
        if not test_case_path:
            print("FAILED (setup)")
            return False
        
        # Run model
        if not self.run_model(test_case_path):
            print("FAILED (run)")
            return False
        
        # Verify outputs
        output_files = list((test_case_path / "output").glob("output.sacbmi.*.txt"))
        if len(output_files) == 0:
            print("FAILED (verify)")
            return False
        
        print("OK")
        return True
    
    def run_all_tests(self) -> dict:
        """Run tests for all configured branches."""
        results = {}
        
        # Remember the starting branch so we can return to it
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                              cwd=self.repo_path, capture_output=True, text=True)
        starting_branch = result.stdout.strip()
        
        print(f"Testing {len(self.branches)} branches (template: {self.template_case})")
        
        for branch in self.branches:
            try:
                results[branch] = self.run_test_for_branch(branch)
            except Exception as e:
                print(f"ERROR: {e}")
                results[branch] = False
        
        # Return to starting branch for visualization
        print(f"\nReturning to {starting_branch} branch...")
        subprocess.run(["git", "checkout", starting_branch], 
                      cwd=self.repo_path, capture_output=True)
        
        # Summary
        passed = sum(1 for s in results.values() if s)
        print(f"Results: {passed}/{len(results)} passed")
        
        return results


def load_config(config_path: Path = None) -> dict:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Validate
    required = ['template_case', 'branches']
    for field in required:
        if field not in config:
            raise ValueError(f"config.yaml must contain '{field}' field")
    
    if not isinstance(config['branches'], list) or len(config['branches']) == 0:
        raise ValueError("'branches' must be a non-empty list")
    
    return config


def main():
    """Main entry point."""
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    
    repo_path = Path(__file__).parent.parent.resolve()
    runner = BranchTestRunner(repo_path, config['template_case'], config['branches'])
    results = runner.run_all_tests()
    
    if not all(results.values()):
        sys.exit(1)
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    
    try:
        visualize_script = Path(__file__).parent / "visualize_comparisons.py"
        result = subprocess.run([sys.executable, str(visualize_script)], 
                              cwd=repo_path, capture_output=False)
        
        if result.returncode != 0:
            print("WARNING: Visualization generation failed")
        
    except Exception as e:
        print(f"WARNING: Could not generate visualizations: {e}")


if __name__ == "__main__":
    main()
