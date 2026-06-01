from xiaoman.loop import run_xiaoman_loop
from xiaoman.session import XiaomanSession


class SuccessfulLLM:
    provider = "test-provider"
    model = "test-model"

    def complete(self, messages, tools=None):
        return {
            "choices": [{"message": {"role": "assistant", "content": "hello"}}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
        }


class FailingLLM:
    provider = "test-provider"
    model = "test-model"

    def complete(self, messages, tools=None):
        raise TimeoutError("too slow")


def test_loop_reports_successful_llm_usage():
    events = []
    session = run_xiaoman_loop(
        XiaomanSession(),
        system_prompt="system",
        tools=[],
        llm_client=SuccessfulLLM(),
        on_usage=events.append,
    )

    assert session.cumulative_usage == 11
    assert events[0]["status"] == "success"
    assert events[0]["usage"]["prompt_tokens"] == 8


def test_loop_reports_failed_llm_usage():
    events = []
    try:
        run_xiaoman_loop(
            XiaomanSession(),
            system_prompt="system",
            tools=[],
            llm_client=FailingLLM(),
            on_usage=events.append,
        )
    except TimeoutError:
        pass
    else:
        raise AssertionError("the LLM failure should be propagated")

    assert events[0]["status"] == "error"
    assert events[0]["metadata"] == {"error_type": "TimeoutError"}
