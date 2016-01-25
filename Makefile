DJANGO ?= "Django>=1.8,<1.9"

testenv:
	pip install -e .
	pip install --upgrade pip wheel
	pip install celery coverage $(DJANGO) flake8 mock 

flake8:
	flake8 post_request_task

runtests:
	coverage run --branch --source=post_request_task ./runtests.py

coveragereport:
	coverage report --omit=post_request_task/test*

test: flake8 runtests coveragereport

.PHONY: test runtests flake8 coveragereport
