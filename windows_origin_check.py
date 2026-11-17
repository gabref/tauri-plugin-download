"""Verify the real Windows IPC origin and its regression sensitivity."""
from pathlib import Path
import subprocess

path = Path('src/ipc_tests.rs')
original = path.read_text()
command = ['cargo', 'test', '-p', 'tauri-plugin-download', '--lib', 'ipc_tests']
def run(name):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(name, 'exit', result.returncode, flush=True)
    print(result.stdout, flush=True)
    return result
assert run('windows-baseline').returncode == 0
needle = '"http://tauri.localhost"'
assert original.count(needle) == 1
try:
    path.write_text(original.replace(needle, '"tauri://localhost"'))
    result = run('windows-wrong-origin')
    assert result.returncode != 0
    assert 'test result: FAILED' in result.stdout and '3 failed' in result.stdout
    assert 'not allowed' in result.stdout.lower() or 'permission' in result.stdout.lower()
finally:
    path.write_text(original)
assert run('windows-restored').returncode == 0
print('All three IPC tests pass on Windows; reverting the origin fails their ACL checks.', flush=True)
