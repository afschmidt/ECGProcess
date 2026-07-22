![Schematic](https://ecgprocess-schmidtaf-f9abe0f74d20c469a1e6cca62c7f636ef6bf6b9ffe.gitlab.io/_static/ECGProcessSchematic.png)

# An ECG processing module
__version__: `1.1.0`


This repository host a mixture of function dealing with processing 
electrocardiogram (ECG) data, and preparing these data for analysis.
The processing functions are intended for user defined parametrisation 
(using user supplied configuration files `cnf`) about the data which 
should be extracted, covering signal data such as waveforms or
median beats, as well as metadata relevant for downstream QC or as
tabular information. 

The module implements a basic application programming interface, mapping
ECG data from distinct file types (e.g. XML or DICOM) to class attributes
providing a fixed interface for downstream analysis and interrogation. 

The documentation for ECGProcess can be found [here](https://SchmidtAF.gitlab.io/ECGProcess/). 

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
For development work, install the package in editable mode with Git commit 
hooks configured:

```bash
make install-dev
```
This command installs the package in editable mode and configures Git commit 
hooks, allowing you to run `git pull` to update the repository or switch 
branches without reinstalling.

Alternatively, you can install manually:
```bash
python -m pip install -e .
python .setup_git_hooks.py
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
After installation you might wish to try the `pytest` to confirm 
everything is in working order. 

```sh
# From the root of the repository
pytest tests
```

## Usage

Please have a look at the examples in 
[resources](https://gitlab.com/SchmidtAF/ECGProcess/-/tree/master/resources/examples)
for some possible recipes. 

### Writing a custom writer

The output format of `ECGTable.write_ecg()` can be customized by subclassing `BaseWriter` and implementing the `write()` method. Before deploying a custom writer, validate it against the contract using `WriterValidator`. See the [Custom writers](https://SchmidtAF.gitlab.io/ECGProcess/custom_writers.html) documentation for the full contract and design patterns.

