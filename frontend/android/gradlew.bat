@ECHO OFF
SET DIR=%~dp0
IF NOT EXIST "%DIR%gradle\wrapper\gradle-wrapper.jar" (
  ECHO Missing gradle-wrapper.jar. Run from frontend\: flutter create . --platforms=android
  EXIT /B 1
)
java -jar "%DIR%gradle\wrapper\gradle-wrapper.jar" %*
