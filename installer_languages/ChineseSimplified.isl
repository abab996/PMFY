; *** Inno Setup version 6.1.0+ Simplified Chinese messages ***
;

[LangOptions]
LanguageName=简体中文
LanguageID=$0804
LanguageCodePage=936

[Messages]

; *** Application titles
SetupAppTitle=安装
SetupWindowTitle=安装 - %1
UninstallAppTitle=卸载
UninstallWindowTitle=卸载 - %1

; *** Misc. common
ExitSetupTitle=退出安装程序
ExitSetupMessage=安装尚未完成。如果您现在退出，程序将不会被安装。%n%n您可以稍后再次运行安装程序来完成安装。%n%n确定要退出安装程序吗？
AboutSetupMenuItem=关于安装程序(&A)...
AboutSetupTitle=关于安装程序
AboutSetupMessage=%1 版本 %2%n%3%n%n%1 网址:%n%4
AboutSetupNote=
TranslatorNote=

; *** Buttons
ButtonBack=< 上一步(&B)
ButtonNext=下一步(&N) >
ButtonInstall=安装(&I)
ButtonOK=确定
ButtonCancel=取消
ButtonYes=是(&Y)
ButtonYesToAll=全是(&A)
ButtonNo=否(&N)
ButtonNoToAll=全否(&O)
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
ButtonWizardBrowse=浏览(&R)...
ButtonNewFolder=新建文件夹(&M)

; *** "Select Language" dialog messages
SelectLanguageTitle=选择安装语言
SelectLanguageLabel=请选择安装时使用的语言:

; *** Common dialog messages
ClickNext=单击“下一步”继续，或单击“取消”退出安装程序。
BeveledLabel=
BrowseDialogTitle=浏览文件夹
BrowseDialogLabel=在列表中选择一个文件夹，然后单击“确定”。
NewFolderName=新建文件夹

; *** "Welcome" wizard page
WelcomeLabel1=欢迎使用 [name] 安装向导
WelcomeLabel2=安装向导将在您的电脑上安装 [name/ver]。%n%n推荐在继续之前关闭所有其它正在运行的应用程序。

; *** "Password" wizard page
WizardPassword=密码
PasswordLabel1=该安装程序有密码保护。
PasswordLabel3=请输入密码，然后单击“下一步”继续。密码区分大小写。
PasswordEditLabel=密码(&P):
PasswordEmpty=必须输入密码才能继续。

; *** "License Agreement" wizard page
WizardLicense=许可协议
LicenseLabel=请在继续之前仔细阅读以下重要信息。
LicenseLabel3=请阅读以下许可协议。您必须接受此协议中的条款，才能继续安装。
LicenseAccepted=我接受协议(&A)
LicenseNotAccepted=我不接受协议(&D)

; *** "Information" wizard pages
WizardInfoBefore=信息
InfoBeforeLabel=请在继续之前仔细阅读以下重要信息。
InfoBeforeClickLabel=当您准备好继续安装时，单击“下一步”。
WizardInfoAfter=信息
InfoAfterLabel=请在继续之前仔细阅读以下重要信息。
InfoAfterClickLabel=当您准备好继续安装时，单击“下一步”。

; *** "User Information" wizard page
WizardUserInfo=用户信息
UserInfoDesc=请输入您的信息。
UserInfoName=用户名(&U):
UserInfoOrg=组织(&O):
UserInfoSerial=序列号(&S):
UserInfoNameEmail=用户名和电子邮件地址:

; *** "Select Destination Location" wizard page
WizardSelectDir=选择安装目标位置
SelectDirDesc=您想将 [name] 安装到什么地方？
SelectDirLabel3=安装程序将把 [name] 安装到下列文件夹中。
SelectDirBrowseLabel=单击“下一步”继续。如果您想选择其它文件夹，请单击“浏览”。
DiskSpaceMBLabel=至少需要 [mb] MB 的可用磁盘空间。
CannotInstallToNetworkDrive=安装程序无法安装到网络驱动器。
CannotInstallToUNCPath=安装程序无法安装到 UNC 路径。
InvalidPath=您必须输入一个包含驱动器盘符的完整路径，例如:%n%nC:\PMFY%n%n或 UNC 路径格式。
InvalidDrive=您选择的驱动器不存在或无法访问。请选择其它位置。
DiskSpaceWarningTitle=磁盘空间不足
DiskSpaceWarning=安装程序需要至少 %1 KB 的可用磁盘空间才能安装，但是所选驱动器只有 %2 KB 可用。%n%n您一定要继续吗？
DirNameTooLong=文件夹名称或路径太长。
InvalidSubDirName=文件夹名称不能包含下列任何字符:%n%n%1
DirExistsTitle=文件夹已存在
DirExists=文件夹:%n%n%1%n%n已经存在。您仍然要安装到此文件夹吗？
DirDoesntExistTitle=文件夹不存在
DirDoesntExist=文件夹:%n%n%1%n%n不存在。您想要创建此文件夹吗？

