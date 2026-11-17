"""Temporary fork-only verification of the review correction."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
results = root / 'review-results'
results.mkdir()
source = root / 'ios/DownloadManagerKit/Sources/DownloadManagerKit/BackgroundSessionHandler.swift'
original = source.read_text()
command = ['swift', 'test', '--package-path', 'ios/DownloadManagerKit', '--filter', 'DownloadDelegateTests']

def run(name):
    result = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (results / (name + '.log')).write_text(result.stdout)
    print(name, 'exit', result.returncode, flush=True)
    print(result.stdout[-5000:], flush=True)
    return result

assert run('baseline').returncode == 0
needle = 'pendingComplete = true'
assert original.count(needle) == 1
try:
    source.write_text(original.replace(needle, 'pendingComplete = false'))
    result = run('drop-pending-completion')
    assert result.returncode != 0
    assert any('testBackgroundHandlerSupportsBothArrivalOrders' in line and 'Asynchronous wait failed' in line
               for line in result.stdout.splitlines()), 'Expected failure in the deterministic arrival-order test'
finally:
    source.write_text(original)
assert run('restored').returncode == 0
print('Dropped pending completion is caught; restored code passes.', flush=True)
