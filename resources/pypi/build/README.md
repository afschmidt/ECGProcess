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

Releases are uploaded to PyPI by GitLab, not from your own computer.
Running `bash inc_version.sh patch` (or `minor`, `major`) in
`resources/build` bumps the version and pushes a tag such as `v1.4.0`.
That tag starts a pipeline. After the tests pass, the `publish_pypi` job
builds two files: a `.tar.gz` file containing the source distribution, and
a `.whl` file representing the built distribution. It then signs both files
and uploads them.

Because GitLab does the upload, PyPI can confirm which pipeline built the
files and shows this as "provenance" on the release page. A provenance
record is a public, signed note saying "these exact files came from this
GitLab job". An upload from a laptop cannot get one.

The job uses PyPI "Trusted Publishing": PyPI accepts uploads from this
GitLab project without a password or stored token. This needs a one-time
setup on PyPI, at
https://pypi.org/manage/project/ecgprocess/settings/publishing/
(choose GitLab):

- Namespace: `SchmidtAF`
- Project name: `ECGProcess`
- Top-level pipeline file path: `.gitlab-ci.yml`
- Environment name: `pypi`

Things to know:

- Any tag of the form `vX.Y.Z` publishes, whichever branch it was made on.
  Only push such a tag when you mean to release.
- The job stops before uploading if the tag does not match the `VERSION`
  file.
- If the job fails before the upload starts, rerun it from the GitLab
  pipeline page.
- If it fails after the `.tar.gz` file is uploaded but before the `.whl`
  file, that version number is used up on PyPI. Release the next patch
  number instead.

A manual upload still works, but PyPI then marks the release "Without
provenance":

```bash
python -m build
twine upload dist/*
```

The uploaded package can be found here:
`https://pypi.org/project/ECGProcess`


