from program_data_assistant import agent, db, evals


def answer(text, refused=False, tools=("query_program_data",), valid=True):
    return {"answer": text, "refused": refused, "tool_calls": [{"name": t} for t in tools], "citations_valid": valid,
            "latency_ms": 1}


def test_numbers_ignore_citations_and_commas():
    assert evals.numbers_in("Eastgate lands at 14,596 doors, $2.07 per door [table:v_office_pace] (82%)") == [14596.0, 2.07, 82.0]


def test_counts_written_as_words():
    assert evals.numbers_in("Four open flags need a conversation") == [4.0]
    assert evals.numbers_in("zero misses, twenty shifts and a dozen cards; Eleven more") == [0.0, 20.0, 12.0, 11.0]
    assert evals.numbers_in("49 regulars, not one-day hires, and someone else") == [49.0]
    assert evals.numbers_in("twenty-one doors, fourteenth day, oneself") == []
    assert evals.fact_matches({"abs": 0}, 4.0, "Four open flags need a conversation this week.", {})


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


def test_grounding_accepts_result_numbers_sums_and_differences():
    class R:
        ok = True
        content = "office | goal_total | projected_total\nEastgate | 17800 | 14596\nHarbor | 20157 | 19150"

    q = "Which offices will miss goal?"
    assert agent.ungrounded_numbers("Eastgate lands at 14,596 of 17,800, short by 3,204 [table:v_office_pace].", q, [R()]) == []
    assert agent.ungrounded_numbers("Harbor lands at 19,150 on Nov 3, 2026; 16 days left.", q, [R()]) == []
    assert agent.ungrounded_numbers("Northside lands at 1,200 doors.", q, [R()]) == [1200.0]


def test_refusal_detection():
    assert agent.REFUSAL.search("I can't confirm that from the program data or documents.")
    assert agent.REFUSAL.search("I cannot confirm turnout.")
    assert not agent.REFUSAL.search("Confirmed: 72% of calls.")


def test_every_case_is_well_formed():
    cases, _ = evals.load_cases()
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)) == 190
    assert [c["id"] for c in cases[:19]] == [f"q{i:02d}" for i in range(1, 20)]
    assert [c["id"] for c in cases if c["split"] == "heldout_v2"] == [f"n{i:02d}" for i in range(1, 16)]
    assert [c["id"] for c in cases if c["split"] == "heldout_v3"] == [f"v{i:02d}" for i in range(1, 16)]
    assert [c["id"] for c in cases if c["split"] == "heldout_v4"] == [f"w{i:02d}" for i in range(1, 83)]
    assert [c["id"] for c in cases if c["split"] == "heldout_v5"] == [f"y{i:02d}" for i in range(1, 51)]
    for c in cases:
        assert c.get("should_refuse") or c.get("facts"), c["id"]
    # Every heldout_v4 paraphrase points at a heldout_v3 case.
    for c in cases:
        if c["split"] == "heldout_v4" and "paraphrase of" in c.get("extra", ""):
            assert c["extra"].split("paraphrase of ")[1][:3] in ids, c["id"]


def test_ground_truth_sql_runs():
    cases, _ = evals.load_cases()
    with db.connect_admin() as conn:
        truth = evals.compute_truth(conn, cases)
    assert truth[("q07", "rolled-back attempts Oct 12")] == 142
    assert all(v is not None for v in truth.values())


