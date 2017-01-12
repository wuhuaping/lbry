$env:Path += ";C:\MinGW\bin\"

$env:Path += ";C:\Program Files (x86)\Windows Kits\10\bin\x86\"

gcc --version

mingw32-make --version

C:\Python27\Scripts\pip.exe install .

# If this is a build because of a tag, make sure that
# its either a testing tag or a tag that matches the version
# specified in the source code.
If (${Env:APPVEYOR_REPO_TAG} -Match "true") {
   If (${Env:APPVEYOR_REPO_TAG_NAME} -Like "test*") {
      exit 0
   }
   # non-testing tags should be in the form v1.2.3
   If ("v$(C:\Python27\python.exe setup.py -V)" -Match ${Env:APPVEYOR_REPO_TAG_NAME}) {
      exit 0
   }
   exit 1
}

mkdir C:\temp

Invoke-WebRequest "https://github.com/lbryio/lbry/raw/master/packaging/windows/libs/gmpy-1.17-cp27-none-win32.whl" -OutFile "C:\temp\gmpy-1.17-cp27-none-win32.whl"

C:\Python27\Scripts\pip.exe install "C:\temp\gmpy-1.17-cp27-none-win32.whl"

cd C:\projects\lbry

C:\Python27\Scripts\pip.exe install -r requirements.txt