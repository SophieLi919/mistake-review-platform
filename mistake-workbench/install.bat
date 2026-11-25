@echo off
chcp 65001 >nul
setlocal
set "SRC=%~dp0"
set "NAME=mistake-workbench"
set "DONE=0"
for %%B in ("%USERPROFILE%\.claude\skills" "%USERPROFILE%\.codex\skills" "%USERPROFILE%\.workbuddy\skills" "%USERPROFILE%\.agents\skills") do (
  if exist %%B (
    if exist "%%~B\%NAME%" rmdir /s /q "%%~B\%NAME%"
    xcopy "%SRC%" "%%~B\%NAME%\" /e /i /q /y >nul
    if exist "%%~B\%NAME%\.git" rmdir /s /q "%%~B\%NAME%\.git"
    echo 已安装到 %%~B\%NAME%
    set "DONE=1"
  )
)
if "%DONE%"=="0" (
  xcopy "%SRC%" "%USERPROFILE%\.claude\skills\%NAME%\" /e /i /q /y >nul
  echo 没找到已有的 Skill 目录，已装到 %USERPROFILE%\.claude\skills\%NAME%
)
echo.
echo 装好了。打开你的 AI（Claude Code / Codex / WorkBuddy），选中一个空文件夹，说：错题工作台，帮我分析这套卷子
pause
