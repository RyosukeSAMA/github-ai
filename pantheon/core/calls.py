"""Request-local attribution and optional incremental text delivery."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

CALL_TAGS = ContextVar('pantheon_call_tags', default={})
TEXT_SINK = ContextVar('pantheon_text_sink', default=None)
RECORDED = ContextVar('pantheon_usage_recorded', default=False)
CALL_STATE = ContextVar('pantheon_call_state', default='reported')
_KEEP = object()


@contextmanager
def call_scope(role='', phase='', sink=_KEEP):
    previous = CALL_TAGS.get()
    tags = CALL_TAGS.set({**previous, **({'role': role} if role else {}), **({'phase': phase} if phase else {})})
    stream = TEXT_SINK.set(sink) if sink is not _KEEP else None
    try:
        yield
    finally:
        if stream is not None:
            TEXT_SINK.reset(stream)
        CALL_TAGS.reset(tags)


def stage(role, phase, *, stream=True):
    def decorate(fn):
        @wraps(fn)
        def run(*args, **kwargs):
            with call_scope(role, phase, sink=_KEEP if stream else None):
                return fn(*args, **kwargs)
        return run
    return decorate


def text_delta(text):
    sink = TEXT_SINK.get()
    if callable(sink) and text:
        sink(str(text))
