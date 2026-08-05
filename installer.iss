[Setup]
AppName=Audio Extractor CD by AO Labs
AppVersion=1.1.5
AppId=AudioExtractorCD_AOLabs
DefaultDirName={autopf}\Audio Extractor CD
DefaultGroupName=Audio Extractor CD
OutputDir=setup
OutputBaseFilename=AudioExtractorCD_Installer
Compression=lzma2/ultra
SolidCompression=yes
DirExistsWarning=no
CloseApplications=yes
RestartApplications=no

DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Iconos adicionales:"

[Messages]
ButtonInstall=&Instalar / Actualizar
SetupAppTitle=Instalador/Actualizador de Audio Extractor CD
SetupWindowTitle=Instalador/Actualizador de %1

[Files]
Source: "dist\Audio_Extractor_CD_AO_Labs\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Audio Extractor CD"; Filename: "{app}\Audio_Extractor_CD_AO_Labs.exe"
Name: "{autodesktop}\Audio Extractor CD"; Filename: "{app}\Audio_Extractor_CD_AO_Labs.exe"; Tasks: desktopicon

[Registry]
; Registra la aplicacion en AutoPlay Handlers
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\Handlers\AudioExtractorCD"; ValueType: string; ValueName: "Action"; ValueData: "Extraer pistas de audio"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\Handlers\AudioExtractorCD"; ValueType: string; ValueName: "DefaultIcon"; ValueData: "{app}\Audio_Extractor_CD_AO_Labs.exe,0"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\Handlers\AudioExtractorCD"; ValueType: string; ValueName: "InvokeProgID"; ValueData: "AudioExtractorCD.AutoPlay"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\Handlers\AudioExtractorCD"; ValueType: string; ValueName: "InvokeVerb"; ValueData: "open"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\Handlers\AudioExtractorCD"; ValueType: string; ValueName: "Provider"; ValueData: "Audio Extractor CD"

; Asigna el Handler al evento PlayCDAudioOnArrival
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers\EventHandlers\PlayCDAudioOnArrival"; ValueType: string; ValueName: "AudioExtractorCD"; ValueData: ""

; Crea el ProgID que ejecutara la aplicacion
Root: HKA; Subkey: "Software\Classes\AudioExtractorCD.AutoPlay"; ValueType: string; ValueData: "Audio Extractor CD AutoPlay Handler"
Root: HKA; Subkey: "Software\Classes\AudioExtractorCD.AutoPlay\shell\open\command"; ValueType: string; ValueData: """{app}\Audio_Extractor_CD_AO_Labs.exe"""
