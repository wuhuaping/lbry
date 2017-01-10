$env:Path += ";C:\MinGW\bin\"

$env:Path += ";C:\Program Files (x86)\Windows Kits\10\bin\x86\"

gcc --version

mingw32-make --version

Invoke-WebRequest "https://github.com/lbryio/lbry/raw/master/packaging/windows/libs/gmpy-1.17-cp27-none-win32.whl" -OutFile "C:\temp\gmpy-1.17-cp27-none-win32.whl"

C:\Python27\Scripts\pip.exe install "C:\temp\gmpy-1.17-cp27-none-win32.whl"

cd C:\projects\lbry

C:\Python27\Scripts\pip.exe install -r requirements.txt
