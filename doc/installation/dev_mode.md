## Install Daisy in dev mode
This document aims to set up a poetry project to install Daisy in dev mode. For users who only need algorithm development, please refer to the [user mode installation](./user_mode.md).


### 1. Clone Daisy repository
```
git clone https://github.com/Intelligent-Systems-Lab/OpenDaisy.git
cd OpenDaisy
```


### 2. Build up virtual environment
To set up the poetry project, using a virtual environment is necessary. The method for creating the virtual environment is not limited to common tools such as `venv` or `conda`. Please prepare and `activate` your virtual environment (with `python=3.8^`). Assume you already have a python3.x-venv in your environment, We provide the following scripts to help you prepare virtual environment.
```
# create venv
bash dev/venv-create.sh <3.x> .venv

# delete venv
bash dev/venv-delete.sh .venv

# reset venv
bash dev/venv-reset.sh <3.x> .venv

# activate
source .venv/bin/activate
```
You can install different python version by substitute "3.x" with your venv version.


### 3. Install poetry project
Change to the Daisy directory and execute `dev/bootstrap.sh` to install the poetry project.
```
./dev/bootstrap.sh
```
After installing the poetry project, the daisyfl package in the virtual environment will reference `src/py/daisyfl` in the local repository.


### 4. Test
We use a toolchain to make sure code quality and unify contributors' coding style.
```
bash dev/format-and-test.sh
```
Please make sure all tests passed before submit a PR.
