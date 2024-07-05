# Package management
Here is documentation on the maintenance of the package.
This is not really geared towards end users but rather a log of how version
numbering is handled and how documentation is built and maintained.
Throughout this section `./` indicates the root of the repository.

## Versioning
dmd uses 3 level versioning:

1. Major version number
2. Minor version number
3. Patch version number

For all non-stable versions (which is all of them at present), these are
augmented with a:

* release - either `dev`, `a` (alpha), `b` (beta), `rc` (release candidate), 
 `prod` (production)
* build number, this build number is associated with a release

So, a development version number will look like `0.2.0dev0`


[`bump2version`](https://github.com/c4urself/bump2version) is used to increment
the version numbers throughout the package.
The version numbers are located in several different places:

* `./.bumpversion.cfg`
* `./README.md`
* `./setup.py`
* `./VERSION`

The bumpversion config file is shown below but is also a hidden file in the root of the repository:
```
[bumpversion]
current_version = 0.2.0dev0
commit = True
tag = True
parse = (?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(\-?(?P<release>[a-z]+)(?P<build>\d+))?
serialize = 
	{major}.{minor}.{patch}{release}{build}
	{major}.{minor}.{patch}

[bumpversion:part:release]
optional_value = prod
first_value = dev
values = 
	dev
	a
	b
	rc
	prod

[bumpversion:part:build]

[bumpversion:file:VERSION]

[bumpversion:file:./README.md]
search = __version__: `{current_version}`
replace = __version__: `{new_version}`

[bumpversion:file:./_version.py]
search = __version__ = '{current_version}'
replace = __version__ = '{new_version}'

[bumpversion:file:./setup.py]
search = VERSION = '{current_version}'
replace = VERSION = '{new_version}'

```

The procedure for incrementing the version number is as follows.
This assumes that the `patch` number is being bumped and you are located in
the root of the repository (where your `.bumpconfig.cfg` file is located):

1. run `bump2version` in "dry-run" (`-n`) mode with `--verbose` to make sure
everything is ok:

```
$ bump2version --verbose -n patch
current_version=0.2.0dev0
commit=True
tag=True
parse=(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(\-?(?P<release>[a-z]+)(?P<build>\d+))?
serialize=
{major}.{minor}.{patch}{release}{build}
{major}.{minor}.{patch}
new_version=0.2.1dev0
```

2. If it all looks good (which it does above) then run for real:

```
$ bump2version --verbose patch
current_version=0.2.0dev0
commit=True
tag=True
parse=(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(\-?(?P<release>[a-z]+)(?P<build>\d+))?
serialize=
{major}.{minor}.{patch}{release}{build}
{major}.{minor}.{patch}
new_version=0.2.1dev0
```

3. Push to git. `bump2version` will produce git tags (imagine these are 
bookmarks in your repository).
Note, to make sure these are updated in your repository you have to push with
the `--tags` flag.

```
git push --tags origin master
```

# Jump to a specific version

```sh
bump2version -n --verbose --new-version 0.0.2a0 part
```

