![Schematic](https://ecgprocess-schmidtaf-f9abe0f74d20c469a1e6cca62c7f636ef6bf6b9ffe.gitlab.io/_static/ECGProcessSchematic.png)

# An ECG processing module
__version__: `1.0.0`


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
`./resources/conda/envs/`.
A new conda environment called `ecgprocess` can be built using the command:

```sh
# From the root of the repository
conda env create --file ./resources/conda/envs/conda_create.yaml
```

To add to an existing environment use:

```sh
# From the root of the repository
conda env update --file ./resources/conda/envs/conda_update.yaml
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

