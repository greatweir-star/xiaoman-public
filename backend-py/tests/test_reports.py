"""Report payload regression tests."""

from xiaoman import reports


def test_monthly_report_exposes_top_emotions(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(reports, "timeline_list", lambda user_id, limit=2000: [])
    monkeypatch.setattr(reports, "_load_achievements", lambda user_id: {"badges": {}})
    monkeypatch.setattr(reports, "_ensure_llm_client", lambda: None)

    report = reports.generate_monthly_report("report-user", force=True)

    assert report["period"] == "monthly"
    assert report["top_emotions"] == []
