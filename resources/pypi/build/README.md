# Publishing your package on PyPI

The Python Package Index [PyPI](https://pypi.org/) is the official repository 
for sharing and distributing Python packages.
It allows developers to publish reusable code that can be easily installed 
using tools like `pip`. 
PyPI hosts thousands of open-source projects across diverse domains,
making it a central hub for Python's software ecosystem.
By uploading a package to PyPI, you make it accessible to others via a simple 
install command, enabling collaboration, reproducibility, and standardised 
distribution. 

## Files needed for a PyPI upload

To upload a Python package to PyPI you will need the following minimal files:

- `pyproject.toml`:
  Defines build system requirements and project metadata.


- A package directory (e.g., `ECGProcess/`) in the root:
  - `__init__.py`: 
    Marks this as a Python module.

Additional recommended files:

- `README.md`: 
  Describes your project. Displayed on PyPI.

- `LICENSE`: 
  Specifies licensing terms.

- `.gitignore`, `tests/`, and CI config files (e.g., `.github/workflows/`)
  are useful for development but not required for PyPI.

## Necessary Python modules

Ensure the following modules are install: 

- **build**: Builds the package (wheel and source)
- **twine**: Uploads to PyPI
- **setuptools**: Build backend
- **wheel**: Ensures `.whl` format is available

Next, update your `pyproject.toml` to include

```sh
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

## Build and upload your package

To build the package files run the following from 
the root of your project directory (where `pyproject.toml` is located):

```bash
python -m build
```

This will generate two files: a `.tar.gz` file containing the source 
distribution, and a `.whl` file representing the built distribution. 
Modern versions of `pip` prefer wheels but fall back to source if needed, 
hence you should always upload both. 

Next to upload these files run 

```sh
twine upload dist/*
```

The uploaded package can be found here: 
`https://test.pypi.org/project/ECGProcess`


