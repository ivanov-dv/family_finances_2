"""Логика scripts/deploy.sh на заглушках kubectl, docker, ssh, sudo и k0s: порядок шагов и защитные проверки."""
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'scripts' / 'deploy.sh'

pytestmark = pytest.mark.skipif(shutil.which('bash') is None, reason='нужен bash')

KUBECTL = r'''#!/usr/bin/env bash
echo "kubectl $*" >> "$STUB_LOG"
case "$*" in
  *"get nodes"*) printf '%s\n' ${STUB_NODE_ARCHS:-amd64} ;;
  *"get job"*) echo "${STUB_JOB_STATUS-1||}" ;;
  *"apply -f -"*) grep 'image:' >> "$STUB_LOG" || true ;;
esac
exit 0
'''

DOCKER = r'''#!/usr/bin/env bash
echo "docker $*" >> "$STUB_LOG"
case "$*" in
  "version --format {{.Server.Arch}}") echo "${STUB_LOCAL_ARCH:-amd64}" ;;
  "version") [ -z "${STUB_NO_SERVER_DOCKER:-}" ] || exit 1 ;;
  "buildx version") [ -n "${STUB_BUILDX:-}" ] || exit 1 ;;
  "build "*|"buildx build "*) cat > /dev/null ;;
esac
exit 0
'''

# «Сервер» эмулируется локально: ssh выполняет удалённую команду через bash -c, а sudo и k0s — заглушки.
SSH = r'''#!/usr/bin/env bash
echo "ssh $*" >> "$STUB_LOG"
[ -z "${STUB_SSH_FAIL:-}" ] || { echo "ssh: connect to host failed" >&2; exit 255; }
while [ $# -gt 0 ]; do
  case "$1" in -o|-O|-i|-p|-l) shift 2 ;; -*) shift ;; *) break ;; esac
done
shift
exec bash -c "$*"
'''

SUDO = r'''#!/usr/bin/env bash
exec "$@"
'''

K0S = r'''#!/usr/bin/env bash
echo "k0s $*" >> "$STUB_LOG"
[ "$1" = "kubectl" ] && shift
exec kubectl "$@"
'''

MUTATING = ('docker build', 'docker push', 'kubectl delete', 'kubectl apply', 'kubectl rollout')


@pytest.fixture
def deploy(tmp_path):
    for name, body in (('kubectl', KUBECTL), ('docker', DOCKER), ('ssh', SSH), ('sudo', SUDO), ('k0s', K0S)):
        stub = tmp_path / name
        stub.write_text(body)
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / 'calls.log'

    def run(*args, **env):
        log.write_text('')
        full_env = {
            **os.environ,
            'PATH': f'{tmp_path}:{os.environ["PATH"]}',
            'STUB_LOG': str(log),
            **env,
        }
        result = subprocess.run(
            ['bash', str(SCRIPT), *args],
            capture_output=True, text=True, env=full_env, stdin=subprocess.DEVNULL, timeout=60,
        )
        return result, log.read_text().splitlines()

    return run


def index(calls, prefix):
    return next(i for i, call in enumerate(calls) if call.startswith(prefix))


def test_manifests_use_the_image_the_script_deploys():
    """Подстановка тега в deploy.sh рассчитана на «image: ivanovdv/ff2-django:latest» в манифестах."""
    manifests = [p.read_text() for p in (ROOT / 'k8s').glob('*.yaml')]
    assert sum(len(re.findall(r'image: ivanovdv/ff2-django:latest', text)) for text in manifests) == 2


def test_script_has_valid_bash_syntax():
    assert subprocess.run(['bash', '-n', str(SCRIPT)]).returncode == 0


