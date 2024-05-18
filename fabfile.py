
# NB 2024-05-17: Not currently using this for deploys, at least until this py3 stuff settles out -mh
# NB: this file requires fabric 3

import sys
import time
import atexit
import threading

from fabric.api import env, run, sudo, cd, local

env.hosts = ['login.tools.wmflabs.org']
env.sudo_prefix = "sudo -ni -p '%(sudo_prompt)s' "

# TODO
DEFAULT_TOOL = 'montage-dev'
DEFAULT_RELEASE_BRANCH = 'master'
SHELL_POD_NAME = 'interactive'  # this'll only change if the webservce command does
TOOL_IMAGE = 'python3.9' 
# TOOL_IMAGE is used in the restart command, but the real restart command (as of 2024-05-17) is:
# webservice --backend=kubernetes --cpu 1 --mem 4096Mi -r 2 python3.9 restart


# if you hit ctrl-c while ssh'd in, it kills the session, and if you
# were in the middle of pip installing packages, it will leave the
# interactive shell around. so we use atexit to clean up. (also gotta
# clean up stdin termios)
_SHELL_UP = False

old_termios_attrs = None
try:
    import termios
    import tty
    old_termios_attrs = termios.tcgetattr(sys.stdin)
except:
    pass

def _shutdown_shell():
    try:
        if _SHELL_UP:
            # host string has to be reset for some unknown reason.
            env.host_string = 'login.tools.wmflabs.org'
            env.sudo_prefix = "sudo -ni -p '%(sudo_prompt)s' "
            sudo('kubectl delete pod %s' % SHELL_POD_NAME)
    except SystemExit:
        pass

    if old_termios_attrs is not None:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_termios_attrs)
    return

atexit.register(_shutdown_shell)


def deploy(tool=DEFAULT_TOOL, branch=DEFAULT_RELEASE_BRANCH):
    cur_branch = local('git symbolic-ref --short HEAD', capture=True).stdout.strip()

    print()
    print(' ++ deploying %s to %s' % (branch, tool))
    if cur_branch != branch:
        print(' -- note that you are on %s' % cur_branch)
        time.sleep(3)
    print()

    res = local('git --no-pager log origin/{0}...{0}'.format(branch), capture=True)
    if res.stdout != '':
        raise SystemExit(' !! unpushed/unpulled commits on release branch %s,'
                         ' run git push, test, and try again.' % branch)

    time.sleep(3)
    result = run('whoami')
    prefix = run('cat /etc/wmflabs-project').stdout.strip()

    username = '%s.%s' % (prefix, tool)
    env.sudo_user = username

    result = sudo('whoami')
    assert result == username

    with cd('montage'):
        out = sudo('git checkout %s' % branch)
        out = sudo('git pull origin %s' % branch)


    def _webservice_shell_steps():
        global _SHELL_UP

        time.sleep(10)
        pip_upgrade_cmd = ("kubectl exec " + SHELL_POD_NAME +
                           " -- www/python/venv/bin/pip install --upgrade -r montage/requirements.txt")
        _SHELL_UP = True

        out = sudo(pip_upgrade_cmd)

        sudo('kubectl delete pod %s' % SHELL_POD_NAME)
        _SHELL_UP = False

        return

    # needed a non-brittle* way of starting up a shell
    # pod in the background. so, we background it here, and sleep to
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
