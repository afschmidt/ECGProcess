# `docker` directory
This contains build files to build a docker image that can be used for 
gitlab CI/CD for this repo.
These images are not docker images containing the actual python package.

If needed a new docker file can be build from scratch running 

```sh
./build.sh
```

Where the image can be pushed to docker hub as follows:

```sh
docker image list
sudo docker push docker.io/floriaan1/ecgprocess:master
```

Docker can be removed using `please docker image prune -a`, 
where an existing docker can be pulled from docker hub by 
running

```sh
sudo docker pull floriaan1/ecgprocess:master
```
