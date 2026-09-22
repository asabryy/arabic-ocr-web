"""A user must not be able to reach another user's files by shaping `filename`.

This was a confirmed cross-user read: with user 1's token,
`GET /download?filename=../2/secret.pdf` returned user 2's bytes.
"""
import io

import pytest
from fastapi import HTTPException

from app.services.local_storage import LocalFileStorage
from app.services.storage import safe_name, safe_user_id

TRAVERSALS = [
    "../2/secret.pdf",
    "../../etc/passwd",
    "a/../../escaped.pdf",
    "..\\2\\secret.pdf",
    "/absolute.pdf",
    "sub/dir.pdf",
    "..",
    ".",
    "",
    ".hidden",
    "nul\x00.pdf",
]


@pytest.mark.parametrize("name", TRAVERSALS)
def test_safe_name_rejects_traversal(name):
    with pytest.raises(HTTPException) as exc:
        safe_name(name)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("name", ["report.pdf", "تقرير.pdf", "a b (1).PDF", "x-1_2.pdf"])
def test_safe_name_allows_ordinary_filenames(name):
    assert safe_name(name) == name


@pytest.mark.parametrize("uid", ["../1", "1/../2", "a", "", "trial/../x", "trial/a b"])
def test_safe_user_id_rejects_shaped_owners(uid):
    with pytest.raises(HTTPException):
        safe_user_id(uid)


@pytest.mark.parametrize("uid", ["1", "42", "trial/8a7b6c5d4e3f"])
def test_safe_user_id_allows_real_owners(uid):
    assert safe_user_id(uid) == uid


@pytest.mark.parametrize("name", TRAVERSALS)
def test_storage_refuses_to_build_an_escaping_path(tmp_path, monkeypatch, name):
    """Every storage primitive, not just the ones an endpoint happens to call."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    s = LocalFileStorage()
    for call in (
        lambda: s.get_path("1", name),
        lambda: s.file_exists("1", name),
        lambda: s.delete_file("1", name),
        lambda: s.get_status("1", name),
        lambda: s.save_file("1", name, io.BytesIO(b"x")),
    ):
        with pytest.raises(HTTPException):
            call()


def test_a_real_file_still_round_trips(tmp_path, monkeypatch):
    """The guard must not break the normal path."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    s = LocalFileStorage()
    s.save_file("1", "report.pdf", io.BytesIO(b"%PDF-1.4"))
    assert s.file_exists("1", "report.pdf")
    assert s.get_status("1", "report.pdf") == "pending"
    # And it landed inside the owner's directory, nowhere else.
    assert (tmp_path / "1" / "report.pdf").read_bytes() == b"%PDF-1.4"


def test_user_2_file_is_unreachable_from_user_1(tmp_path, monkeypatch):
    """The original exploit, as a regression test."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    s = LocalFileStorage()
    s.save_file("2", "secret.pdf", io.BytesIO(b"user-2-private"))

    with pytest.raises(HTTPException) as exc:
        s.get_path("1", "../2/secret.pdf")
    assert exc.value.status_code == 400
