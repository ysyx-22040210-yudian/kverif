@echo off
if defined PYTHON (
  "%PYTHON%" "%~dp0fake_kdebug.py" %*
) else (
  python "%~dp0fake_kdebug.py" %*
)
