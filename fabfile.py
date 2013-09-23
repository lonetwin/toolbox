#!/usr/bin/env python

from os.path import exists
from ConfigParser import ConfigParser

from fabric.api import env, sudo, abort, task, prompt
from fabric.contrib import files

# this can be configured in ~/.fabricrc using the string "user = lonetwin", it
# defaults to $USER
# env.user = 'lonetwin'

if exists('~/.ssh/config'):
    env.use_ssh_config = True

# - process config and load plugins
# XXX Note: Lack of error checks is intentional since we want the config module
# to be present and correct rather than tolerate errors

config = ConfigParser()
config.read('config.ini')
plugins = config.defaults().get('plugins', '')
for plugin in ( s.strip() for s in plugins.split(',')):
    if plugin:
        globals()[plugin] = __import__(plugin, fromlist=['*'])

# -----------------------------------------------------------------------------
# - common commands

@task
def grant_access(remote_user, ssh_pubkey=''):
    """ Grant ssh access as ``remote_user`` for key ``ssh_pubkey``

    * ssh_pubkey:   The ssh pubkey to setup
    * remote_user:  The remote user for which ssh access needs to be setup

    Usage: fab grant_access:<username>[<ssh_pubkey>]
        If ssh_pubkey is not provided, you would be prompted for it.
    """

    if not ssh_pubkey:
        ssh_pubkey = prompt("Please paste the ssh pubkey here: ",
                             validate=r'^ssh-.*$')
        ssh_pubkey = ssh_pubkey.strip()

    if not files.exists('/home/%s/.ssh' % remote_user, use_sudo=True):
        sudo('mkdir /home/%s/.ssh' % remote_user)

    if not files.exists('/home/%s/.ssh/authorized_keys' % remote_user, use_sudo=True):
        sudo('touch /home/%s/.ssh/authorized_keys' % remote_user)

    files.append(filename = '/home/%s/.ssh/authorized_keys' % remote_user,
                 text = ssh_pubkey, use_sudo = True)

    sudo('chmod 600 /home/%s/.ssh/authorized_keys' % remote_user)
    sudo('chmod 700 /home/%s/.ssh' % remote_user)
    sudo('chown -R %s:%s /home/%s/.ssh/' % (remote_user, remote_user, remote_user))


@task
def add_user(username):
    """ Add a user with ssh access (key should be present in the config file).

    * username: The username to be added.

    Usage: fab add_user:<username>
    """
    if username not in config.options('users'):
        abort("I don't have %s's ssh key" % username)

    sudo('grep -q %s /etc/passwd || useradd -m -s /bin/bash %s' % (username, username))

    grant_access(username, config.get('users', username))


@task
def set_sudo(username):
    """ Setup sudo access for an existing user

    * username: the existing user name

    Usage: fab set_sudo:<username>
    """
    sudo('cp /etc/sudoers /etc/sudoers~')
    files.append(filename = '/etc/sudoers',
                 text = '%s\tALL=(ALL)\tNOPASSWD: ALL' % username,
                 use_sudo = True)


@task
def add_with_sudo(username):
    """ Add a user with ssh access and sudo privileges (key should be present in the config file).

    * username: The username to be added.

    Usage: fab add_with_sudo:<username>
    """
    add_user(username)
    set_sudo(username)


@task
def svc_reload(service='apache2', restart=0):
    """ Restart or reload a service.

    * service: service name to restart or reload
    * restart: Defaults to ``0``, which implies ``reload``, any other value
               implies ``restart``

    Usage: fab svc_reload[:[apache2|squid3][,1]]
    """
    action = 'reload' if restart == 0 else 'restart'
    sudo('service %s %s' % (service, action))

