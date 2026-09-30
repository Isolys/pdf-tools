Unicode true
!include "LogicLib.nsh"
!include "x64.nsh"
!include "WinVer.nsh"

Name "Сжать PDF"
Caption "Установка — Сжать PDF"
OutFile "release\PDF-Tools-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\PDF-Tools"
RequestExecutionLevel user
ManifestDPIAware true
SetCompressor /SOLID lzma
AutoCloseWindow true
ShowInstDetails nevershow
BrandingText "Сжать PDF — установка без лишних шагов"
Icon "assets\pdf.ico"
UninstallIcon "assets\pdf.ico"
VIProductVersion "1.1.0.0"
VIAddVersionKey /LANG=1049 "ProductName" "Сжать PDF"
VIAddVersionKey /LANG=1049 "FileDescription" "Установщик программы для сжатия PDF"
VIAddVersionKey /LANG=1049 "FileVersion" "1.1.0"
VIAddVersionKey /LANG=1049 "LegalCopyright" "PDF Tools"

Page instfiles
UninstPage uninstConfirm
UninstPage instfiles
LoadLanguageFile "${NSISDIR}\Contrib\Language files\Russian.nlf"

Function .onInit
  SetShellVarContext current
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "Для программы нужна 64-разрядная Windows 10 или 11."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "Для программы нужна Windows 10 или 11."
    Abort
  ${EndIf}
FunctionEnd

Section "Установка"
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  SetOverwrite on
  File /r "dist\portable\PDF-Tools\*.*"
  File "assets\pdf.ico"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\Сжать PDF.lnk" "$INSTDIR\PDF-Tools.exe" "" "$INSTDIR\pdf.ico"
  CreateShortcut "$SMPROGRAMS\Сжать PDF.lnk" "$INSTDIR\PDF-Tools.exe" "" "$INSTDIR\pdf.ico"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Tools" "DisplayName" "Сжать PDF"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Tools" "DisplayVersion" "1.1.0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Tools" "DisplayIcon" "$INSTDIR\pdf.ico"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Tools" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Tools" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Tools" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Tools" "NoRepair" 1
SectionEnd

Function .onInstSuccess
  IfSilent done
  Exec '"$INSTDIR\PDF-Tools.exe"'
  done:
FunctionEnd

Section "Uninstall"
  SetShellVarContext current
  ; Remove only files listed at build time, never recursively erase the app folder.
  !include "build\uninstall-files.nsh"
  Delete "$INSTDIR\pdf.ico"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$DESKTOP\Сжать PDF.lnk"
  Delete "$SMPROGRAMS\Сжать PDF.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDF-Tools"
SectionEnd
