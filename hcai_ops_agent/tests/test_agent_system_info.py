from hcai_ops_agent.system_info import collect_system_info


def test_collect_system_info():
    info = collect_system_info()
    required = [
        "hostname",
        "platform",
        "cpu_percent",
        "ram_percent",
        "disk_percent",
        "net_sent",
        "net_recv",
        "uptime",
        "process_count",
    ]
    for key in required:
        assert key in info
