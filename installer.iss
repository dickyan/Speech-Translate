; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "Speech Translate"
#define MyAppVersion "1.3.2"
#define MyAppPublisher "Dadangdut33"
#define MyAppURL "https://github.com/Dadangdut33/Speech-Translate"
#define MyAppExeName "SpeechTranslate.exe"
#define EnvName ".venv"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
; Speech Translate     -> {EDE12D07-73B0-4B1F-91C3-A0ECE1AB3F7C}
; Speech Translate CPU -> {1C434936-CD0D-47B4-AB60-29E8AD2AEE40}
AppId={{EDE12D07-73B0-4B1F-91C3-A0ECE1AB3F7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=build\SpeechTranslate {#MyAppVersion} {#EnvName}\LICENSE.txt
InfoBeforeFile=build\pre_install_note.txt
InfoAfterFile=build\post_install_note.txt
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline
OutputDir=dist
OutputBaseFilename=SpeechTranslate
SetupIconFile=speech_translate\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "build\SpeechTranslate {#MyAppVersion} {#EnvName}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\SpeechTranslate {#MyAppVersion} {#EnvName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

