"""Run the action's Bash entrypoint against a stub CLI, without publishing."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest

ACTION = Path(__file__).resolve().parents[1] / 'action.yaml'
SCRIPT = textwrap.dedent(ACTION.read_text().split('      run: |\n')[-1])


class ActionTests(unittest.TestCase):
    def run_action(self, command='release', overrides=None, error='', output=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stub = root / 'release-plz'
            stub.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
Path(os.environ['CALL_LOG']).write_text(json.dumps({'args': sys.argv[1:], 'target': os.getenv('CARGO_BUILD_TARGET')}))
if os.environ['CLI_ERROR']:
    print(os.environ['CLI_ERROR'], file=sys.stderr)
    sys.exit(7)
print(os.environ['CLI_OUTPUT'])
''')
            stub.chmod(0o755)
            env = os.environ.copy()
            for key in ['CARGO_BUILD_TARGET', 'RELEASE_PLZ_BUILD_ARCH']:
                env.pop(key, None)
            env.update({key: '' for key in ['RELEASE_PLZ_CONFIG', 'RELEASE_PLZ_TOKEN',
                        'RELEASE_PLZ_MANIFEST_PATH', 'RELEASE_PLZ_VERBOSE',
                        'RELEASE_PLZ_DRY_RUN', 'RELEASE_PLZ_TARGET']})
            env.update(PATH=str(root) + os.pathsep + env['PATH'],
                       RELEASE_PLZ_COMMAND=command, GITHUB_TOKEN='test-token',
                       GITHUB_REPOSITORY='near/example', GITHUB_OUTPUT=str(root/'outputs'),
                       CALL_LOG=str(root/'call'), CLI_ERROR=error,
                       CLI_OUTPUT=json.dumps(output or {'prs': [], 'releases': []}))
            env.update(overrides or {})
            result = subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', SCRIPT],
                                    env=env, cwd=root, capture_output=True, text=True)
            call = json.loads((root/'call').read_text()) if (root/'call').exists() else None
            outputs = (root/'outputs').read_text() if (root/'outputs').exists() else ''
            self.assertFalse((root/'injected').exists())
            return result, call, outputs

    def test_native_and_configured_targets(self):
        for command in ['release', 'release-pr']:
            for overrides, target in [({}, None), ({'CARGO_BUILD_TARGET':'existing'}, 'existing'),
                ({'RELEASE_PLZ_BUILD_ARCH':'fallback'}, 'fallback'),
                ({'RELEASE_PLZ_TARGET':'explicit', 'RELEASE_PLZ_BUILD_ARCH':'fallback'}, 'explicit')]:
                with self.subTest(command=command, target=target):
                    result, call, _ = self.run_action(command, overrides)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(call['target'], target)

    def test_boolean_flags(self):
        for value in ['', 'false', 'true']:
            for command in ['release', 'release-pr']:
                with self.subTest(value=value, command=command):
                    result, call, _ = self.run_action(command, {'RELEASE_PLZ_VERBOSE':value,
                                                              'RELEASE_PLZ_DRY_RUN':value})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual('-v' in call['args'], value == 'true')
                    self.assertEqual('--dry-run' in call['args'], value == 'true' and command == 'release')

    def test_inputs_remain_literal_arguments(self):
        literal = 'path with spaces $(touch injected) `touch injected` "quote"'
        result, call, _ = self.run_action(overrides={'RELEASE_PLZ_CONFIG':literal,
            'RELEASE_PLZ_MANIFEST_PATH':literal, 'RELEASE_PLZ_TOKEN':literal})
        self.assertEqual(result.returncode, 0, result.stderr)
        for flag in ['--config', '--manifest-path', '--token']:
            self.assertEqual(call['args'][call['args'].index(flag)+1], literal)

    def test_cli_errors_fail_including_422(self):
        for command in ['release', 'release-pr']:
            for error in ['HTTP 422: validation failed', 'HTTP 403: forbidden']:
                with self.subTest(command=command, error=error):
                    result, _, outputs = self.run_action(command, error=error)
                    self.assertEqual(result.returncode, 7)
                    self.assertIn(error, result.stderr)
                    self.assertEqual(outputs, '')

    def test_outputs_and_noop(self):
        for command, field in [('release', 'releases'), ('release-pr', 'prs')]:
            for items in [[], [{'number': 1}]]:
                result, _, outputs = self.run_action(command, output={field:items})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'{field}_created={str(bool(items)).lower()}\n', outputs)
                if command == 'release-pr':
                    self.assertIn('pr=' + ('{"number":1}' if items else '{}') + '\n', outputs)

    def test_unknown_command_fails(self):
        result, call, _ = self.run_action('unsupported')
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNone(call)


if __name__ == '__main__':
    unittest.main()
