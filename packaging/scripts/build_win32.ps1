# this is a port of setup_build.sh used for the unix platforms

function AddUi {
   wget https://s3.amazonaws.com/lbry-ui/development/dist.zip -OutFile dist.zip
   if ($LastExitCode -ne 0) { $host.SetShouldExit($LastExitCode)  }

   Expand-Archive dist.zip -dest lbrynet\resources\ui
   if ($LastExitCode -ne 0) { $host.SetShouldExit($LastExitCode)  }

   wget https://s3.amazonaws.com/lbry-ui/development/data.json -OutFile lbrynet\resources\ui\data.json
   if ($LastExitCode -ne 0) { $host.SetShouldExit($LastExitCode)  }
}

function SetBuild([string]$build) {
   (Get-Content lbrynet\build_type.py).replace('dev', $build) | Set-Content lbrynet\build_type.py
   if ($LastExitCode -ne 0) { $host.SetShouldExit($LastExitCode)  }
}

If (${Env:APPVEYOR_REPO_TAG} -NotMatch "true") {
   C:\Python27\python.exe packaging\scripts\append_sha_to_version.py lbrynet\__init__.py ${Env:APPVEYOR_REPO_COMMIT}
   if ($LastExitCode -ne 0) { $host.SetShouldExit($LastExitCode) }
   
   AddUi
   SetBuild "qa"
}
ElseIf (${Env:APPVEYOR_REPO_TAG_NAME} -Match "v\d+\.\d+\.\d+rc\d+") {
   # If the tag looks like v0.7.6rc0 then this is a tagged release candidate.
   AddUi
   SetBuild "rc"
}
Else {
   SetBuild "release"
}

C:\Python27\Scripts\pip.exe install pypiwin32==219

# this is a patched to allow version numbers with non-integer values
# and it is branched off of 4.3.3
C:\Python27\Scripts\pip.exe install https://bitbucket.org/jobevers/cx_freeze/get/handle-version.tar.gz


C:\Python27\python.exe packaging\app\build_win32.py build bdist_msi
