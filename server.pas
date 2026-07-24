program HealthServer;

{$mode objfpc}{$H+}

uses
  cthreads,
  fphttpserver, httpdefs, sysutils;

const
  LOTTY =
'╔═════════════════════════════════════════════════════════════════════╗' + LineEnding +
'║                                                                     ║' + LineEnding +
'║  ⠀⠀⠀⠀⢀⡀⣄⢀⡄⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣤⣴⡶⠶⠶⠖⠒⠒⠒⠲⠶⠶⢶⣤⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠰⣮⡿⠛⠻⠷⣯⣶⣀⡀⠀⠀⠀⠀⣀⣴⠾⠛⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠛⠶⣤⡀⠀⠀⠀⠀⠀⣀⣤⣾⣼⣿⣷⣿⣠⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⢛⣿⡄⠀⠀⠀⠀⠙⢿⣶⣂⣀⣤⡾⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠷⣄⠀⣀⣶⣿⠟⠋⠁⠀⠀⢹⣿⠆⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠾⣻⣦⡀⠀⠀⠀⠀⠙⣿⡿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⣿⠋⠁⠀⠀⠀⢀⣴⢿⡍⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠈⠸⢻⡷⣦⣄⡀⣰⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣦⣠⣤⣴⣾⢿⠝⠃⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⣀⢀⠀⡀⠀⠈⠋⠿⢹⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⠃⠋⠉⠀⢀⠀⡀⣀⠀⠀⠀        ║' + LineEnding +
'║  ⣴⣮⣷⣿⣾⣾⣧⣿⣼⣶⣆⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢿⣴⣄⣷⣿⡾⠷⠿⠾⣾⣧⡄        ║' + LineEnding +
'║  ⠶⢿⡋⠀⠀⠀⠀⠀⠀⠉⠉⢻⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡟⠋⠁⠀⠀⠀⠀⠀⢀⣿⠶        ║' + LineEnding +
'║  ⠉⠽⣷⣦⣄⣀⣀⠀⠀⠀⣀⣸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⢀⣀⣤⣴⣿⡏⠁        ║' + LineEnding +
'║  ⠀⠀⠁⠋⠻⠹⠿⠟⡿⠻⠻⠟⣿⠀⠀⠀⠀⠀⣴⣾⣿⣶⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣷⣦⠀⠀⠀⠀⣾⢻⠟⡿⠻⠛⠏⠛⠈⠁⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⣄⣤⣰⣿⣆⠀⠀⠀⠀⣿⣿⣿⣿⡇⠀⠀⠀⠀⢀⠀⠀⠀⠀⠀⣀⠀⠀⠀⠀⢸⣿⣿⣿⣿⠃⠀⠀⣰⣿⣖⣴⢀⡀⡀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⣀⢰⣼⣷⠿⠛⠋⠉⠹⣦⡀⠀⠀⠈⠛⠛⠋⠀⠀⠀⠀⠀⠉⠛⠛⠛⠛⠛⠉⠀⠀⠀⠀⠀⠉⠛⠛⠁⠀⠀⣴⠏⠉⠙⠛⠿⢾⣧⣶⣠⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⣰⣾⠟⠉⠀⠀⠀⠀⠀⣠⣾⡷⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⢞⣷⣤⡀⠀⠀⠀⠀⠈⠙⢿⣄⡀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠈⣽⣯⡀⠀⠀⢀⣠⣴⣿⡝⠊⠀⠈⠙⠶⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣤⠶⠋⠁⠀⠑⠋⣿⢶⣤⣤⣀⣀⣠⣼⢯⡅⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠐⠋⠿⢻⠿⡏⠷⠙⠁⠀⠀⠀⠀⠀⠀⠀⠉⠛⠳⠶⣤⣤⣄⣀⣀⣀⣀⣀⣀⣀⣠⣤⣤⠶⠚⠋⠉⠀⠀⠀⠀⠀⠀⠀⠈⠐⠃⠘⠋⠗⠙⠁⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡿⠁⠈⠉⠉⠉⠉⠉⠉⠉⠁⠀⢹⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⠃⠉⠉⠙⣆⠀⠀⠀⢰⠋⠉⠉⠀⢿⡀⠀⠀⠀╭─────────────────────╮  ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡏⠀⠐⠓⠒⠃⠀⠀⠀⠈⠓⠚⠂⠀⠸⣇⠀⠀⠀│ LOTTY says:         │  ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣾⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀│  "Теперь вы PROD!"  │  ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀╰─────────────────────╯  ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢹⡄⠀⣠⠚⠙⡆⠀⠀⠀⢰⠋⠑⣆⠀⢰⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣄⠀⠀⠰⠁⠀⠀⠀⠈⠃⠀⢀⣰⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⢶⣤⣤⣤⣤⣤⣤⣤⡶⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⢻⣇⠀⠀⠀⢸⡏⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠀⣿⠀⠀⢀⡿⢰⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡄⣿⠀⠀⣼⢇⡾⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢷⣿⠀⢰⣿⡞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║  ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣤⠿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀        ║' + LineEnding +
'║                                                                     ║' + LineEnding +
'║                 ██████╗ ██████╗  ██████╗ ██████╗                    ║' + LineEnding +
'║                 ██╔══██╗██╔══██╗██╔═══██╗██╔══██╗                   ║' + LineEnding +
'║                 ██████╔╝██████╔╝██║   ██║██║  ██║                   ║' + LineEnding +
'║                 ██╔═══╝ ██╔══██╗██║   ██║██║  ██║                   ║' + LineEnding +
'║                 ██║     ██║  ██║╚██████╔╝██████╔╝                   ║' + LineEnding +
'║                 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═════╝                    ║' + LineEnding +
'║                                                                     ║' + LineEnding +
'║                                                                     ║' + LineEnding +
'║                         Status: HEALTHY                             ║' + LineEnding +
'║                                                                     ║' + LineEnding +
'║                                                                     ║' + LineEnding +
'║                                                                     ║' + LineEnding +
'║                                                                     ║' + LineEnding +
'║                       © Powered by Watlon                           ║' + LineEnding +
'╚═════════════════════════════════════════════════════════════════════╝' + LineEnding;

type
  THandler = class
    procedure HandleRequest(Sender: TObject; var Req: TFPHTTPConnectionRequest;
      var Res: TFPHTTPConnectionResponse);
  end;

procedure THandler.HandleRequest(Sender: TObject; var Req: TFPHTTPConnectionRequest;
  var Res: TFPHTTPConnectionResponse);
begin
  Res.ContentType := 'text/plain; charset=utf-8';

  if (Req.URI = '/ping') or (Req.URI = '/ready') or (Req.URI = '/health') then
  begin
    Res.Code := 200;
    Res.Content := LOTTY;
  end
  else
  begin
    Res.Code := 404;
    Res.Content := 'not found' + LineEnding;
  end;
end;

var
  Server: TFPHTTPServer;
  Handler: THandler;

begin
  Handler := THandler.Create;
  Server := TFPHTTPServer.Create(nil);
  try
    Server.Port := 80;
    Server.Threaded := True;
    Server.OnRequest := @Handler.HandleRequest;
    Server.Active := True;

    WriteLn('Listening on :80');
    while True do Sleep(3600 * 1000);
  finally
    Server.Free;
    Handler.Free;
  end;
end.
