# An ECG processing module
__version__: `0.2.1`


This repository host a mixture of function dealing with processing 
electrocardiogram (ECG) data, and preparing these data for analysis.
The processing functions are intended for user defined parametrisation 
about the data which should be extracted, covering signal data such as 
waveforms or median beats, as well as metadata relevant for downstream 
QC or as tabular information. 


The documentation for ECGProcess can be found [here](https://SchmidtAF.gitlab.io/ECGProcess/). 


## Installation 
At present, the repository is undergoing development and no packages exist yet 
on PyPy or in Conda.
Therefore it is recommended that it is installed in either of the two ways
listed below.
First, clone this repository and then `cd` to the root of the repository.

```sh
git clone git@gitlab.com:SchmidtAF/ECGProcess.git
cd ECGProcess
```

### Installation using conda dependencies
A conda environment is provided in a `yaml` file in the directory 
`./resources/conda_env/`.
A new conda environment called `ecgprocess` can be built using the command:

```sh
# From the root of the repository
conda env create --file ./resources/conda_env/conda_create.yml
```

To add to an existing environment use:

```sh
# From the root of the repository
conda env update --file ./resources/conda_env/conda_update.yml
```

Next the package can be installed: 

```sh
python -m pip install .
```

Or for an editable (developer) install run the command below from the root of 
the repository.
The difference with this is that you can just to a `git pull` to 
update repository, or switch branches without re-installing:

```sh
python -m pip install -e .

```
### Installation not using any conda dependencies
If you are not using conda in any way then install the dependencies via `pip` 
and install repository as an editable install also via pip:

Install dependencies:

```sh
python -m pip install --upgrade -r requirements.txt
```

Then to install repository you can either do:

```sh
python -m pip install .
```

Or for an editable (developer) install run the command below from the root of
the repository.
The difference with this is that you can just to a `git pull` to update
repository, or switch branches without re-installing:

```sh
python -m pip install -e .
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

