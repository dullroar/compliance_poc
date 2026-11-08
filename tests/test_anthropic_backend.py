"""Offline Anthropic default and thinking-block compatibility checks."""
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agents.backends import Backend, model_name
from compliance_common.tools import TOOL_FIRST_MARKER, rejects_forced_tool_choice, tool_first_instruction


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


# Request bodies for claude-haiku-5-5 as sent before plans/archive/tune-ais step 01 (captured from the code at that commit, canonical JSON).
HAIKU_FIRST = ('{"max_tokens":16384,"messages":[{"content":"hi","role":"user"}],"model":"claude-haiku-5-5","output_config":{"effort":"low"},'
               '"system":"SYSTEM TEXT","tool_choice":{"disable_parallel_tool_use":true,"name":"ybs_evaluate","type":"tool"},'
               '"tools":[{"description":"evaluate","input_schema":{"type":"object"},"name":"ybs_evaluate"}]}')
HAIKU_SECOND = ('{"max_tokens":16384,"messages":[{"content":"hi","role":"user"},{"content":[{"id":"call-1","input":{"case":{}},"name":"ybs_evaluate",'
                '"type":"tool_use"}],"role":"assistant"},{"content":[{"content":"{\\"decision_id\\": \\"d\\"}","tool_use_id":"call-1","type":"tool_result"}],'
                '"role":"user"}],"model":"claude-haiku-5-5","output_config":{"effort":"low"},"system":"SYSTEM TEXT",'
                '"tool_choice":{"disable_parallel_tool_use":true,"type":"auto"},"tools":[{"description":"evaluate","input_schema":{"type":"object"},'
                '"name":"ybs_evaluate"}]}')
HAIKU_SEEDED = ('{"max_tokens":16384,"messages":[{"content":"hi","role":"user"},{"content":[{"id":"toolu_seeded_1","input":{"case":{}},'
                '"name":"ybs_evaluate","type":"tool_use"}],"role":"assistant"},{"content":[{"content":"{\\"decision_id\\": \\"d\\"}",'
                '"tool_use_id":"toolu_seeded_1","type":"tool_result"}],"role":"user"}],"model":"claude-haiku-5-5","output_config":{"effort":"low"},'
                '"system":"SYSTEM TEXT","tool_choice":{"disable_parallel_tool_use":true,"type":"auto"},'
                '"tools":[{"description":"evaluate","input_schema":{"type":"object"},"name":"ybs_evaluate"}]}')
SPEC = {'name': 'ybs_evaluate', 'description': 'evaluate', 'inputSchema': {'type': 'object'}}
REJECTING = ('claude-sonnet-5-5', 'claude-opus-5-5', 'claude-fable-5-1')


class SnapshotMessages(FakeMessages):
    """Records each request as canonical JSON at call time (the loop later appends to the message list it passed)."""

    def create(self, **kwargs):
        self.requests.append(json.dumps(kwargs, sort_keys=True, separators=(',', ':'), default=vars))
        return next(self.responses)


def run_model_mode(model, answers, *, system='SYSTEM TEXT'):
    client = FakeClient([])
    client.messages = SnapshotMessages(answers)
    calls = []
    result = Backend('anthropic', model, client=client).complete_with_tool(
        system, [{'role': 'user', 'content': 'hi'}], SPEC, lambda *_: {'decision_id': 'd'}, calls)
    return client.messages.requests, calls, result


def tool_use():
    return SimpleNamespace(type='tool_use', name='ybs_evaluate', input={'case': {}}, id='call-1')


