"""Base class for LLM clients."""

from __future__ import annotations

import abc
import inspect
from functools import wraps
from typing import Any


class BaseLLMClient(abc.ABC):
    """Abstract base. All providers expose the same `complete()` interface."""

    default_model: str = ""
    provider_name: str = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        complete = cls.__dict__.get('complete')
        if complete is None:
            return
        signature = inspect.signature(complete)
        extras_name = next((name for name, parameter in signature.parameters.items()
                            if parameter.kind == inspect.Parameter.VAR_KEYWORD), 'kwargs')

        @wraps(complete)
        def guarded(self, messages, model='', system='', *args, **options):
            from types import SimpleNamespace

            from pantheon.core.budgets import RESERVATION
            from pantheon.core.calls import CALL_STATE, RECORDED, TEXT_SINK
            budget = getattr(self, 'budget', None)
            target = model or self.default_model
            bound = signature.bind(self, messages, model, system, *args, **options)
            recorded = RECORDED.set(False)
            reservation = None
            sent = False
            failed = False
            try:
                if budget is not None:
                    options = dict(bound.arguments.get(extras_name, {}))
                    responses = callable(getattr(self, '_uses_responses_api', None)) and self._uses_responses_api(target)
                    output = options.get('max_output_tokens', bound.arguments.get('max_tokens', options.get('max_tokens', 4096)))
                    identity, output = budget.reserve(self.provider_name, target, messages, system, int(output or 4096))
                    if responses:
                        options.pop('max_tokens', None)
                        options['max_output_tokens'] = output
                    elif 'max_tokens' in signature.parameters:
                        bound.arguments['max_tokens'] = output
                    else:
                        options['max_tokens'] = output
                    bound.arguments[extras_name] = options
                    reservation = RESERVATION.set((budget, identity))
                implementation = complete
                if self.streaming_enabled and callable(TEXT_SINK.get()) and callable(getattr(type(self), 'stream_complete', None)):
                    implementation = type(self).stream_complete
                sent = True
                return implementation(*bound.args, **bound.kwargs)
            except BaseException:
                failed = True
                raise
            finally:
                if sent and not RECORDED.get() and self.usage_recorder is not None:
                    state = CALL_STATE.set('failed' if failed else 'unmetered')
                    try:
                        self.usage_recorder(self.provider_name, target, SimpleNamespace(usage=None))
                    except Exception:
                        import logging
                        logging.getLogger(__name__).warning('Usage attempt could not be recorded')
                    finally:
                        CALL_STATE.reset(state)
                if reservation is not None:
                    RESERVATION.reset(reservation)
                RECORDED.reset(recorded)
        cls.complete = guarded

    def __init__(self, api_key: str = "", base_url: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.usage_recorder: Any = None
        self.budget: Any = None
        self.streaming_enabled = True

    def _record_usage(self, model: str, response: Any, *, responses_api: bool = False) -> None:
        from pantheon.core.budgets import RESERVATION
        from pantheon.core.calls import RECORDED
        RECORDED.set(True)
        reservation = RESERVATION.get()
        if reservation:
            try:
                reservation[0].settle(reservation[1], response, responses_api=responses_api)
            except Exception:
                import logging
                logging.getLogger(__name__).warning('Usage settlement unavailable; conservative budget reservation retained.')
        if self.usage_recorder is not None:
            try:
                self.usage_recorder(self.provider_name, model, response, responses_api=responses_api)
            except Exception:
                # Accounting must never turn a successful model answer into a failure.
                import logging
                logging.getLogger(__name__).exception("Failed to record model usage")

    @abc.abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        model: str,
        system: str = "",
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> str:
        """Call the LLM and return the assistant's text content.

        Args:
            messages: OpenAI-style messages [{"role": ..., "content": ...}, ...].
            model: The model ID to use.
            system: System prompt (separate field for Anthropic-style APIs).
            temperature: Sampling temperature.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{type(self).__name__} provider={self.provider_name} model={self.default_model}>"
