
import time
import threading

from fabric.api import env, run, sudo, cd

env.hosts = ['login.tools.wmflabs.org']
env.sudo_prefix = "sudo -ni -p '%(sudo_prompt)s' "

# $(kubectl get pods -l name=montage-dev -o jsonpath='{.items[0].metadata.name}')


def deploy():
    result = run('whoami')
    prefix = run('cat /etc/wmflabs-project').stdout.strip()

    # TODO: control env here
    username = '%s.%s' % (prefix, 'montage-dev')
    env.sudo_user = username

    result = sudo('whoami')

    with cd('montage'):
        out = sudo('git pull')
        # i think the following might be redundant with fabric's own behavior
        assert out.succeeded, 'git pull failed'
        assert out.stderr == '', 'stderr present: %s' % out.stderr


    def _interactive_steps():
        time.sleep(10)
        pip_upgrade_cmd = ("kubectl exec interactive"
                           " -- www/python/venv/bin/pip install --upgrade -r montage/requirements.txt")
        sudo(pip_upgrade_cmd)
        sudo('kubectl delete pod interactive')

    # couldn't figure out a non-brittle* way of starting up a shell
    # pod in the background. so, we background it here and sleep to
    # give time for the pod to come up and get deleted.

    # *non-brittle = not reimplementing the internals of the
    # webservice command
    th = threading.Thread(target=_interactive_steps)
    th.start()

    sudo('webservice python2 shell', pty=True)
    time.sleep(3)

    sudo("webservice python2 restart")
