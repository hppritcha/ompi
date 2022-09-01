#!/bin/sh

git clone git@github.com:mpi-forum/mpi-standard.git
git clone git@github.com:mpi-forum/py-mpi-standard

# To get apis.json to exist:
cd mpi-standard
make
