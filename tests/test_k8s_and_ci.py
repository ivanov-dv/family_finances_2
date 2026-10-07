"""Манифесты k8s и workflow CI: пробы и requests, раннер GitHub, выкладка через scripts/deploy.sh."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = yaml.safe_load((ROOT / '.github' / 'workflows' / 'main.yml').read_text(encoding='utf-8'))
TRIGGERS = WORKFLOW.get('on') or WORKFLOW.get(True)   # PyYAML читает ключ `on` как булево True


def deployments():
    docs = [doc for path in sorted((ROOT / 'k8s').glob('*.yaml')) for doc in yaml.safe_load_all(path.read_text(encoding='utf-8')) if doc]
    return {d['metadata']['name']: d['spec']['template']['spec']['containers'][0] for d in docs if d['kind'] == 'Deployment'}


class TestDeployments:

    def test_expected_deployments(self):
        assert set(deployments()) == {'ff2-django', 'ff2-nginx'}

    @pytest.mark.parametrize('name', ['ff2-django', 'ff2-nginx'])
    def test_have_probes_and_requests_but_no_limits(self, name):
        container = deployments()[name]
        assert 'readinessProbe' in container and 'livenessProbe' in container
        # limits нарочно нет: угаданный потолок памяти убивал бы под по OOM
        assert 'requests' in container['resources'] and 'limits' not in container['resources']

    @pytest.mark.parametrize('probe', ['readinessProbe', 'livenessProbe'])
    def test_django_probes_are_tcp(self, probe):
        """httpGet не подходит: kubelet шлёт Host с IP пода, а ALLOWED_HOSTS его отвергает."""
        spec = deployments()['ff2-django'][probe]
        assert spec['tcpSocket']['port'] == 8000 and 'httpGet' not in spec


class TestWorkflow:

    jobs = WORKFLOW['jobs']

    def test_triggers_are_pull_requests_and_manual_runs_only(self):
        assert set(TRIGGERS) == {'pull_request', 'workflow_dispatch'}
        assert TRIGGERS['pull_request']['branches'] == ['main']

    def test_no_self_hosted_runner(self):
        assert [name for name, job in self.jobs.items() if 'self-hosted' in str(job['runs-on'])] == []

    def test_tests_job_runs_flake8_and_pytest_against_postgres(self):
        job = self.jobs['tests']
        assert job['if'] == "github.event_name == 'pull_request'"
        assert job['services']['postgres']['image'].startswith('postgres:')
        assert job['services']['postgres']['ports'] == ['55432:5432']
        run = ' '.join(step.get('run', '') for step in job['steps'])
        assert 'poetry run flake8' in run and 'poetry run pytest' in run
        env = next(step['env'] for step in job['steps'] if step.get('name') == 'Flake8 and tests')
        assert str(env['POSTGRES_PORT']) == '55432' and env['ACCESS_TOKEN']

    def test_deploy_job_is_manual_and_uses_the_script(self):
        job = self.jobs['deploy']
        assert job['if'] == "github.event_name == 'workflow_dispatch'"
        run = ' '.join(step.get('run', '') for step in job['steps'])
        assert 'scripts/deploy.sh --ssh' in run and '--yes' in run

    def test_secrets_reach_shell_only_through_env(self):
        """`${{ secrets.X }}` прямо в run-строке — это подстановка текста в shell; передаём через env."""
        for job in self.jobs.values():
            for step in job['steps']:
                assert 'secrets.' not in step.get('run', ''), step.get('name')

    @pytest.mark.skipif(shutil.which('bash') is None, reason='нужен bash')
    def test_flags_used_by_the_workflow_exist_in_the_script(self):
        helptext = subprocess.run(['bash', str(ROOT / 'scripts' / 'deploy.sh'), '--help'],
                                  capture_output=True, text=True, timeout=30).stdout
        run = ' '.join(step.get('run', '') for step in self.jobs['deploy']['steps'])
        for flag in set(re.findall(r'(?<![\w-])--[a-z][a-z-]+', run)):
            assert flag in helptext, flag
        for variable in ('DOCKER_USERNAME', 'DOCKER_PASSWORD'):
            assert variable in helptext
