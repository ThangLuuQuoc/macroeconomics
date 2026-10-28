"""Bản đồ ảnh hưởng (spec influence-map): đóng góp, màu theo tác động, kích thước, thiếu dữ liệu."""

from __future__ import annotations

import math

import pytest

from macro.db import connect, init_schema
from macro.influence import R_MAX, R_MIN, influence
from macro.scenario import SHOCKS, load_monthly, simulate
from macro.synthetic import load as synthetic


@pytest.fixture
def demo(database_url):
    synthetic.load(database_url, "influence-demo")
    with connect(database_url) as conn:
        yield conn


def test_default_centre_is_gdp_when_it_has_data(demo):
    result = influence(demo, real=False)
    assert result.center == "vn.gdp_yoy"
    assert result.month == result.months[-1] == "2036-12"
    assert len(result.bubbles) == len(SHOCKS)
    assert result.no_real_data == []


def test_contribution_follows_the_backtest_formula(demo):
    result = influence(demo, "vn.vnindex", "2036-12", real=False)
    brent = next(b for b in result.bubbles if b.series_id == "global.brent")
    betas = {
        row.h: row.estimate
        for o in simulate(demo, "global.brent", 1.0).outcomes
        if o.series_id == "vn.vnindex"
        for row in o.horizons
    }
    x = SHOCKS["global.brent"].transform(load_monthly(demo, "global.brent"))
    month = x.index[-1]
    expected = sum(betas[k] * x[month - k] for k in range(1, 12))
    assert brent.contribution == pytest.approx(expected)
    assert brent.shock_change == pytest.approx(sum(x[month - k] for k in range(12)))


def test_colour_follows_the_effect_not_the_direction(demo):
    result = influence(demo, "vn.vnindex", real=False)
    usd = next(b for b in result.bubbles if b.series_id == "us.usd_broad")
    assert usd.shock_change is not None and usd.shock_change < 0
    assert usd.effect == "up" and usd.effect_text == "đẩy lên"


def test_radius_grows_with_contribution_and_ranking_is_sorted(demo):
    result = influence(demo, "vn.vnindex", real=False)
    sized = sorted(
        (abs(b.contribution), b.radius) for b in result.bubbles if b.contribution is not None
    )
    radii = [r for _, r in sized]
    assert radii == sorted(radii)
    assert radii[0] >= R_MIN and math.isclose(radii[-1], R_MAX)
    by_id = {b.series_id: abs(b.contribution or 0) for b in result.bubbles}
    contributions = [by_id[s] for s in result.ranking]
    assert contributions == sorted(contributions, reverse=True)


def test_month_changes_the_numbers(demo):
    latest = influence(demo, "vn.vnindex", real=False)
    earlier = influence(demo, "vn.vnindex", "2030-06", real=False)
    assert earlier.month == "2030-06"
    assert [b.contribution for b in earlier.bubbles] != [b.contribution for b in latest.bubbles]
    unknown = influence(demo, "vn.vnindex", "1800-01", real=False)
    assert unknown.month == latest.month


def test_missing_centre_and_missing_factors(database_url):
    with connect(database_url) as conn:
        init_schema(conn)
        result = influence(conn)
    assert result.center == "vn.vnindex"
    assert result.insufficient_text == "Chưa đủ dữ liệu cho VN-Index."
    assert result.bubbles == []
    assert "Lãi suất điều hành NHNN" in result.no_real_data
