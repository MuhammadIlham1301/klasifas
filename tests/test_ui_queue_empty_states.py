"""Regression checks for queue heading hierarchy and empty-state patterns."""
import re
from pathlib import Path

TEMPLATES = {
    "admin": Path("app/templates/admin/queue.html"),
    "technician": Path("app/templates/technician/queue.html"),
}


def _read(name):
    return TEMPLATES[name].read_text(encoding="utf-8")


def test_queue_headings_do_not_skip_levels():
    for name, path in TEMPLATES.items():
        source = path.read_text(encoding="utf-8")
        levels = [int(level) for level in re.findall(r"<h([1-6])\b", source)]

        assert levels, name
        assert levels[0] == 1, name
        assert "<h6" not in source, name
        for previous, current in zip(levels, levels[1:]):
            assert current <= previous + 1, (name, levels)


def test_technician_empty_states_distinguish_no_assignment_from_filter_empty():
    source = _read("technician")
    branch = source.index("{% if counts and counts.total %}")
    filter_empty = source.index("Tidak ada tiket ditemukan", branch)
    reset = source.index("Kembalikan Filter Default", filter_empty)
    fallback = source.index("{% else %}", branch)
    no_assignment = source.index("Belum ada tiket ditugaskan", fallback)

    assert branch < filter_empty < reset < fallback < no_assignment
    assert "Belum ada tiket yang ditugaskan kepada Anda." in source
    assert "Kembalikan Filter Default" not in source[fallback:]


def test_queue_empty_states_share_admin_pattern():
    for name in TEMPLATES:
        source = _read(name)

        assert '<h2 class="h6 fw-bold mb-0 text-dark">' in source, name
        assert "gap-2 flex-wrap" in source, name
        assert "card-body text-center py-5 px-3 px-sm-4" in source, name
        assert "rounded-circle bg-light text-primary p-3 mb-3" in source, name
        assert '<i class="bi bi-inbox fs-3"></i>' in source, name
        assert "Tidak ada tiket ditemukan" in source, name
        assert "Kembalikan Filter Default" in source, name
