# have to do `which trial` instead of simply trial because coverage needs the full path
pip install cython
pip install unqlite
pip install mock
pip install coveralls


coverage run --source=lbrynet `which trial` tests
coveralls