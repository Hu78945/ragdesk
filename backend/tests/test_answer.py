from ragdesk.answer import REFUSAL, ExtractiveAnswerer, format_sources
from ragdesk.store import Hit

HITS = [
    Hit(1, "retries.md", "Retries", "Workers send a heartbeat every 5 seconds. Dogs are not involved.", 1.0),
    Hit(2, "security.md", "Security", "Tokens are hashed with SHA-256.", 0.5),
]


def test_extractive_answer_cites_the_matching_source():
    answer = "".join(ExtractiveAnswerer().stream("How often do workers send a heartbeat?", HITS))
    assert answer.startswith("Workers send a heartbeat every 5 seconds. [1]")
    assert "[2]" not in answer


def test_extractive_answer_refuses_without_overlap():
    assert "".join(ExtractiveAnswerer().stream("banana bread recipe", HITS)) == REFUSAL


def test_extractive_answer_is_deterministic():
    a = ExtractiveAnswerer()
    q = "how are tokens hashed and how often are heartbeats sent"
    assert "".join(a.stream(q, HITS)) == "".join(a.stream(q, HITS))


def test_sources_are_numbered_for_citation():
    text = format_sources(HITS)
    assert '<source id="1" document="retries.md"' in text
    assert '<source id="2" document="security.md"' in text


class _FakeStream:
    def __init__(self, chunks):
        self.text_stream = iter(chunks)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_claude_answerer_streams_with_grounding_prompt(monkeypatch):
    from ragdesk.answer import SYSTEM_PROMPT, ClaudeAnswerer

    answerer = ClaudeAnswerer(api_key="test-key", model="claude-haiku-5-5")
    calls = []

    def fake_stream(**kwargs):
        calls.append(kwargs)
        return _FakeStream(["Every 5 ", "seconds [1]."])

    monkeypatch.setattr(answerer.client.messages, "stream", fake_stream)
    assert "".join(answerer.stream("How often are heartbeats sent?", HITS)) == "Every 5 seconds [1]."
    [kwargs] = calls
    assert kwargs["model"] == "claude-haiku-5-5"
    assert kwargs["system"] == SYSTEM_PROMPT
    content = kwargs["messages"][0]["content"]
    assert '<source id="1" document="retries.md"' in content
    assert content.endswith("Question: How often are heartbeats sent?")
