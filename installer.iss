#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#ifndef AppName
  #define AppName "ChatList"
#endif

#ifndef AppExeName
  #define AppExeName AppName + "-" + AppVersion
#endif

[Setup]
AppId={{A3F8C2E1-9B4D-4F6A-8C1E-2D5E7F9A0B3C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename={#AppName}-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#AppExeName}.exe
UninstallDisplayName={#AppName}
CreateUninstallRegKey=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "dist\{#AppExeName}.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}.exe"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}.exe"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM {#AppExeName}.exe"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
Type: files; Name: "{app}\chatlist.log"
Type: files; Name: "{app}\chatlist.db"
Type: files; Name: "{app}\.env"
