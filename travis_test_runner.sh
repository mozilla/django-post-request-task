#!/bin/bash

if [[ "$TRAVIS_PYTHON_VERSION" == "3.5" ]]; then
  if [[ "$DJANGO_VERSION" == "1.6.x" || "$DJANGO_VERSION" == "1.7.x" ]]; then
    echo "$DJANGO_VERSION is not compatible with $TRAVIS_PYTHON_VERSION so skipping the test"
    exit 0
  fi
fi

tox -e "$TRAVIS_PYTHON_VERSION-$DJANGO_VERSION"
