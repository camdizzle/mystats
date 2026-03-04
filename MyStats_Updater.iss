; MyStats Inno Setup script tuned for in-place silent updates.
; Compatible with app updater launch flags:
;   /SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS        (one-click update)
;   /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS    (recovery re-launch)

#define MyAppName "MyStats"
#define MyAppVersion "6.2.0"
#define MyAppPublisher "CamWOW!!!"
#define MyAppURL "https://discord.gg/camwow"
#define MyAppExeName "mystats.exe"

[Setup]
AppId={{044A312F-B61E-4312-9A57-AE5558F6FCFE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableWelcomePage=yes
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no
PrivilegesRequired=lowest
OutputBaseFilename=MyStats_Setup_{#MyAppVersion}
SetupIconFile=circle1.ico
UninstallDisplayIcon={app}\circle1.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
RestartIfNeededByRun=no
AppMutex=MyStats_Setup_Mutex

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Registry]
Root: HKCU; Subkey: "Software\MyStats"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\MyStats"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletevalue

[Dirs]
Name: "{app}\Results"; Flags: uninsneveruninstall

[Files]
Source: "{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.iss,Output\*,MyStats_Setup_*.exe,settings.txt,obs_overlay\*,modern_dashboard\*"
Source: "settings.txt"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "circle1.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "obs_overlay\*"; DestDir: "{app}\obs_overlay"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "modern_dashboard\*"; DestDir: "{app}\modern_dashboard"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#MyAppExeName}"; Flags: nowait skipifnotsilent

[Code]
var
  i, j: Integer;
  settingExists: Boolean;
  NewSetting, Key, ExistingKey: String;

procedure StopRunningMyStatsProcesses;
var
  ResultCode: Integer;
  PsCommand: String;
begin
  Exec('taskkill', '/IM mystats.exe /F /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  PsCommand :=
    'Get-CimInstance Win32_Process | ' +
    'Where-Object { $_.CommandLine -and ($_.CommandLine -match ''mystats.py'' -or $_.CommandLine -match ''mystats.exe'') } | ' +
    'ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }';

  Exec('powershell', '-NoProfile -ExecutionPolicy Bypass -Command "' + PsCommand + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);
end;

function InitializeSetup(): Boolean;
begin
  StopRunningMyStatsProcesses;
  Result := True;
end;

procedure ClearPendingUpdateSettings;
var
  SettingsFile: TStringList;
  ConfigFilePath, Line, SettingKey: String;
  idx: Integer;
begin
  ConfigFilePath := ExpandConstant('{app}\settings.txt');
  if not FileExists(ConfigFilePath) then Exit;

  SettingsFile := TStringList.Create;
  try
    SettingsFile.LoadFromFile(ConfigFilePath);
    for idx := SettingsFile.Count - 1 downto 0 do
    begin
      Line := SettingsFile[idx];
      if Pos('=', Line) > 0 then
      begin
        SettingKey := Copy(Line, 1, Pos('=', Line) - 1);
        if (CompareText(SettingKey, 'pending_update_installer_path') = 0) or
           (CompareText(SettingKey, 'pending_update_silent_mode') = 0) or
           (CompareText(SettingKey, 'pending_update_version_label') = 0) then
          SettingsFile.Delete(idx);
      end;
    end;
    SettingsFile.SaveToFile(ConfigFilePath);
  finally
    SettingsFile.Free;
  end;
end;

procedure AppendAdditionalSettings;
var
  SettingsFile: TStringList;
  ConfigFilePath: String;
  NewSettings: array of String;
begin
  ConfigFilePath := ExpandConstant('{app}\settings.txt');
  SettingsFile := TStringList.Create;
  try
    if FileExists(ConfigFilePath) then
      SettingsFile.LoadFromFile(ConfigFilePath);

    SetArrayLength(NewSettings, 43);
    NewSettings[0] := 'marble_day=2024-09-17';
    NewSettings[1] := 'season=54';
    NewSettings[2] := 'br_file=';
    NewSettings[3] := 'race_file=';
    NewSettings[4] := 'allraces_file=';
    NewSettings[5] := 'winners_file=';
    NewSettings[6] := 'directory=';
    NewSettings[7] := 'announcedelay=False';
    NewSettings[8] := 'announcedelayseconds=10';
    NewSettings[9] := 'reset_audio=True';
    NewSettings[10] := 'chunk_alert=True';
    NewSettings[11] := 'chunk_alert_value=1000';
    NewSettings[12] := 'checkpoint_file=';
    NewSettings[13] := 'sync=Yes';
    NewSettings[14] := 'tilts_results_file=';
    NewSettings[15] := 'audio_device=';
    NewSettings[16] := 'chunk_alert_sound=' + 'Sound Files\chunkalert.mp3';
    NewSettings[17] := 'reset_audio_sound=' + 'Sound Files\reset.mp3';
    NewSettings[18] := 'active_event_ids=[]';
    NewSettings[19] := 'checkpoint_results_file=';
    NewSettings[20] := 'tilt_player_file=';
    NewSettings[21] := 'tilt_level_file=';
    NewSettings[22] := 'map_results_file=';
    NewSettings[23] := 'map_data_file=';
    NewSettings[24] := 'overlay_rotation_seconds=10';
    NewSettings[25] := 'overlay_refresh_seconds=3';
    NewSettings[26] := 'overlay_server_port=5000';
    NewSettings[27] := 'overlay_theme=midnight';
    NewSettings[28] := 'overlay_card_opacity=84';
    NewSettings[29] := 'overlay_text_scale=100';
    NewSettings[30] := 'overlay_show_medals=True';
    NewSettings[31] := 'overlay_compact_rows=False';
    NewSettings[32] := 'overlay_horizontal_layout=False';
    NewSettings[33] := 'tilt_overlay_theme=midnight';
    NewSettings[34] := 'tilt_scroll_step_px=1';
    NewSettings[35] := 'tilt_scroll_interval_ms=40';
    NewSettings[36] := 'tilt_scroll_pause_ms=900';
    NewSettings[37] := 'tilt_lifetime_base_xp=0';
    NewSettings[38] := 'update_later_clicks=0';
    NewSettings[39] := 'update_later_version=';
    NewSettings[40] := 'pending_update_installer_path=';
    NewSettings[41] := 'pending_update_silent_mode=True';
    NewSettings[42] := 'pending_update_version_label=';

    for j := 0 to GetArrayLength(NewSettings) - 1 do
    begin
      NewSetting := NewSettings[j];
      if Pos('=', NewSetting) = 0 then
        Continue;

      Key := Copy(NewSetting, 1, Pos('=', NewSetting) - 1);
      settingExists := False;

      for i := 0 to SettingsFile.Count - 1 do
      begin
        if Pos('=', SettingsFile[i]) = 0 then
          Continue;

        ExistingKey := Copy(SettingsFile[i], 1, Pos('=', SettingsFile[i]) - 1);
        if CompareText(Key, ExistingKey) = 0 then
        begin
          settingExists := True;
          Break;
        end;
      end;

      if not settingExists then
        SettingsFile.Add(NewSetting);
    end;

    SettingsFile.SaveToFile(ConfigFilePath);
  finally
    SettingsFile.Free;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssDone then
  begin
    AppendAdditionalSettings;
    ClearPendingUpdateSettings;
  end;
end;
