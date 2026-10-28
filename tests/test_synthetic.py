"""Dữ liệu giả lập (spec synthetic-data): bộ sinh, đổi về đơn vị nguồn, đáp án thật, nạp."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from macro import ingest
from macro.db import connect, init_schema
from macro.scenario import SHOCKS, outcome_series
from macro.synthetic import load as synthetic
from macro.synthetic.generate import (
    _to_source,
    bounded_downstream,
    impulse_response,
    model_space,
    observations,
)
from macro.synthetic.model import Relation, Scenario, load_scenario


def scenario(**overrides: object) -> Scenario:
    data: dict[str, object] = {
        "name": "t",
        "seed": 1,
        "start": "2010-01",
        "end": "2015-12",
        "series": {
            "global.brent": {"process": "ar1", "phi": 0.5, "sd": 6},
            "vn.pmi_mfg": {"process": "random_walk", "start": 50, "sd": 0.3},
            "vn.iip": {"process": "noise", "mean": 8, "sd": 2},
        },
        "relations": [{"outcome": "vn.pmi_mfg", "shock": "global.brent", "beta": 0.2, "lag": 1}],
    }
    data.update(overrides)
    return Scenario.model_validate(data)


def test_same_seed_same_numbers_other_seed_differs():
    s = scenario()
    pd.testing.assert_frame_equal(model_space(s), model_space(s))
    assert not model_space(s).equals(model_space(s, seed=2))


@pytest.mark.parametrize("series_id", ["global.brent", "us.ust10y", "vn.vnindex", "vn.exports"])
def test_source_units_give_back_the_model_series(series_id):
    y = pd.Series(
        np.random.default_rng(0).normal(5, 2, 48),
        index=pd.period_range("2010-01", periods=48, freq="M"),
    )
    raw = _to_source(series_id, y)
    if series_id in SHOCKS:
        back = SHOCKS[series_id].transform(raw)
        np.testing.assert_allclose(back.iloc[1:], y.iloc[1:])
    elif series_id == "vn.vnindex":
        np.testing.assert_allclose(100 * np.log(raw), y)
    else:  # tăng trưởng so cùng kỳ, từ tháng 13
        np.testing.assert_allclose((raw / raw.shift(12) - 1).iloc[12:] * 100, y.iloc[12:])


def test_gdp_stays_between_bounds_from_the_cutoff():
    gdp = model_space(load_scenario("baseline"))["vn.gdp_yoy"]
    after = gdp[gdp.index >= pd.Period("2026-01", freq="M")]
    assert len(after) == 132
    assert after.between(9, 15).all()


def test_cpi_parts_overlap_with_the_declared_offset():
    s = scenario(
        series={"vn.cpi_yoy_long": {"process": "ar1", "mean": 3, "phi": 0.9, "sd": 0.3}},
        relations=[],
        cpi={"overlap_months": 6, "offset": 0.5},
    )
    by_id: dict[str, dict] = {}
    for o in observations(s):
        by_id.setdefault(o.series_id, {})[o.period] = o.value
    imf, local = by_id["vn.cpi_yoy_imf"], by_id["vn.cpi_yoy"]
    common = sorted(set(imf) & set(local))
    assert len(common) == 6
    assert all(abs(local[d] - imf[d] - 0.5) < 1e-9 for d in common)
    assert max(local) > max(imf)


def test_missing_series_are_not_written():
    s = scenario(missing=["vn.iip"])
    assert {o.series_id for o in observations(s)} == {"global.brent", "vn.pmi_mfg"}


def test_impulse_response_includes_shock_persistence():
    s = scenario()
    response = impulse_response(s, s.relations, "global.brent", "vn.pmi_mfg")
    # PMI là bước ngẫu nhiên, Brent AR(1) phi 0,5: tầm h cộng dồn 0,2·(1 + 0,5 + … + 0,5^(h−1)).
    expected = [0.2 * sum(0.5**k for k in range(h)) for h in range(1, 13)]
    np.testing.assert_allclose(response, expected)
    assert impulse_response(s, s.relations, "global.brent", "vn.iip") == [0.0] * 12


def test_bounded_series_and_what_they_drive_are_nonlinear():
    s = load_scenario("baseline")
    relations = [*s.relations, Relation(outcome="vn.iip", shock="vn.gdp_yoy", beta=1, lag=1)]
    assert bounded_downstream(s, relations) == {"vn.gdp_yoy", "vn.iip"}


def test_extends_overrides_keys(tmp_path):
    child = tmp_path / "child.yaml"
    child.write_text("extends: baseline\nname: child\ncpi: {offset: 0.5}\n", encoding="utf-8")
    s = load_scenario(str(child))
    assert s.name == "child" and s.cpi.offset == 0.5 and s.cpi.overlap_months == 24
    assert s.series == load_scenario("baseline").series


def test_relation_must_reference_declared_series():
    with pytest.raises(ValueError, match="chưa khai báo"):
        scenario(relations=[{"outcome": "vn.iip", "shock": "us.ust10y", "beta": 1, "lag": 1}])


def test_load_then_refuse_mixing_in_both_directions(database_url, tmp_path, capsys):
    loaded_scenario, seed = synthetic.load(database_url, "missing-data", seed=3)
    assert (loaded_scenario.name, seed) == ("missing-data", 3)
    assert synthetic.loaded(database_url) == ("missing-data", 3)
    with connect(database_url) as conn:
        y, reason, source = outcome_series(conn, "vn.pmi_mfg")
    assert reason is None and source == "Nguồn: Giả lập" and y.notna().sum() > 200

    # Số thật vào database giả lập: từ chối, không ghi gì.
    assert ingest.main(["--raw-dir", str(tmp_path), "--database-url", database_url]) == 2
    assert "Từ chối:" in capsys.readouterr().err
    assert synthetic.loaded(database_url) == ("missing-data", 3)


def test_synthetic_into_a_real_database_is_refused(database_url):
    with connect(database_url) as conn:
        init_schema(conn)
        conn.execute(
            "INSERT INTO fetch_runs (connector, status, raw_path) VALUES ('fred', 'ok', 'x')"
        )
        conn.commit()
    with pytest.raises(synthetic.Refused, match="Từ chối: database này đã có số liệu thật"):
        synthetic.load(database_url, "missing-data")