class ForcedToolChoiceByModelTests(unittest.TestCase):
    """Models that reject a forced tool_choice get `auto` plus an instruction naming the tool; every other model is unchanged."""

    def test_haiku_5_5_requests_are_byte_for_byte_what_they_were(self):
        requests, calls, result = run_model_mode('claude-haiku-5-5', [response(tool_use(), stop_reason='tool_use'), response(text('narrative'))])
        self.assertEqual(requests, [HAIKU_FIRST, HAIKU_SECOND])
        self.assertEqual((result, len(calls)), ('narrative', 1))
        client = FakeClient([])
        client.messages = SnapshotMessages([response(text('narrative'))])
        Backend('anthropic', 'claude-haiku-5-5', client=client).complete_seeded(
            'SYSTEM TEXT', [{'role': 'user', 'content': 'hi'}], SPEC, lambda *_: {}, [], {'case': {}}, {'decision_id': 'd'})
        self.assertEqual(client.messages.requests, [HAIKU_SEEDED])

    def test_models_that_reject_a_forced_choice_are_exactly_the_documented_ones(self):
        for model in REJECTING + ('claude-mythos-5-1',):
            self.assertTrue(rejects_forced_tool_choice(model), model)
        for model in ('claude-haiku-5-5', 'claude-haiku-4-5-20251001', 'claude-sonnet-4-6', 'claude-opus-5', 'claude-sonnet-5-50', 'custom-model', '', None):
            self.assertFalse(rejects_forced_tool_choice(model), model)

    def test_a_rejecting_model_is_never_sent_a_forced_choice_and_is_told_to_call_the_tool(self):
        for model in REJECTING:
            with self.subTest(model=model):
                requests, calls, result = run_model_mode(model, [response(tool_use(), stop_reason='tool_use'), response(text('narrative'))])
                first, second = map(json.loads, requests)
                self.assertEqual(first['tool_choice'], {'disable_parallel_tool_use': True, 'type': 'auto'})
                self.assertEqual(second['tool_choice'], first['tool_choice'])
                self.assertEqual(first['system'], 'SYSTEM TEXT' + tool_first_instruction('ybs_evaluate'))      # the repository prompt stays a prefix
                self.assertEqual(second['system'], first['system'])
                self.assertIn('ybs_evaluate', first['system'])
                self.assertIn(TOOL_FIRST_MARKER, first['system'])
                # everything else in the body is what Haiku sends, except the model id and the system suffix
                expected = json.loads(HAIKU_FIRST)
                expected.update(model=model, system=first['system'], tool_choice=first['tool_choice'])
                self.assertEqual(first, expected)
                self.assertEqual((result, len(calls)), ('narrative', 1))

    def test_a_rejecting_model_that_does_not_call_the_tool_returns_its_answer_for_the_runner_to_cover(self):
        requests, calls, result = run_model_mode('claude-sonnet-5-5', [response(text('prose answer'))])
        self.assertEqual((len(requests), calls, result), (1, [], 'prose answer'))

    def test_seeded_requests_need_no_instruction_and_differ_from_haikus_only_by_the_model_id(self):
        for model in REJECTING:
            with self.subTest(model=model):
                client = FakeClient([])
                client.messages = SnapshotMessages([response(text('narrative'))])
                Backend('anthropic', model, client=client).complete_seeded(
                    'SYSTEM TEXT', [{'role': 'user', 'content': 'hi'}], SPEC, lambda *_: {}, [], {'case': {}}, {'decision_id': 'd'})
                self.assertEqual(client.messages.requests, [HAIKU_SEEDED.replace('claude-haiku-5-5', model)])

    def test_other_models_keep_the_forced_first_call(self):
        for model in ('claude-haiku-4-5-20251001', 'claude-sonnet-4-6', 'custom-model'):
            with self.subTest(model=model):
                requests, _, _ = run_model_mode(model, [response(tool_use(), stop_reason='tool_use'), response(text('narrative'))])
                first = json.loads(requests[0])
                self.assertEqual(first['tool_choice']['type'], 'tool')
                self.assertEqual(first['system'], 'SYSTEM TEXT')

    def test_the_instruction_names_only_the_given_tool_and_asks_for_the_call_first(self):
        text_ = tool_first_instruction('hmda_evaluate')
        self.assertIn('hmda_evaluate', text_)
        self.assertNotIn('ybs_evaluate', text_)
        self.assertTrue(text_.startswith('\n\n'))          # appended after the prompt, never inside it


class AnthropicEffortDefaultTests(unittest.TestCase):
    """Claude 5-family narration asks for low effort so thinking does not consume the whole output cap."""
    SPEC = {'name': 'ybs_evaluate', 'description': 'evaluate', 'inputSchema': {'type': 'object'}}

    def test_every_anthropic_request_path_asks_for_low_effort_on_the_5_family(self):
        tool = SimpleNamespace(type='tool_use', name='ybs_evaluate', input={'case': {}}, id='call-1')
        for model in ('claude-haiku-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5'):
            with self.subTest(model=model):
                plain, looped, seeded = (FakeClient([response(text('a'))]), FakeClient([response(tool, stop_reason='tool_use'), response(text('a'))]),
                                         FakeClient([response(text('a'))]))
                Backend('anthropic', model, client=plain).complete('system', [])
                Backend('anthropic', model, client=looped).complete_with_tool('system', [], self.SPEC, lambda *_: {'decision_id': 'd'}, [])
                Backend('anthropic', model, client=seeded).complete_seeded('system', [], self.SPEC, lambda *_: {}, [], {'case': {}}, {'decision_id': 'd'})
                for client in (plain, looped, seeded):
                    for request in client.messages.requests:
                        self.assertEqual(request['output_config'], {'effort': 'low'})
                        self.assertEqual(request['max_tokens'], 16384)
                        self.assertNotIn('thinking', request)

    def test_the_anthropic_cap_is_larger_than_the_shared_one_and_the_other_providers_keep_theirs(self):
        from agents.backends import ANTHROPIC_MAX_TOKENS, MAX_TOKENS
        self.assertEqual((MAX_TOKENS, ANTHROPIC_MAX_TOKENS), (8192, 16384))

    def test_other_models_are_sent_no_effort_field(self):
        for model in ('custom-model', 'claude-sonnet-4-6', 'claude-haiku-4-5', ''):
            with self.subTest(model=model):
                client = FakeClient([response(text('a'))])
                Backend('anthropic', model or 'custom-model', client=client).complete('system', [])
                self.assertNotIn('output_config', client.messages.requests[0])
        from compliance_common.tools import anthropic_request_options
        self.assertEqual(anthropic_request_options(''), {})
        self.assertEqual(anthropic_request_options(None), {})


if __name__ == '__main__':
    unittest.main()
