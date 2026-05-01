# Building and uploading to conda

## Requirements

The following packages must be installed if they are not already 
available:

```sh
conda install conda-build
conda install anaconda-client
```

### Set up an Anaconda token

If needed create an Anaconda account and set up login token 
`https://anaconda.org/<USER_NAME>/settings/access`.

Add the token to your `~/.bashrc`:

```sh
export ANACONDA_API_TOKEN=<YOUR_ACTUAL_TOKEN_HERE>
```

Finally confirm the token is found by running `anaconda whoami`. 

### Required files 

To build the package for Conda we need to ensure
there is a `meta.yaml` file which describes the 
package dependencies and Python version. 

Additionally, include a `build.sh` file detailing how the package 
should be installed.
For example, the following chunk installs the package using the 
very verbose mode.

```sh
set -ex
$PYTHON -m pip install . -vv
```

_NOTE_: include a `conda_build_config.yaml` to specify the build 
packages used, for example numpy 1.23. 

## Build the conda package locally

Ensure the package environment is active, then from the build directory run:

```sh
conda build .
```
This will build your package locally. 
The output will indicate the location; look for something like
`${HOME}/miniconda/envs/ecgprocess/conda-bld/noarch/ecgprocess-1.0.1-py_0.conda` . 

### Build the package prompting for the build number

The `build_prompt.sh` script similarly creates the conda build but 
now additionally prompts the user whether to change the build number 
in the meta.yaml file. _Note_: this will change the meta.yaml file 
so please remember to commit the updated file. 

## Upload to conda 

```sh
anaconda upload ${HOME}/miniconda/envs/ecgprocess/conda-bld/noarch/ecgprocess-1.0.1-py_0.conda 
```

If you want to automatically upload to Conda, skipping the step above, please
add `anaconda_upload: true` to your `~/.condarc`. 

