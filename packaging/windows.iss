; Per-user installation; build with ISCC /DAppVersion=... windows.iss
[Setup]
AppId=io.github.mingdu.Brightness
AppName=Mingdu
AppVersion={#AppVersion}
AppPublisher=Mingdu Contributors
AppPublisherURL=https://github.com/ZhaoOyu/mingdu
DefaultDirName={localappdata}\Programs\Mingdu
DefaultGroupName=Mingdu
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=mingdu-{#AppVersion}-windows-x86_64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Mingdu.exe
LicenseFile=..\LICENSE

[Files]
Source: "..\dist\Mingdu\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Mingdu"; Filename: "{app}\Mingdu.exe"

[Run]
Filename: "{app}\Mingdu.exe"; Description: "Launch Mingdu"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Value: String;
begin
  if CurUninstallStep = usUninstall then
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run',
      'io.github.mingdu.Brightness', Value) then
      if Pos(ExpandConstant('{app}\Mingdu.exe'), Value) > 0 then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run',
          'io.github.mingdu.Brightness');
end;