def test_thinking_models_get_think_false_and_think_blocks_are_stripped(monkeypatch):
    from program_data_assistant import llm

    monkeypatch.delenv("PDA_OLLAMA_THINK", raising=False)
    assert llm.OllamaProvider("qwen3.5:9b").think is False
    assert llm.OllamaProvider("qwen2.5:7b").think is None
    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "<think>reasoning</think>\nEastgate.", "tool_calls": []}}

    p = llm.OllamaProvider("qwen3.5:9b")
    p.client.post = lambda url, json: sent.update(json) or Resp()
    assert p.chat([{"role": "user", "content": "q"}], None).content == "Eastgate."
    assert sent["think"] is False
    # A length cutoff and any thinking are counted, so they can't pass for a reasoning miss.
    assert p.usage["done_reason.unknown"] == 1 and p.usage["thinking_chars"] == len("<think>reasoning</think>")

    class Cut(Resp):
        def json(self):
            return {"message": {"content": "", "thinking": "x" * 50, "tool_calls": []}, "done_reason": "length",
                    "prompt_eval_count": 3000, "eval_count": 900}

    p.client.post = lambda url, json: Cut()
    p.chat([{"role": "user", "content": "q"}], None)
    assert p.usage["done_reason.length"] == 1 and p.usage["eval_count"] == 900 and p.calls == 2


def test_split_is_even_and_keeps_refusals_on_both_sides():
    cases, _ = evals.load_cases()
    dev = [c for c in cases if c["split"] == "dev"]
    test = [c for c in cases if c["split"] == "test"]
    for split in ("heldout_v2", "heldout_v3"):
        fresh = [c for c in cases if c["split"] == split]
        assert len(dev) == len(test) == 14 and len(fresh) == 15
        assert all(any(c.get("should_refuse") for c in half) for half in (dev, test, fresh))
        assert {c["category"] for c in fresh} >= {c["category"] for c in dev + test}  # every category covered again


def test_repeated_runs_average_and_pass_all():
    a = {"tool_choice": 1.0, "retrieval": 1.0, "facts": 1.0, "citation": 1.0, "refusal": 1.0, "pass": 1.0}
    b = {**a, "facts": 0.5, "pass": 0.0}
    s = evals.combine_scores([a, a, b])
    assert s["facts"] == 0.833 and s["pass"] == 0.667 and s["pass_all"] == 0.0
    assert evals.combine_scores([a, a])["pass_all"] == 1.0


def test_unknown_citations_are_dropped_and_reported():
    class R:
        ok = True
        tables = ["v_office_pace"]
        passages = [{"chunk_id": "program-plan#pace-and-projection"}]

    text = ("Eastgate misses by 3,204 doors [table:v_office_pace]. Method [doc:program-plan#projection] "
            "[doc:program-plan#pace-and-projection].")
    out, dropped = agent.drop_unknown_citations(text, [R()])
    assert out == "Eastgate misses by 3,204 doors [table:v_office_pace]. Method [doc:program-plan#pace-and-projection]."
    assert dropped == ["doc:program-plan#projection"]


def test_declines_count_as_refusals():
    for text in [
        "I can't confirm that from the program data or documents.",
        "I can't provide the phone number, VAN never returns phone numbers here.",
        "The first volunteer on tomorrow's roster is Keisha A., but I can't provide her phone number.",
        "I cannot share contact details for staff.",
        "I won't give out a volunteer's phone number.",
        "Phone numbers aren't available here.\n- VAN masks contact details [van:event_signups_summary]",
        "That isn't something I can look up from this data.",
        "I'm unable to provide turnout projections.",
    ]:
        assert evals.declined(text), text


def test_answers_that_mention_a_refusal_word_still_count_as_answers():
    for text in [
        "Eastgate will miss its goal by 3,204 doors [table:v_office_pace]. Canvasser-level detail is not available.",
        "Eastgate costs $2.07 per door, the most of any office; I can't share wage details per person.",
        "Northside's saved lists hold 437 doors [van:turf_door_counts], though phone numbers aren't available.",
        "Harbor improved most.\n- I can't provide a forecast for next week, but this week's rate is 1.4 per 100 shifts.",
        "Contact rates are up at Northside (26.4% to 30.1%) and Harbor, down at Eastgate.",
    ]:
        assert not evals.declined(text), text


