from hcai_ops.storage.filesystem import FileSystemStorage


def test_filesystem_storage_append_and_read(tmp_path):
    storage = FileSystemStorage(str(tmp_path))
    storage.append("events", {"a": 1})
    storage.append("events", {"b": 2})

    records = storage.read_all("events")
    assert len(records) == 2
    assert records[0]["a"] == 1
    assert records[1]["b"] == 2
