#define MyAppName "idō"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "idō"
#define MyAppExeName "ido.exe"

[Setup]
AppId={{A42A3845-76FC-48B8-8DB0-4F4F1A4D6E11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ido
DefaultGroupName=idō
OutputDir=..
OutputBaseFilename=ido-windows
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\ido.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\idō"; Filename: "{app}\{#MyAppExeName}"

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
  ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}')

[Code]
function NeedsAddPath(Param: string): Boolean;
var
  Paths: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Paths) then
    Paths := '';
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(Paths) + ';') = 0;
end;
