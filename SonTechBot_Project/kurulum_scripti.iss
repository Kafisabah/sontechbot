; SonTechBot için Inno Setup Kurulum Betiği
; v1.0 - 17 Haziran 2025

[Setup]
; AppId, uygulamanız için benzersiz bir kimliktir. Lütfen aşağıdaki adresten
; yeni bir GUID oluşturup {{...}} kısmına yapıştırın.
; https://www.guidgenerator.com/
AppId={{"rgzx1se4f0w145y8mb2h7w"}}
AppName=SonTechBot
AppVersion=1.7.1
AppPublisher=SonTech
AppPublisherURL=https://www.41den.com
AppSupportURL=https://www.41den.com/destek
DefaultDirName={autopf}\SonTechBot
DisableProgramGroupPage=yes
; Oluşturulacak setup.exe dosyasının konumu ve adı
OutputDir=.\install_package
OutputBaseFilename=SonTechBot_Kurulum_v1.7.1
SetupIconFile=logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Kurulacak olan ana .exe dosyanız. Kaynak yolunun doğru olduğundan emin olun.
Source: "nuitka_dist\sontechbot_gui.exe"; DestDir: "{app}"; Flags: ignoreversion
; Not: Gelecekte programa ek dosyalar (kullanım kılavuzu.pdf gibi) eklemek isterseniz,
; onları da buraya ekleyebilirsiniz.

[Icons]
Name: "{autoprograms}\SonTechBot"; Filename: "{app}\sontechbot_gui.exe"
Name: "{autodesktop}\SonTechBot"; Filename: "{app}\sontechbot_gui.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\sontechbot_gui.exe"; Description: "{cm:LaunchProgram,SonTechBot}"; Flags: nowait postinstall skipifsilent