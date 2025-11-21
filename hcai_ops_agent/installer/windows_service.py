"""
Windows service installer stub using pywin32.
Not executed during tests; provided for completeness.
"""
try:
    import win32serviceutil  # type: ignore
    import win32service  # type: ignore
    import win32event  # type: ignore
except Exception:  # pragma: no cover - environment without pywin32
    win32serviceutil = None
    win32service = None
    win32event = None

from hcai_ops_agent.main import run


class HCAIAgentService:  # pragma: no cover - platform-specific
    if win32serviceutil:
        _svc_name_ = "HCAIAgent"
        _svc_display_name_ = "HCAI OPS Agent"
        _svc_description_ = "Collects telemetry and sends to HCAI OPS backend"

        def __init__(self, args):
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        def SvcStop(self):
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            run()


def install_service():  # pragma: no cover - platform-specific
    if not win32serviceutil:
        raise RuntimeError("pywin32 not available")
    win32serviceutil.InstallService(
        HCAIAgentService,
        HCAIAgentService._svc_name_,
        HCAIAgentService._svc_display_name_,
        startType=win32service.SERVICE_AUTO_START,
    )
    win32serviceutil.StartService(HCAIAgentService._svc_name_)

