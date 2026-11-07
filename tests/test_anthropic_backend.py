"""Offline Anthropic default and thinking-block compatibility checks."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents.backends import Backend, model_name


class FakeMessages:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return next(self.responses)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def response(*content, stop_reason='end_turn'):
    return SimpleNamespace(content=list(content), stop_reason=stop_reason)


def text(value):
    return SimpleNamespace(type='text', text=value)


def thinking():
    return SimpleNamespace(type='thinking', thinking='', signature='signature')


class AnthropicBackendTests(unittest.TestCase):
    def test_default_and_explicit_overrides(self):
        with patch.dict(os.environ, {'COMPLIANCE_MODEL': ''}):
            self.assertEqual(model_name('anthropic'), 'claude-haiku-5-5')
            self.assertEqual(model_name('anthropic', 'custom-model'), 'custom-model')
            self.assertEqual(model_name('ollama'), 'gemma4:26b')
        with patch.dict(os.environ, {'COMPLIANCE_MODEL': 'configured-model'}):
            self.assertEqual(model_name('anthropic'), 'configured-model')
            self.assertEqual(model_name('anthropic', 'custom-model'), 'custom-model')

    def test_plain_completion_selects_text_after_thinking(self):
        client = FakeClient([response(thinking(), text(' first '), text('second '))])
        with patch.dict(os.environ, {'COMPLIANCE_MODEL': ''}):
            result = Backend('anthropic', client=client).complete('system', [])
        self.assertEqual(result, 'first second')
        self.assertEqual(client.messages.requests[0]['model'], 'claude-haiku-5-5')

    def test_tool_loop_replays_thinking_and_selects_final_text(self):
        thought = thinking()
        tool = SimpleNamespace(type='tool_use', name='ybs_evaluate', input={'case': {}}, id='call-1')
        client = FakeClient([response(thought, tool, stop_reason='tool_use'),
                             response(thinking(), text('narrative'))])
        calls = []
        spec = {'name': 'ybs_evaluate', 'description': 'evaluate', 'inputSchema': {'type': 'object'}}
        backend = Backend('anthropic', 'claude-haiku-5-5', client=client)
        result = backend.complete_with_tool('system', [], spec, lambda *_: {'decision_id': 'd'}, calls)
        self.assertEqual(result, 'narrative')
        self.assertIs(client.messages.requests[1]['messages'][0]['content'][0], thought)
        self.assertEqual(client.messages.requests[0]['tool_choice']['type'], 'tool')
        self.assertEqual(len(calls), 1)

    def test_seeded_completion_selects_text_after_thinking(self):
        client = FakeClient([response(thinking(), text('narrative'))])
        backend = Backend('anthropic', 'claude-haiku-5-5', client=client)
        spec = {'name': 'ybs_evaluate', 'description': 'evaluate', 'inputSchema': {'type': 'object'}}
        result = backend.complete_seeded('system', [], spec, lambda *_: {}, [], {'case': {}}, {'decision_id': 'd'})
        self.assertEqual(result, 'narrative')
        self.assertEqual(client.messages.requests[0]['messages'][0]['content'][0]['type'], 'tool_use')

    def test_refusal_context_exhaustion_and_thinking_only_fail_explicitly(self):
        for answer in (response(thinking()), response(text('partial'), stop_reason='refusal'),
                       response(text('partial'), stop_reason='model_context_window_exceeded')):
            with self.subTest(stop_reason=answer.stop_reason):
                backend = Backend('anthropic', 'claude-haiku-5-5', client=FakeClient([answer]))
                with self.assertRaises(RuntimeError):
                    backend.complete('system', [])


if __name__ == '__main__':
    unittest.main()
