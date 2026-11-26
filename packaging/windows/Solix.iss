[Setup]
AppId=Solix.WebApp
AppName=Solix
AppVersion=1.0.1
DefaultDirName={localappdata}\Solix
DefaultGroupName=Solix
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=Solix-Setup
SetupIconFile=Solix.ico
UninstallDisplayIcon={app}\Solix.ico
DisableProgramGroupPage=yes

[Files]
Source: "Solix.exe"; DestDir: "{app}"
Source: "Solix.ico"; DestDir: "{app}"

[Icons]
Name: "{autoprograms}\Solix"; Filename: "{app}\Solix.exe"; IconFilename: "{app}\Solix.ico"
Name: "{autodesktop}\Solix"; Filename: "{app}\Solix.exe"; IconFilename: "{app}\Solix.ico"
