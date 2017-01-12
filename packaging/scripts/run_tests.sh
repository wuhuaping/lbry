# have to do `which trial` instead of simply trial because coverage needs the full path

source venv/bin/activate

pip install Cython
pip install unqlite
pip install mock
pip install coveralls

coverage run --source=lbrynet `which trial` tests
coveralls

deactivate nondestructive
