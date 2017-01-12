#! /bin/bash


if [ `uname` = "Linux" ]; then
    source venv/bin/activate
fi

pip install pylint

# Ignoring distutils because: https://github.com/PyCQA/pylint/issues/73
# TODO: as code quality improves, make pylint be more strict
pylint -E --disable=inherit-non-class --disable=no-member \
       --ignored-modules=distutils \
       --enable=unused-import \
       --enable=bad-whitespace \
       --enable=line-too-long \
       --enable=trailing-whitespace \
       --enable=missing-final-newline \
       --enable=mixed-indentation \
       lbrynet $@

if [ `uname` = "Linux" ]; then
    deactivate nondestructive
fi
