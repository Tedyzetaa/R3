Set WshShell = CreateObject("WScript.Shell")
Dim scriptDir
scriptDir = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
WshShell.Run Chr(34) & scriptDir & "start.bat" & Chr(34), 0, False
WshShell.Run Chr(34) & scriptDir & "iniciar_flask.bat" & Chr(34), 0, False