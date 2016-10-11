testenv:
	pip install --upgrade pip wheel tox
	pip install -e .
	pip install -e .[tests]

flake8:
	flake8 post_request_task

runtests:
	coverage run --branch --source=post_request_task ./runtests.py

coveragereport:
	coverage report --omit=post_request_task/test*

test: flake8 runtests coveragereport

.PHONY: test runtests flake8 coveragereport
