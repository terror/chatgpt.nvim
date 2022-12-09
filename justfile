default:
  just --list

all: forbid fmt-check

forbid:
  ./bin/forbid

fmt:
  isort . && yapf --in-place --recursive **/**/*.py

fmt-check:
  isort -c . && yapf --diff --recursive .

install *pkg:
  pipenv install {{pkg}} --skip-lock

install-editable:
  pipenv install -e .

lock:
  pipenv lock --pre
