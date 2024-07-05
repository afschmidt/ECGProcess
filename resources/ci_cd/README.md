# Continuous integration scripts
This allows the testing of various continuous integration scripts before committing to GitLab.
It is a major pain in the backside to debug against that so it is easier to do a test run before setting it up.

The various `run_<pipeline>.sh` scripts represent different scripts that can be run on different pipelines.
The other scripts represent small sections that can be run in a pipeline.

Specifically:

- **run_docker**: mimics the `.gitlab_ci.yaml` functionality and runs the docker locally. 
 This can be used to debug CI/CD gitlab builds without repeated commits.  
 This will create a container called and do the build before closing and removing the container. 
 The container will also be removed on error.
- **run_pages**:  A script to initialise the dock building within the docker container.
 This is designed to for local tests of gitlab CI/CD scripts inside the docker container. 
 The script will source before_script.sh and pages.sh
- **set_ssh_key**: This will set the ssh keys needed to install private gitlab repos during 
 CI/CD on gitlab. 
 For this you will need to have included a private ssh key as a CI/CD variable to the private repo
 you want to install and activated the matching public key as a `deployed` key on the repo you 
 are doing the CI/CD for, please see the [documentation](https://docs.gitlab.com/ee/ci/ssh_keys/).
- **before_script**: The before script is used by gitlab CI/CD and used to set any commands necessary 
- before running the script commands. Here it mostly installs the required python packages, as well 
as the package being evaluated `merit_helper`.
It also runs all the pytests for `merit_helper`.
Essentially after this scripts completes, the package install has been verified.
- **pages**: Run the sphinx documentation and ensures these are published as static webpages within 
gitlab.

To run a test build prior to committing:

```
# ./run_docker.sh <docker image> <repo root> <doc build dir>
./run_docker.sh floriaan1/merit:master ~/google_drive/Research/merit /path/to/doc/build/directory
```

**debug_run_docker.sh** wraps the above code in a executable shell script. 

Other options for the docker image are (build by Chris Finan)
`chrisfin/pypan:complete`
`chrisfin/pypan:data_sci`
`chrisfin/pypan:base`
`chrisfin/bio_misc:build`
`chrisfin/merit:master`
`chrisfin/skyline:build`
