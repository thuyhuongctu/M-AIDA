from pathlib import Path

import pytest

from validation.analyze_validation import GOLD_REQUIRED, PRED_REQUIRED, analyze, read_csv


FIXTURES = Path(__file__).parent / "fixtures"


def test_synthetic_benchmark_metrics():
    metrics = analyze(
        read_csv(FIXTURES / "gold.csv", GOLD_REQUIRED),
        read_csv(FIXTURES / "predictions.csv", PRED_REQUIRED),
        tolerance=0.005,
    )

    assert metrics["selection"]["confusion_matrix"] == {"tp": 2, "fp": 1, "fn": 1, "tn": 0}
    assert metrics["selection"]["precision"] == pytest.approx(2 / 3)
    assert metrics["selection"]["recall"] == pytest.approx(2 / 3)
    assert metrics["field_accuracy"]["r_exact"]["value"] == pytest.approx(0.5)
    assert metrics["field_accuracy"]["sign"]["value"] == pytest.approx(1.0)
    assert metrics["governance"]["machine_proposal_hallucination_rate"]["value"] == pytest.approx(1 / 3)
    assert metrics["time"]["time_saving_fraction"] == pytest.approx(0.6)


def test_case_id_sets_must_match():
    gold = read_csv(FIXTURES / "gold.csv", GOLD_REQUIRED)
    predictions = read_csv(FIXTURES / "predictions.csv", PRED_REQUIRED)[:-1]
    with pytest.raises(ValueError, match="missing predictions: SYN-004"):
        analyze(gold, predictions, tolerance=0.005)
