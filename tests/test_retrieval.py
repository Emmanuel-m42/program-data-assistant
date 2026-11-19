import pytest

from program_data_assistant import db, retrieval


def test_chunks_split_on_headings():
    title, chunks = retrieval.chunk_markdown("rules", "# Rules\n\nIntro text.\n\n## First rule\nOne.\n\n## Second rule\nTwo.\n")
    assert title == "Rules"
    assert [c.chunk_id for c in chunks] == ["rules#overview", "rules#first-rule", "rules#second-rule"]
    assert chunks[1].text == "One."


def test_corpus_chunk_ids_are_unique():
    ids = [c.chunk_id for *_, cs in retrieval.load_corpus(db.REPO / "corpus") for c in cs]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("query,expected", [
    ("Who approves overtime?", "payroll-rules#overtime"),
    ("Why is the client's number higher than ours?", "counting-doors#why-the-client-s-numbers-differ-from-ours"),
    ("What counts as a duplicate registration card?", "registration-drive#valid-cards-and-duplicates"),
    ("How do I record a locked apartment building?", "qc-rules#apartments-and-units"),
])
def test_search_ranks_the_right_passage_in_top_4(query, expected):
    with db.connect_admin() as conn:
        hits = retrieval.search(conn, query)
    assert expected in [h["chunk_id"] for h in hits]
    assert hits == sorted(hits, key=lambda h: -h["score"])
