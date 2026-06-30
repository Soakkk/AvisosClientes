; Script de Inno Setup para "Avisos Asesoria E. Marin".
; Requiere haber compilado antes con build_exe.bat (carpeta dist\AvisosEMarin).
; Compilar este instalador con Inno Setup (ISCC.exe AvisosEMarin.iss).

#define MyAppName "Avisos Asesoria E. Marin"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Asesoria E. Marin"
#define MyAppExeName "AvisosEMarin.exe"

[Setup]
AppId={{B4F1B2A7-1E9A-4C77-9A2B-AV1S0SEMAR1N}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AvisosEMarin
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=AvisosEMarin_Setup_{#MyAppVersion}
SetupIconFile=..\assets\app.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\dist\AvisosEMarin\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
