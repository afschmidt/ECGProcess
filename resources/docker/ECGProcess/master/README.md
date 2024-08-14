# `docker` directory
This contains build files to build a docker image that can be used for 
gitlab CI/CD for this repo.
These images are not docker images containing the actual python package.

If needed a new docker file can be build from scratch running 

```sh
./build.sh
```

Where the image can be pushed to docker hub as follows

```sh
docker image list
sudo docker push docker.io/<USERNAME>/ecgprocess:master
```

Unused Docker image's can be removed using `sudo docker image prune -a`, 
or by docker image id `sudo docker rmi ade67f3b8eaf`.

An existing docker can be pulled from docker hub by 
running

```sh
sudo docker pull floriaan1/merit:master
```
