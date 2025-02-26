## Install Daisy in dev mode
This document aims to set up a poetry project to install Daisy in dev mode. For users who only need algorithm development, please refer to the [user mode installation](./user_mode.md).


### 1. Clone Daisy repository
```
git clone https://github.com/Intelligent-Systems-Lab/daisy
```


### 2. Build up virtual environment
To set up the poetry project, using a virtual environment is necessary. The method for creating the virtual environment is not limited to common tools such as `venv` or `conda`. Please prepare and `activate` your virtual environment (with `python=3.8^`).


### 3. Install poetry project
Change to the Daisy directory and execute `dev/bootstrap.sh` to install the poetry project.
```
cd daisy
./dev/bootstrap.sh
```
After installing the poetry project, the daisyfl package in the virtual environment will reference `src/py/daisyfl` in the local repository.