class TestLocalKubectl:
    """Без --ssh скрипт использует обычный локальный kubectl."""

    def test_full_deploy_runs_migrations_before_restarting_the_app(self, deploy):
        result, calls = deploy('--yes', STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='amd64')
        assert result.returncode == 0, result.stderr
        order = [
            index(calls, 'docker build'),
            index(calls, 'docker push'),
            index(calls, 'kubectl delete job django-collectstatic'),
            index(calls, 'kubectl rollout restart deployment/ff2-django'),
            index(calls, 'kubectl rollout status deployment/ff2-django'),
        ]
        assert order == sorted(order)
        # Job применяется раньше Deployment: миграции готовы к моменту перезапуска приложения.
        applies = [i for i, call in enumerate(calls) if call.startswith('kubectl apply')]
        assert applies and applies[0] < index(calls, 'kubectl rollout restart')

    def test_failed_job_leaves_the_running_app_untouched(self, deploy):
        result, calls = deploy('--yes', STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='amd64',
                               STUB_JOB_STATUS='|1|True')
        assert result.returncode != 0
        assert 'прежняя версия' in result.stderr
        assert not any(call.startswith('kubectl rollout') for call in calls)
        assert not any('ff2-django:latest' in call and 'deployment' in call for call in calls)

    def test_refuses_cross_architecture_build_without_buildx(self, deploy):
        result, calls = deploy('--yes', STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='arm64')
        assert result.returncode != 0
        assert 'buildx' in result.stderr
        assert not any(call.startswith(('docker build ', 'docker push')) for call in calls)

    def test_dry_run_changes_nothing(self, deploy):
        result, calls = deploy('--dry-run', STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='amd64')
        assert result.returncode == 0, result.stderr
        assert not any(call.startswith(MUTATING) for call in calls)

    def test_rollback_pins_the_requested_tag_and_skips_the_build(self, deploy):
        result, calls = deploy('--yes', '--skip-build', '--tag', 'abc1234', STUB_NODE_ARCHS='amd64')
        assert result.returncode == 0, result.stderr
        images = [call.strip() for call in calls if call.strip().startswith('image:')]
        assert 'image: ivanovdv/ff2-django:abc1234' in images
        assert 'image: ivanovdv/ff2-django:latest' not in images
        assert not any(call.startswith('docker build') for call in calls)

    def test_tag_requires_skip_build(self, deploy):
        result, calls = deploy('--yes', '--tag', 'abc1234')
        assert result.returncode != 0
        assert not any(call.startswith(MUTATING) for call in calls)

    def test_refuses_without_confirmation_when_not_interactive(self, deploy):
        result, calls = deploy(STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='amd64')
        assert result.returncode != 0
        assert '--yes' in result.stderr
        assert not any(call.startswith(MUTATING) for call in calls)


class TestOverSsh:
    """С --ssh kubectl выполняется на сервере (k0s), локальный контекст кластера не нужен."""

    def test_kubectl_runs_on_the_server_through_k0s(self, deploy):
        result, calls = deploy('--yes', '--ssh', 'deploy@srv', STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='amd64')
        assert result.returncode == 0, result.stderr
        assert any(call.startswith('ssh ') and 'deploy@srv' in call for call in calls)
        kubectl_calls = [call for call in calls if call.startswith('kubectl ')]
        k0s_calls = [call for call in calls if call.startswith('k0s kubectl')]
        assert kubectl_calls and len(kubectl_calls) == len(k0s_calls)
        # Манифесты уходят на сервер через stdin, образ в них — из коммита.
        assert any(call.strip() == 'image: ivanovdv/ff2-django:latest' for call in calls)

    def test_migrations_still_run_before_the_restart(self, deploy):
        result, calls = deploy('--yes', '--ssh', 'deploy@srv', STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='amd64')
        assert result.returncode == 0, result.stderr
        assert index(calls, 'kubectl delete job') < index(calls, 'kubectl rollout restart')

    def test_failed_job_over_ssh_leaves_the_running_app_untouched(self, deploy):
        result, calls = deploy('--yes', '--ssh', 'deploy@srv', STUB_NODE_ARCHS='amd64',
                               STUB_LOCAL_ARCH='amd64', STUB_JOB_STATUS='|1|True')
        assert result.returncode != 0
        assert not any(call.startswith('kubectl rollout') for call in calls)

    def test_builds_on_the_server_when_this_machine_cannot(self, deploy):
        """Локальная arm64-машина и amd64-сервер без buildx: образ собирается на сервере."""
        result, calls = deploy('--yes', '--ssh', 'deploy@srv', STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='arm64')
        assert result.returncode == 0, result.stderr
        assert any(call.startswith('ssh ') and 'tar -x' in call for call in calls)  # контекст сборки передан на сервер
        remote_builds = [call for call in calls if call.startswith('ssh ') and 'docker build' in call]
        assert remote_builds and 'docker push' in remote_builds[0]

    def test_reports_missing_docker_on_the_server(self, deploy):
        result, calls = deploy('--yes', '--ssh', 'deploy@srv', '--build', 'server',
                               STUB_NODE_ARCHS='amd64', STUB_NO_SERVER_DOCKER='1')
        assert result.returncode != 0
        assert 'Docker' in result.stderr
        assert not any(call.startswith(MUTATING) for call in calls)

    def test_ssh_failure_stops_before_any_change(self, deploy):
        result, calls = deploy('--yes', '--ssh', 'deploy@srv', STUB_SSH_FAIL='1')
        assert result.returncode != 0
        assert 'SSH' in result.stderr
        assert not any(call.startswith(MUTATING) for call in calls)

    def test_dry_run_over_ssh_changes_nothing(self, deploy):
        result, calls = deploy('--dry-run', '--ssh', 'deploy@srv', STUB_NODE_ARCHS='amd64', STUB_LOCAL_ARCH='amd64')
        assert result.returncode == 0, result.stderr
        assert not any(call.startswith(MUTATING) for call in calls)

    def test_server_build_requires_ssh(self, deploy):
        result, calls = deploy('--yes', '--build', 'server')
        assert result.returncode != 0
        assert '--ssh' in result.stderr
