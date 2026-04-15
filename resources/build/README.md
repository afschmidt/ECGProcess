# Package management

Documentation on version numbering and the release workflow.
Throughout this section `./` indicates the root of the repository.

## Versioning

This package uses 3-level semantic versioning:

1. **Major** version number
2. **Minor** version number
3. **Patch** version number

For example: `0.1.0`, `1.0.0`, `1.2.3`.

[`bump2version`](https://github.com/c4urself/bump2version) is used to
increment version numbers across the package. The configuration lives in
`./.bumpversion.cfg` and updates the following files:

* `./VERSION`
* `./{{PKG}}/_version.py`
* `./pyproject.toml`
* `./docs/source/conf.py`
* `./README.md`
* `./CHANGELOG.md` — replaces `[Unreleased]` with the new version number

## Release workflow

The `inc_version.sh` script in this directory wraps `bump2version` with:

1. A dry-run preview of the version change
2. User confirmation before proceeding
3. Automatic date insertion in `CHANGELOG.md` (e.g. `### [0.1.0] - 2026-04-05`)
4. A fresh `### [Unreleased]` section added to the top of the changelog
5. Amended commit and re-tagged to include the changelog changes
6. Push to remote with tags

### Usage

From this directory (`resources/build`):

```bash
bash inc_version.sh patch    # 0.0.0 -> 0.0.1
bash inc_version.sh minor    # 0.0.0 -> 0.1.0
bash inc_version.sh major    # 0.0.0 -> 1.0.0
```

### Jump to a specific version

First a dry-run:
```bash
cd ../../
bump2version -n --verbose --new-version 0.1.0 patch
```

Remove `-n` to apply for real.
