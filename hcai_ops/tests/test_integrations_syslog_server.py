from hcai_ops.integrations.syslog_server import SyslogReceiver


def test_syslog_receiver_process_line():
    collected = []
    receiver = SyslogReceiver(udp_port=0, tcp_port=0, event_handler=collected.append)
    receiver.process_line("Oct 11 22:14:15 myhost app[123]: Error connecting to db")
    assert collected
    evt = collected[0]
    assert evt.event_type == "log"
    assert "Error" in evt.log_message
    assert evt.source_id == "myhost"
