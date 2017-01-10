C:\Python27\Scripts\pip.exe install pylint

C:\Python27\Scripts\pylint.exe -E --disable=inherit-non-class --disable=no-member --ignored-modules=distutils --enable=unused-import --enable=bad-whitespace --enable=line-too-long lbrynet packaging/app/win32/LBRYWin32App.py
if ($LastExitCode -ne 0) { $host.SetShouldExit($LastExitCode)  }