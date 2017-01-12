# have to do `which trial` instead of simply trial because coverage needs the full path

if [ ${TRAVIS_OS_NAME} = "linux" ]; then
    source venv/bin/activate
fi

pip install Cython
pip install unqlite
pip install mock
pip install coveralls

coverage run --source=lbrynet `which trial` tests
coveralls