; *** "Select Components" wizard page
WizardSelectComponents=选择组件
SelectComponentsDesc=您想安装哪些组件？
SelectComponentsLabel2=选择您想安装的组件；清除您不想安装的组件。单击“下一步”继续。
FullInstallation=完全安装
CompactInstallation=精简安装
CustomInstallation=自定义安装
NoUninstallWarningTitle=组件已存在
NoUninstallWarning=安装程序检测到下列组件已经安装在您的电脑中:%n%n%1%n%n取消选择这些组件将不会卸载它们。%n%n您一定要继续吗？
ComponentSize1=%1 KB
ComponentSize2=%1 MB
ComponentsDiskSpaceMBLabel=当前选择的组件至少需要 [mb] MB 的可用磁盘空间。

; *** "Select Additional Tasks" wizard page
WizardSelectTasks=选择附加任务
SelectTasksDesc=您想让安装程序执行哪些附加任务？
SelectTasksLabel2=选择您想让安装程序在安装 [name] 时执行的附加任务，然后单击“下一步”。

; *** "Select Start Menu Folder" wizard page
WizardSelectProgramGroup=选择开始菜单文件夹
SelectStartMenuFolderDesc=您想在哪里放置程序的快捷方式？
SelectStartMenuFolderLabel3=安装程序将在下列开始菜单文件夹中创建程序的快捷方式。
SelectStartMenuFolderBrowseLabel=单击“下一步”继续。如果您想选择其它文件夹，请单击“浏览”。
MustEnterGroupName=您必须输入一个文件夹名称。
GroupNameTooLong=文件夹名称或路径太长。
InvalidGroupName=文件夹名称不能包含下列任何字符:%n%n%1
NoProgramGroupCheck2=不要创建开始菜单文件夹(&D)

; *** "Ready to Install" wizard page
WizardReady=准备安装
ReadyLabel1=安装程序现在准备开始在您的电脑中安装 [name]。
ReadyLabel2a=单击“安装”继续安装，或单击“上一步”查看或更改任何设置。
ReadyLabel2b=单击“安装”继续安装。
ReadyMemoUserInfo=用户信息:
ReadyMemoDir=目标位置:
ReadyMemoType=安装类型:
ReadyMemoComponents=选定组件:
ReadyMemoGroup=开始菜单文件夹:
ReadyMemoTasks=附加任务:

; *** "Preparing to Install" wizard page
WizardPreparing=正在准备安装
PreparingDesc=安装程序正在准备在您的电脑中安装 [name]。
PreviousInstallNotCompleted=先前程序的安装或卸载未完成。您需要重新启动电脑来完成该安装。%n%n重新启动电脑后，请再次运行安装程序以完成 [name] 的安装。
CannotContinue=安装程序无法继续。请单击“取消”退出。
ApplicationsFound=下列应用程序正在使用需要由安装程序更新的文件。推荐您允许安装程序自动关闭这些应用程序。
ApplicationsFound2=下列应用程序正在使用需要由安装程序更新的文件。推荐您允许安装程序自动关闭这些应用程序。安装完成后，安装程序将尝试重新启动这些应用程序。
CloseApplications=自动关闭应用程序(&A)
DontCloseApplications=不要关闭应用程序(&D)
ErrorCloseApplications=安装程序无法自动关闭所有应用程序。推荐您在继续之前关闭所有使用需要由安装程序更新的文件的应用程序。
PrepareToInstallNeedsRestart=安装程序必须重新启动电脑。重新启动电脑后，请再次运行安装程序以完成 [name] 的安装。

; *** "Installing" wizard page
WizardInstalling=正在安装
InstallingLabel=安装程序正在将 [name] 安装到您的电脑中，请稍候。

; *** "Setup Completed" wizard page
FinishedHeadingLabel=[name] 安装向导完成
FinishedLabelNoIcons=安装程序已在您的电脑中成功安装了 [name]。
FinishedLabel=安装程序已在您的电脑中成功安装了 [name]。可以通过选择安装的快捷方式来运行此应用程序。
ClickFinish=单击“完成”退出安装程序。
FinishedRestartLabel=为了完成 [name] 的安装，安装程序必须重新启动您的电脑。您想现在重新启动吗？
FinishedRestartMessage=为了完成 [name] 的安装，安装程序必须重新启动您的电脑。%n%n您想现在重新启动吗？
ShowReadmeCheck=是的，我想查看 README 文件
YesRadio=是，立即重新启动电脑(&Y)
NoRadio=否，我稍后重新启动电脑(&N)
ChangeRunProgram=运行 [name](&R)
ConfirmExit=您确定要退出安装程序吗？

; *** "Status" messages
StatusClosingApplications=正在关闭应用程序...
StatusCreateDirs=正在创建目录...
StatusExtractFiles=正在提取文件...
StatusCreateIcons=正在创建快捷方式...
StatusCreateIniEntries=正在创建 INI 条目...
StatusCreateRegistryEntries=正在创建注册表条目...
StatusRegisterFiles=正在注册文件...
StatusSavingVersion=正在保存版本信息...
StatusRunProgram=正在完成安装...
StatusRestartingApplications=正在重新启动应用程序...
StatusRollback=正在回滚更改...

; *** Custom Messages
[CustomMessages]
CreateDesktopIcon=创建桌面快捷方式(&D)
AdditionalIcons=快捷方式:
LaunchProgram=立即运行 %1
