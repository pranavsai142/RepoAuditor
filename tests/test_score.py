from repoauditor.auditor.score import inspector_score, item_score, repo_tag_scores, rubric_label


def test_rubric_label_matches_scorecard() -> None:
    assert rubric_label("head_substance") == "head substance"
    assert rubric_label("purpose") == "purpose"
    assert rubric_label("greenfield_vs_buy") == "greenfield vs buy"


def test_item_score_triplet() -> None:
    assert item_score({"concern": False, "answer": "real library"}) == 1
    assert item_score({"concern": True, "answer": "padding"}) == -1
    assert item_score({"concern": False, "answer": "cannot tell from pack"}) == 0
    assert item_score(None) is None


def test_item_score_coerces_bool_answer() -> None:
    assert item_score({"concern": False, "answer": True}) == 0
    assert item_score({"concern": True, "answer": True}) == -1
    assert item_score({"concern": False, "answer": False}) == 0
    assert item_score(True) is None  # type: ignore[arg-type]


def test_inspector_score_sums_scored_tags() -> None:
    report = {
        "checklist": [
            {"id": "padding", "concern": True, "answer": "daily dupes"},
            {"id": "head_substance", "concern": False, "answer": "has code"},
            {"id": "wip_theater", "concern": False, "answer": "cannot tell from pack"},
            {"id": "next_inspect", "concern": False, "answer": "abc"},
        ]
    }
    scores = repo_tag_scores(report)
    assert scores["padding"] == -1
    assert scores["head_substance"] == 1
    assert scores["wip_theater"] == 0
    assert "next_inspect" not in scores
    assert inspector_score(report) == 0  # -1 + 1 + 0, missing tags score 0 once present
    assert inspector_score(None) is None
    assert inspector_score({"checklist": []}) is None


def test_inspector_score_tolerates_bool_answers_and_non_dicts() -> None:
    report = {
        "checklist": [
            True,
            False,
            {"id": "padding", "concern": True, "answer": True},
            {"id": "head_substance", "concern": False, "answer": "has code"},
        ]
    }
    assert inspector_score(report) == 0