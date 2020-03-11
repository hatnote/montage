
import time
import threading

from fabric.api import env, run, sudo, cd, local

env.hosts = ['login.tools.wmflabs.org']
env.sudo_prefix = "sudo -ni -p '%(sudo_prompt)s' "

# TODO
RELEASE_BRANCH_NAME = 'master'
SHELL_POD_NAME = 'interactive'  # this'll only change if the webservce command does
TOOL_NAME = 'montage-dev'
TOOL_IMAGE = 'python2'

def deploy():

    res = local('git --no-pager log origin/{0}...{0}'.format(RELEASE_BRANCH_NAME))
    assert res.stdout == '', 'unpushed/unpulled commits on %s, run git push, test, and try again' % RELEASE_BRANCH_NAME

    result = run('whoami')
    prefix = run('cat /etc/wmflabs-project').stdout.strip()

    username = '%s.%s' % (prefix, TOOL_NAME)
    env.sudo_user = username

    result = sudo('whoami')
    assert result == username

    with cd('montage'):
        out = sudo('git checkout %s' % RELEASE_BRANCH_NAME)
        out = sudo('git pull origin %s' % RELEASE_BRANCH_NAME)


    def _webservice_shell_steps():
        time.sleep(10)
        pip_upgrade_cmd = ("kubectl exec " + SHELL_POD_NAME +
                           " -- www/python/venv/bin/pip install --upgrade -r montage/requirements.txt")
        sudo(pip_upgrade_cmd)
        sudo('kubectl delete pod %s' % SHELL_POD_NAME)

    # couldn't figure out a non-brittle* way of starting up a shell
    # pod in the background. so, we background it here and sleep to
    # give time for the pod to come up and get deleted.
    #
    # *non-brittle = not reimplementing the internals of the
    # webservice command
    th = threading.Thread(target=_webservice_shell_steps)
    th.start()

    sudo('webservice %s shell' % TOOL_IMAGE, pty=True)
    time.sleep(3)

    sudo("webservice %s restart" % TOOL_IMAGE)


# $(kubectl get pods -l name=montage-dev -o jsonpath='{.items[0].metadata.name}')
