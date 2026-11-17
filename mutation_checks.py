"""Temporary fork-only acceptance experiment; never committed to the implementation branch."""
import pathlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

root = pathlib.Path(__file__).resolve().parent
results = root / 'mutation-results'
results.mkdir(exist_ok=True)


def run(command, name, cwd):
    completed = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (results / (name + '.log')).write_text(completed.stdout)
    print(name, 'exit', completed.returncode, flush=True)
    print(completed.stdout[-3000:], flush=True)
    return completed


if sys.argv[1] == 'swift':
    path = root / 'ios/DownloadManagerKit/Sources/DownloadManagerKit/DownloadManager.swift'
    original = path.read_text()
    needle = 'let request = Self.request(for: record, userAgent: await userAgentHolder.value)'
    assert original.count(needle) == 2
    command = ['swift', 'test', '--package-path', 'ios/DownloadManagerKit', '--filter', 'DownloadRequestPolicyTests']
    assert run(command, 'swift-baseline', root).returncode == 0
    for index, name in enumerate(['start', 'resume']):
        pieces = original.split(needle)
        mutated = pieces[0] + ('let request = URLRequest(url: record.url)' if index == 0 else needle) + pieces[1]
        mutated += ('let request = URLRequest(url: record.url)' if index == 1 else needle) + pieces[2]
        try:
            path.write_text(mutated)
            result = run(command, 'swift-' + name, root)
            method = 'testStartAppliesStoredPolicyAndUserAgent' if index == 0 else 'testResumeWithoutDataAppliesStoredPolicyAndUserAgent'
            assert result.returncode != 0
            assert any(method in line and 'failed' in line for line in result.stdout.splitlines())
            assert 'XCTAssertEqual failed' in result.stdout
        finally:
            path.write_text(original)
    assert run(command, 'swift-restored', root).returncode == 0
else:
    manager = root / 'android/lib/src/main/java/org/silvermine/downloadmanager/DownloadManager.kt'
    plugin = root / 'android/src/main/java/org/silvermine/plugin/download/DownloadPlugin.kt'
    mutations = [
        ('remove-constraints', manager, '.setConstraints(constraintsFor(record.options))', '', ':lib',
         'org.silvermine.downloadmanager.DownloadRestartInstrumentedTest', 'startAppliesBothStoredNetworkPoliciesToQueuedWork'),
        ('default-policy', manager, 'constraintsFor(record.options)', 'constraintsFor(CreateOptions())', ':lib',
         'org.silvermine.downloadmanager.DownloadRestartInstrumentedTest', 'startAppliesBothStoredNetworkPoliciesToQueuedWork'),
        ('drop-bridge-options', plugin, 'downloadManager.create(path, url, options)', 'downloadManager.create(path, url)', '',
         'org.silvermine.plugin.download.DownloadPluginInstrumentedTest', 'createStartAndResumeKeepPolicyThroughPlugin'),
    ]
    for name, path, old, new, module, cls, method in mutations:
        original = path.read_text()
        assert original.count(old) == 1
        command = ['./gradlew', module + ':connectedDebugAndroidTest',
                   '-Pandroid.testInstrumentationRunnerArguments.class=' + cls + '#' + method]
        assert run(command, name + '-baseline', root / 'android').returncode == 0
        try:
            path.write_text(original.replace(old, new))
            result = run(command, name, root / 'android')
            assert result.returncode != 0
            report_root = root / ('android/lib' if module else 'android') / 'build/outputs/androidTest-results'
            found = False
            for report in report_root.rglob('TEST-*.xml'):
                shutil.copy2(report, results / (name + '-' + report.name))
                for case in ET.parse(report).iter('testcase'):
                    if case.get('name') != method:
                        continue
                    for failure in case.findall('failure'):
                        text = ''.join(failure.itertext()) + str(failure.attrib)
                        if 'AssertionError' in text or 'ComparisonFailure' in text:
                            found = True
            assert found, 'Expected an assertion failure in ' + method
        finally:
            path.write_text(original)
        assert run(command, name + '-restored', root / 'android').returncode == 0
print('All requested mutations were caught; restored code passes.', flush=True)
