"""Temporary fork-only checks; never added to the implementation branch."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
results = root / 'review-results'
results.mkdir()
command = ['swift', 'test', '--package-path', 'ios/DownloadManagerKit', '--filter', 'DownloadDelegateTests']

def run(name):
    result = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (results / (name + '.log')).write_text(result.stdout)
    print(name, 'exit', result.returncode, flush=True)
    print(result.stdout[-7000:], flush=True)
    return result

assert run('baseline').returncode == 0
sources = root / 'ios/DownloadManagerKit/Sources/DownloadManagerKit'
delegate = sources / 'DownloadSessionDelegate.swift'
handler = sources / 'BackgroundSessionHandler.swift'
guard = 'if let statusCode, !Self.isSuccessStatus(statusCode) { return }'
assert delegate.read_text().count(guard) == 1
original_handler = handler.read_text()
needle = 'completionHandler = nil'
assert original_handler.count(needle) == 2
mutations = [('remove-http-progress-guard', delegate, delegate.read_text().replace(guard, ''),
              'testHTTPErrorProgressIsIgnored')]
for index, name in enumerate(['retain-handler-after-pending-completion', 'retain-handler-after-completion']):
    parts = original_handler.split(needle)
    mutated = parts[0] + ('' if index == 0 else needle) + parts[1]
    mutated += ('' if index == 1 else needle) + parts[2]
    mutations.append((name, handler, mutated, 'testBackgroundHandlerSupportsBothArrivalOrders'))
for name, path, mutated, method in mutations:
    original = path.read_text()
    try:
        path.write_text(mutated)
        result = run(name)
        assert result.returncode != 0
        assert any(method in line and 'error:' in line for line in result.stdout.splitlines()), 'Expected test failure in ' + method
    finally:
        path.write_text(original)
    assert run(name + '-restored').returncode == 0
print('HTTP guard and both duplicate-callback regressions are caught; restored code passes.', flush=True)
