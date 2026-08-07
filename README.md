![Schematic](https://SchmidtAF.gitlab.io/ECGProcess/_static/ecgp_logo.png)

# An ECG processing module
__version__: `1.1.0`

Supports Python 3.11-3.13; the test suite runs against all three versions
in CI.


This repository hosts a collection of functions for processing
electrocardiogram (ECG) data and preparing it for analysis.

At a glance, ECGProcess is driven by three units:

* A **processor** unit, reads individual ECG files and based on 
  a user-supplied configuration file extracts waveform
  signals, median beats, and metadata to python dictionaries; see [Configuration files](https://SchmidtAF.gitlab.io/ECGProcess/configuration_files.html)).
* The **table** unit, `ECGTable`, loops over a directory of ECG files, 
  calls the reader for each one, while applying optional engineering steps
  (e.g. resampling, calibration, lead correction), and again optionally 
  concatenating multiple files together.
* A **writer** unit, tells `ECGTable` what to write to disk
  (tables, NumPy arrays, WFDB records, images, ...). 

Together these units implement an application programming interface (API),
mapping ECG data from distinct file types to class attributes
providing a fixed interface for downstream processing. 
The package ships with boilerplate classes and validation utilities,
letting the user expand **processing** of additional file types,
build custom **engineering** (e.g. standardisation) pipelines, as well as 
create custom **writers**.

Please consult the [documentation](https://SchmidtAF.gitlab.io/ECGProcess/)
for the full picture.

## Installation 
The package is available on PyPI, and conda, with the latest source code 
available on gitlab. 

### Installation using PyPI

To install the package from PyPI, run:

```bash
pip install ecgprocess
```

This installs the latest stable release along with its dependencies.

### Installation using conda

A Conda package is maintained in my personal Conda channel.
To install from this channel, run:

```bash
conda install afschmidt::ecgprocess
```

### Installation using gitlab

If you require the latest updates, potentially not yet formally released,
you can install the package directly from GitLab.

First, clone the repository and move into its root directory:

```bash
git clone git@gitlab.com:SchmidtAF/ecgprocess.git
cd ecgprocess
```

Install the dependencies:

```bash
# From the root of the repository
conda env create --file ./resources/conda/envs/conda_create.yaml
```

To add to an existing environment use:

```bash
# From the root of the repository
conda env update --file ./resources/conda/envs/conda_update.yaml
```

Next the package can be installed: 

```bash
make install
```

#### Development
For development work, install the package in editable mode, with its
development dependencies (`pytest`, `codespell`, `sphinx`, ...) and Git
commit hooks configured:

```bash
make install-dev
```

This command installs the package in editable mode with the `[dev]`
extras and configures Git commit hooks, allowing you to run `git pull`
to update the repository or switch branches without reinstalling.

Alternatively, you can install manually. This is exactly equivalent
to `make install-dev`:

```bash
python -m pip install -e ".[dev]"
python .githooks/.setup_git_hooks.py
```

#### Git Hooks Configuration


When setting up a development environment, the `setup-hooks` command 
configures Git hooks to enforce conventional commit message formatting and 
spell check using `codespell`.

To view the commit message format requirements, run:

```bash
./.githooks/commit-msg -help
```

For frequent use, add this function to your shell configuration (`~/.bashrc` 
or `~/.zshrc`):

```bash
commit-format-help() {
    local git_root
    git_root=$(git rev-parse --show-toplevel 2>/dev/null)
    
    if [ -z "$git_root" ]; then
        echo "Error: Not inside a git repository"
        return 1
    fi
    
    local hook_path="$git_root/.githooks/commit-msg"
    
    if [ ! -f "$hook_path" ]; then
        echo "Error: commit-msg hook not found"
        return 1
    fi
    
    "$hook_path" --help
}
```

## Next steps...
If you installed with `make install-dev`, you might wish to run `pytest` to 
confirm everything is in working order. 

```sh
# From the root of the repository
pytest tests
```

## Usage

Please have a look at the [example](https://SchmidtAF.gitlab.io/ECGProcess/examples.html)
 recipes. 
