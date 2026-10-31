import pytest
from pydantic import ValidationError
from backend.models.campaign import CallingHours


def test_calling_hours_accepts_integers():
    ch = CallingHours(days_of_week=[1, 2, 3, 4, 5, 6])
    assert ch.days_of_week == [1, 2, 3, 4, 5, 6]


def test_calling_hours_accepts_day_strings():
    ch = CallingHours(days_of_week=["Monday", "Saturday", "friday"])
    assert ch.days_of_week == [1, 5, 6]


def test_calling_hours_normalizes_and_sorts_with_sunday():
    ch = CallingHours(days_of_week=["Sun", "Wed", 1, 6])
    assert ch.days_of_week == [0, 1, 3, 6]


def test_calling_hours_rejects_invalid_day():
    with pytest.raises(ValidationError):
        CallingHours(days_of_week=["Funday"])


def test_calling_hours_rejects_empty_days():
    with pytest.raises(ValidationError):
        CallingHours(days_of_week=[])


def test_calling_hours_rejects_out_of_range():
    with pytest.raises(ValidationError):
        CallingHours(days_of_week=[7])


def test_campaign_response_includes_calling_hours():
    from backend.models.campaign import Campaign
    from backend.api.v1.campaigns import _campaign_response

    c = Campaign(
        organization_id="org-1",
        name="Test Camp",
        agent_id="ag-1",
        agent_version=1,
        voice_profile_id="vp-1",
        voice_profile_version=1,
        calling_number_id="pn-1",
        calling_number="+919876543210",
        calling_hours=CallingHours(start_time="10:00", end_time="17:00", days_of_week=[1, 2, 6]),
    )
    res = _campaign_response(c)
    assert "calling_hours" in res
    assert res["calling_hours"] is not None
    assert res["calling_hours"]["start_time"] == "10:00"
    assert res["calling_hours"]["days_of_week"] == [1, 2, 6]