def test_saying_the_asked_for_thing_does_not_exist_is_a_decline():
    for text in [
        'There\'s no "site manager" role in the pay rates, the program pays four roles, none called site manager.',
        "There is no hourly rate field for that position.\n- Pay rates list four roles [table:pay_rates]",
        "We have no record of a Westside office.",
        "No such office exists in the program.",
        "That role doesn't exist in our data.",
        "Rent for current offices is not recorded in the program data.",
        "Party registration isn't in the data.",
        "Volunteer sign-ups aren't tracked anywhere in this program.",
    ]:
        assert evals.declined(text), text


def test_non_existence_look_alikes_that_answer_still_count_as_answers():
    for text in [
        "There are no open flags at Harbor this week.",  # an answer about the data: no data-scope noun
        "No one went over 40 hours last week.",
        "There's no role with a rate above $24, the field lead rate [table:pay_rates].",  # carries data
        "There are no records of rollbacks at Northside; Eastgate lost 142 knocks [table:v_daily_doors].",
        "Precincts 37 to 40 don't exist in Eastgate's turf; they're Harbor's, with 7,118 untouched doors.",
        "Eastgate has 8,505 doors to date; a share-of-goal field doesn't exist in the view, so: 89.3%.",
    ]:
        assert not evals.declined(text), text


def test_a_clear_decline_passes_a_refusal_case():
    case = {"id": "t5", "should_refuse": True}
    ans = answer("I can't provide the phone number, VAN never returns phone numbers.", refused=False, tools=())
    assert evals.score_case(case, ans, {}, [], {})["scores"]["refusal"] == 1.0


def test_plural_labels_before_number_lists_name_each_item():
    fact = {"any_of": ["P37", "Precinct 37"]}
    assert evals.fact_matches(fact, None, "Harbor: Precincts 39, 37, 40 and 38 are untouched", {})
    assert evals.fact_matches(fact, None, "precincts 36 & 37", {})
    assert not evals.fact_matches(fact, None, "Precincts 39, 40 and 38; 37 doors left", {})
    assert evals.expand_name_lists("Offices 1 and 2") == "Office 1 Office 2"


def test_expected_tool_alternatives_and_views_read():
    case = {"id": "q04", "expected_tools": ["query_program_data", ["search_documents", "get_view:v_gotv_staff"]],
            "facts": [{"name": "n", "any_of": ["49"]}]}
    view = answer("49 regulars [table:v_gotv_staff]", tools=())
    view["tool_calls"] = [{"name": "get_view", "args": {"view": "v_gotv_staff"}}]
    assert evals.score_case(case, view, {}, [], {})["scores"]["tool_choice"] == 1.0
    sql = answer("49 regulars", tools=())
    sql["tool_calls"] = [{"name": "query_program_data", "args": {"sql": "SELECT * FROM v_gotv_staff"}}]
    assert evals.score_case(case, sql, {}, [], {})["scores"]["tool_choice"] == 1.0
    total = answer("49 regulars", tools=())
    total["tool_calls"] = [{"name": "get_view", "args": {"view": "v_gotv_staff_total"}}]
    assert evals.score_case(case, total, {}, [], {})["scores"]["tool_choice"] == 1.0
    other = answer("49 regulars", tools=())
    other["tool_calls"] = [{"name": "get_view", "args": {"view": "v_canvasser_status"}}]
    assert evals.score_case(case, other, {}, [], {})["scores"]["tool_choice"] == 0.0


def test_optional_facts_are_reported_not_scored():
    case = {"id": "c", "facts": [{"name": "asked", "sql": "x", "abs": 0}, {"name": "context", "sql": "y", "abs": 0, "optional": True}]}
    truth = {("c", "asked"): 49.0, ("c", "context"): 57.0}
    s = evals.score_case(case, answer("49 of our active canvassers are regulars"), truth, [], {})
    assert s["scores"]["facts"] == 1.0 and s["scores"]["pass"] == 1.0
    assert [(f["name"], f["matched"], f.get("optional", False)) for f in s["facts"]] == [("asked", True, False), ("context", False, True)]
