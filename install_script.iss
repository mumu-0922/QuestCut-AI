; Inno Setup Script for QuestCut-AI 1.0.1
; Reconstructed from installed files and setup analysis
; Original: Inno Setup 5.5.7 (Unicode)

[Setup]
AppId={{27CF3092-3A5A-460E-B48A-A19514427869}
AppName=QuestCut-AI
AppVersion=1.0.1
AppPublisher=QuestCut
DefaultDirName={pf}\QuestCut-AI
DefaultGroupName=QuestCut-AI
OutputBaseFilename=QuestCut-AI
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayName=QuestCut-AI
UninstallDisplayIcon={app}\QuestCut-AI.exe
SetupIconFile=Unpack.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Main executable (PyInstaller bootloader with embedded Python 3.10)
Source: "QuestCut-AI.exe"; DestDir: "{app}"; Flags: ignoreversion

; Python runtime and internal files
Source: "_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Windows App SDK / WinUI 3 runtime files
Source: "Microsoft.WindowsAppRuntime.Bootstrap.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.WindowsAppRuntime.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.Xaml.Controls.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.Xaml.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.ui.xaml.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.Xaml.Internal.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.Xaml.Phone.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.Input.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.Windowing.Core.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.Windowing.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.UI.Composition.OSSupport.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.Internal.FrameworkUdk.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.Windows.Widgets.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.Windows.ApplicationModel.Resources.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.WindowsAppRuntime.Insights.Resource.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.Graphics.Display.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.InputStateManager.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.DirectManipulation.dll"; DestDir: "{app}"; Flags: ignoreversion

; WinMD metadata files
Source: "*.winmd"; DestDir: "{app}"; Flags: ignoreversion

; Core system DLLs
Source: "DWriteCore.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "dwmcorei.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "dcompi.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "DwmSceneI.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "CoreMessagingXP.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "wuceffectsi.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "marshal.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "MRM.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "WinUIEdit.dll"; DestDir: "{app}"; Flags: ignoreversion

; Bundled AI model files
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs

; Resource files
Source: "resources.pri"; DestDir: "{app}"; Flags: ignoreversion
Source: "WindowsAppRuntime.png"; DestDir: "{app}"; Flags: ignoreversion

; UI resources
Source: "Microsoft.ui.xaml.resources.common.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "Microsoft.ui.xaml.resources.19h1.dll"; DestDir: "{app}"; Flags: ignoreversion

; WebView2
Source: "Microsoft.Web.WebView2.Core.dll"; DestDir: "{app}"; Flags: ignoreversion

; Language resources (100+ locales)
Source: "*-*\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; AppX / MSIX deployment files
Source: "AppxManifest.xml"; DestDir: "{app}"; Flags: ignoreversion
Source: "AppxBlockMap.xml"; DestDir: "{app}"; Flags: ignoreversion
Source: "AppxSignature.p7x"; DestDir: "{app}"; Flags: ignoreversion
Source: "AppxMetadata\*"; DestDir: "{app}\AppxMetadata"; Flags: ignoreversion
Source: "[Content_Types].xml"; DestDir: "{app}"; Flags: ignoreversion
Source: "MSIX\*"; DestDir: "{app}\MSIX"; Flags: ignoreversion

; JSON configuration
Source: "DynamicDependency-Override.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "PushNotifications-Override.json"; DestDir: "{app}"; Flags: ignoreversion

; Event Log manifest
Source: "EventLog-Instrumentation.man"; DestDir: "{app}"; Flags: ignoreversion

; PDB debug symbols
Source: "WindowsAppSdk.AppxDeploymentExtensions.Desktop-EventLog-Instrumentation.pdb"; DestDir: "{app}"; Flags: ignoreversion
Source: "WindowsAppSdk.AppxDeploymentExtensions.Desktop-EventLog-Instrumentation.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "WindowsAppSdk.AppxDeploymentExtensions.Desktop.dll"; DestDir: "{app}"; Flags: ignoreversion

; Deployment agent
Source: "DeploymentAgent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "RestartAgent.exe"; DestDir: "{app}"; Flags: ignoreversion

; Push notifications
Source: "PushNotificationsLongRunningTask.ProxyStub.dll"; DestDir: "{app}"; Flags: ignoreversion

; Release marker
Source: "Microsoft.WindowsAppRuntime.Release*"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\QuestCut-AI"; Filename: "{app}\QuestCut-AI.exe"
Name: "{group}\Uninstall QuestCut-AI"; Filename: "{app}\Uninstall.exe"
Name: "{commondesktop}\QuestCut-AI"; Filename: "{app}\QuestCut-AI.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\QuestCut-AI.exe"; Description: "Launch QuestCut-AI"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\QuestCut-AI.exe"; Parameters: "/uninstall"; Flags: runhidden

[Code]
; Custom messages and setup logic would go here
; The original setup used custom messages from the Inno Setup Messages file
