C:\Python27\Scripts\pip.exe install mock
C:\Python27\Scripts\pip.exe install coveralls
C:\Python27\Scripts\pip.exe install cython==0.24.1
C:\Python27\Scripts\pip.exe install unqlite==0.5.3

C:\Python27\python.exe C:\Python27\Scripts\trial.py C:\projects\lbry\tests\unit
if ($LastExitCode -ne 0) { $host.SetShouldExit($LastExitCode)  }

coverage run --source=lbrynet `which trial` tests
coveralls