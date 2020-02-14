#!/bin/bash

eval "$(ssh-agent -s)" &&
ssh-add -k ~/.ssh/id_rsa &&
mkdir /var/api/lokesal-backend -p &&
cd /var/api/lokesal-backend
git checkout release
git pull

source ~/.docker-profile
echo $DOCKERHUB_PASS | docker login --username $DOCKERHUB_USER --password-stdin
docker stop lokesal-backend
docker rm lokesal-backend
docker rmi wiflash/lokesal:be-latest
docker run -d --name lokesal-backend -p 5000:5000 wiflash/lokesal:be-latest
