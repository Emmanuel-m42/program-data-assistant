from program_data_assistant import agent, db, evals


def answer(text, refused=False, tools=("query_program_data",), valid=True):
    return {"answer": text, "refused": refused, "tool_calls": [{"name": t} for t in tools], "citations_valid": valid,
            "latency_ms": 1}


def test_numbers_ignore_citations_and_commas():
    assert evals.numbers_in("Eastgate lands at 14,596 doors, $2.07 per door [table:v_office_pace] (82%)") == [14596.0, 2.07, 82.0]


def test_relative_and_absolute_tolerance():
    assert evals.fact_matches({"tol": 0.01}, 57329.3, "We land at 57,100 doors.", {})
    assert not evals.fact_matches({"tol": 0.001}, 57329.3, "We land at 57,100 doors.", {})
    assert evals.fact_matches({"abs": 0.3}, 4.36, "Eastgate needs 4.4 more shifts a day", {})
    assert not evals.fact_matches({"abs": 0.3}, 4.36, "Eastgate needs 5 more shifts a day", {})


def test_shortfall_matches_regardless_of_sign():
    assert evals.fact_matches({"tol": 0.03}, 3203.6, "Eastgate is projected at -3,204 against goal", {})


def test_percent_facts_accept_fractions():
    assert evals.fact_matches({"abs": 0.6, "kind": "percent"}, 72.3, "confirmed share 0.723", {})
    assert evals.fact_matches({"abs": 0.6, "kind": "percent"}, 72.3, "72.1% confirmed", {})


def test_text_facts():
    assert evals.fact_matches({"any_of": ["Mill Street", "S1"]}, None, "Open it at the mill street storefront.", {})
    assert not evals.fact_matches({"any_of": ["Mill Street"]}, None, "Canal Row", {})


def test_score_case_full_pass():
    case = {"id": "t1", "expected_tools": ["query_program_data"], "expected_docs": ["a#b"],
            "facts": [{"name": "n", "sql": "x", "abs": 0}, {"name": "office", "any_of": ["Eastgate"]}]}
    r = evals.score_case(case, answer("Eastgate misses by 3,204 [table:v_office_pace]"), {("t1", "n"): 3204.0}, ["a#b"], {})
    assert r["scores"] == {"tool_choice": 1.0, "retrieval": 1.0, "facts": 1.0, "citation": 1.0, "refusal": 1.0, "pass": 1.0}


def test_score_case_wrong_refusal_fails_everything():
    case = {"id": "t2", "expected_tools": ["query_program_data"], "facts": [{"name": "office", "any_of": ["Eastgate"]}]}
    r = evals.score_case(case, answer("I can't confirm that. Eastgate?", refused=True, valid=False), {}, [], {})
    assert r["scores"]["refusal"] == 0.0 and r["scores"]["facts"] == 0.0 and r["scores"]["pass"] == 0.0


def test_score_case_correct_refusal():
    case = {"id": "t3", "should_refuse": True}
    r = evals.score_case(case, answer("I can't confirm that from the program data or documents.", refused=True, tools=()), {}, [], {})
    assert r["scores"]["refusal"] == 1.0 and r["scores"]["pass"] == 1.0
    assert r["scores"]["facts"] is None and r["scores"]["citation"] is None


def test_missing_tool_fails_tool_choice():
    case = {"id": "t4", "expected_tools": ["query_program_data", "search_documents"], "facts": []}
    r = evals.score_case(case, answer("ok [table:x]"), {}, [], {})
    assert r["scores"]["tool_choice"] == 0.0


def test_citation_parsing_and_validation():
    cites = agent.parse_citations("Doors [table:v_office_pace]; rule [doc:qc-rules#flash-knocking] and [table: knocks, doc:x#y]")
    assert cites == [{"type": "table", "id": "v_office_pace"}, {"type": "doc", "id": "qc-rules#flash-knocking"},
                     {"type": "table", "id": "knocks"}, {"type": "doc", "id": "x#y"}]

    class R:
        ok = True
        tables = ["v_office_pace", "knocks"]
        passages = [{"chunk_id": "qc-rules#flash-knocking"}]

    assert not agent.citations_valid([R()], cites)  # x#y was never returned
    assert agent.citations_valid([R()], cites[:3])
    assert not agent.citations_valid([R()], [])


def test_refusal_detection():
    assert agent.REFUSAL.search("I can't confirm that from the program data or documents.")
    assert agent.REFUSAL.search("I cannot confirm turnout.")
    assert not agent.REFUSAL.search("Confirmed: 72% of calls.")


def test_every_case_is_well_formed():
    cases, _ = evals.load_cases()
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)) == 28
    assert [c["id"] for c in cases[:19]] == [f"q{i:02d}" for i in range(1, 20)]
    for c in cases:
        assert c.get("should_refuse") or c.get("facts"), c["id"]


def test_ground_truth_sql_runs():
    cases, _ = evals.load_cases()
    with db.connect_admin() as conn:
        truth = evals.compute_truth(conn, cases)
    assert truth[("q07", "rolled-back attempts Oct 12")] == 142
    assert all(v is not None for v in truth.values())
