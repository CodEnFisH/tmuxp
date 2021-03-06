# -*- coding: utf-8 -*-
"""Configuration parsing and export for tmuxp.

tmuxp.config
~~~~~~~~~~~~

"""
from __future__ import absolute_import, division, print_function, \
    with_statement, unicode_literals

import os
import copy
import logging

from . import exc
from ._compat import string_types

logger = logging.getLogger(__name__)


def validate_schema(sconf):
    """Return True if config schema is correct.

    :param sconf: session configuration
    :type sconf: dict
    :rtype: bool

    """

    # verify session_name
    if not 'session_name' in sconf:
        raise exc.ConfigError('config requires "session_name"')

    if not 'windows' in sconf:
        raise exc.ConfigError('config requires list of "windows"')

    for window in sconf['windows']:
        if not 'window_name' in window:
            raise exc.ConfigError('config window is missing "window_name"')

        if not 'panes' in window:
            raise exc.ConfigError(
                'config window %s requires list of panes' %
                window['window_name']
            )

    return True


def is_config_file(filename, extensions=['.yml', '.yaml', '.json']):
    """Return True if file has a valid config file type.

    :param filename: filename to check (e.g. ``mysession.json``).
    :type filename: string
    :param extensions: filetypes to check (e.g. ``['.yaml', '.json']``).
    :type extensions: list or string
    :rtype: bool

    """

    extensions = [extensions] if isinstance(
        extensions, string_types) else extensions
    return any(filename.endswith(e) for e in extensions)


def in_dir(
    config_dir=os.path.expanduser('~/.tmuxp'),
    extensions=['.yml', '.yaml', '.json']
):
    """Return a list of configs in ``config_dir``.

    :param config_dir: directory to search
    :type config_dir: string
    :param extensions: filetypes to check (e.g. ``['.yaml', '.json']``).
    :type extensions: list
    :rtype: list

    """
    configs = []

    for filename in os.listdir(config_dir):
        if is_config_file(filename, extensions) and \
           not filename.startswith('.'):
            configs.append(filename)

    return configs


def in_cwd():
    """Return list of configs in current working directory.

    If filename is ``.tmuxp.py``, ``.tmuxp.json``, ``.tmuxp.yaml``.

    :rtype: list

    """
    configs = []

    for filename in os.listdir(os.getcwd()):
        if filename.startswith('.tmuxp') and is_config_file(filename):
            configs.append(filename)

    return configs

def expandpath(_path):
    """Return expanded path based on user's ``$HOME`` and ``env``.

    :py:func:`os.path.expanduser` and :py:func:`os.path.expandvars`

    :param _path: path to expand
    :type _path: string
    :returns: expanded path
    :rtype: string

    """
    return os.path.expandvars(os.path.expanduser(_path))

def inline(sconf):
    """ Return config in inline form, opposite of :meth:`config.expand`.

    :param sconf: unexpanded config file
    :type sconf: dict
    :rtype: dict

    """

    if (
        'shell_command' in sconf and
        isinstance(sconf['shell_command'], list) and
        len(sconf['shell_command']) == 1
    ):
        sconf['shell_command'] = sconf['shell_command'][0]

        if len(sconf.keys()) == int(1):
            sconf = sconf['shell_command']
    if (
        'shell_command_before' in sconf and
        isinstance(sconf['shell_command_before'], list) and
        len(sconf['shell_command_before']) == 1
    ):
        sconf['shell_command_before'] = sconf['shell_command_before'][0]

    # recurse into window and pane config items
    if 'windows' in sconf:
        sconf['windows'] = [
            inline(window) for window in sconf['windows']
        ]
    if 'panes' in sconf:
        sconf['panes'] = [inline(pane) for pane in sconf['panes']]

    return sconf


def expand(sconf, cwd=None, parent=None):
    """Return config with shorthand and inline properties expanded.

    This is necessary to keep the code in the :class:`WorkspaceBuilder` clean
    and also allow for neat, short-hand configurations.

    As a simple example, internally, tmuxp expects that config options
    like ``shell_command`` are a list (array)::

        'shell_command': ['htop']

    tmuxp configs allow for it to be simply a string::

        'shell_command': 'htop'

    Kaptan will load JSON/YAML files into python dicts for you.

    :param sconf: the configuration for the session
    :type sconf: dict
    :param cwd: directory to expand relative paths against. should be the dir
                of the config directory.
    :rtype: dict

    """

    # Note: cli.py will expand configs relative to project's config directory
    # for the first cwd argument.
    if not cwd:
        cwd = os.getcwd()

    # Any config section, session, window, pane that can contain the
    # 'shell_command' value
    if 'start_directory' in sconf:
        sconf['start_directory'] = expandpath(sconf['start_directory'])
        start_path = sconf['start_directory']
        if any(start_path.startswith(a) for a in ['.', './']):
            # if window has a session, or pane has a window with a
            # start_directory of . or ./, make sure the start_directory can be
            # relative to the parent.
            #
            # This is for the case where you may be loading a config from
            # outside your shell current directory.
            if parent:
                cwd = parent['start_directory']
            start_path = os.path.normpath(os.path.join(cwd, start_path))
            sconf['start_directory'] = start_path


    if 'before_script' in sconf:
        before_script = sconf['before_script']
        if any(before_script.startswith(a) for a in ['.', './']):
            before_script = os.path.normpath(os.path.join(cwd, before_script))
            sconf['before_script'] = before_script

    if (
        'shell_command' in sconf and
        isinstance(sconf['shell_command'], string_types)
    ):
        sconf['shell_command'] = [sconf['shell_command']]

    if (
        'shell_command_before' in sconf and
        isinstance(sconf['shell_command_before'], string_types)
    ):
        sconf['shell_command_before'] = [sconf['shell_command_before']]

    # recurse into window and pane config items
    if 'windows' in sconf:
        sconf['windows'] = [
            expand(window, parent=sconf) for window in sconf['windows']
        ]
    elif 'panes' in sconf:

        for pconf in sconf['panes']:
            p_index = sconf['panes'].index(pconf)
            p = copy.deepcopy(pconf)
            pconf = sconf['panes'][p_index] = {}

            if isinstance(p, string_types):
                p = {
                    'shell_command': [p]
                }
            elif not p:
                p = {
                    'shell_command': []
                }

            assert isinstance(p, dict)
            if 'shell_command' in p:
                cmd = p['shell_command']

                if isinstance(p['shell_command'], string_types):
                    cmd = [cmd]

                if not cmd or any(a == cmd for a in [None, 'blank', 'pane']):
                    cmd = []

                if isinstance(cmd, list) and len(cmd) == int(1):
                    if any(a in cmd for a in [None, 'blank', 'pane']):
                        cmd = []

                p['shell_command'] = cmd
            else:
                p['shell_command'] = []

            pconf.update(p)
        sconf['panes'] = [expand(pane, parent=sconf) for pane in sconf['panes']]

    return sconf


def trickle(sconf):
    """Return a dict with "trickled down" / inherited config values.

    This will only work if config has been expanded to full form with
    :meth:`config.expand`.

    tmuxp allows certain commands to be default at the session, window
    level. shell_command_before trickles down and prepends the
    ``shell_command`` for the pane.

    :param sconf: the session configuration
    :type sconf: dict
    :rtype: dict

    """

    # prepends a pane's ``shell_command`` list with the window and sessions'
    # ``shell_command_before``.

    if 'start_directory' in sconf:
        session_start_directory = sconf['start_directory']
    else:
        session_start_directory = None

    for windowconfig in sconf['windows']:

        # Prepend start_directory to relative window commands
        if session_start_directory:
            if not 'start_directory' in windowconfig:
                windowconfig['start_directory'] = session_start_directory
            else:
                if not any(
                    windowconfig['start_directory'].startswith(a)
                    for a in ['~', '/']
                ):
                    window_start_path = os.path.join(
                        session_start_directory, windowconfig['start_directory']
                    )
                    windowconfig['start_directory'] = window_start_path

        for paneconfig in windowconfig['panes']:
            commands_before = []

            # Prepend shell_command_before to commands
            if 'shell_command_before' in sconf:
                commands_before.extend(sconf['shell_command_before'])
            if 'shell_command_before' in windowconfig:
                commands_before.extend(windowconfig['shell_command_before'])
            if 'shell_command_before' in paneconfig:
                commands_before.extend(paneconfig['shell_command_before'])

            if 'shell_command' in paneconfig:
                commands_before.extend(paneconfig['shell_command'])

            p_index = windowconfig['panes'].index(paneconfig)
            windowconfig['panes'][p_index]['shell_command'] = commands_before
            #paneconfig['shell_command'] = commands_before

    return sconf


def import_tmuxinator(sconf):
    """Return tmuxp config from a `tmuxinator`_ yaml config.

    .. _tmuxinator: https://github.com/aziz/tmuxinator

    :param sconf: python dict for session configuration
    :type sconf: dict
    :rtype: dict

    """

    tmuxp_config = {}

    if 'project_name' in sconf:
        tmuxp_config['session_name'] = sconf.pop('project_name')
    elif 'name' in sconf:
        tmuxp_config['session_name'] = sconf.pop('name')
    else:
        tmuxp_config['session_name'] = None

    if 'project_root' in sconf:
        tmuxp_config['start_directory'] = sconf.pop('project_root')

    if 'cli_args' in sconf:
        tmuxp_config['config'] = sconf['cli_args']

        if '-f' in tmuxp_config['config']:
            tmuxp_config['config'] = tmuxp_config[
                'config'
            ].replace('-f', '').strip()
    elif 'tmux_options' in sconf:
        tmuxp_config['config'] = sconf['tmux_options']

        if '-f' in tmuxp_config['config']:
            tmuxp_config['config'] = tmuxp_config[
                'config'
            ].replace('-f', '').strip()

    if 'socket_name' in sconf:
        tmuxp_config['socket_name'] = sconf['socket_name']

    tmuxp_config['windows'] = []

    if 'tabs' in sconf:
        sconf['windows'] = sconf.pop('tabs')

    if 'pre' in sconf and 'pre_window' in sconf:
        tmuxp_config['shell_command'] = sconf['pre']

        if isinstance(sconf['pre'], string_types):
            tmuxp_config['shell_command_before'] = [sconf['pre_window']]
        else:
            tmuxp_config['shell_command_before'] = sconf['pre_window']
    elif 'pre' in sconf:
        if isinstance(sconf['pre'], string_types):
            tmuxp_config['shell_command_before'] = [sconf['pre']]
        else:
            tmuxp_config['shell_command_before'] = sconf['pre']

    if 'rbenv' in sconf:
        if 'shell_command_before' not in tmuxp_config:
            tmuxp_config['shell_command_before'] = []
        tmuxp_config['shell_command_before'].append(
            'rbenv shell %s' % sconf['rbenv']
        )

    for w in sconf['windows']:
        for k, v in w.items():

            windowdict = {}

            windowdict['window_name'] = k

            if isinstance(v, string_types) or v is None:
                windowdict['panes'] = [v]
                tmuxp_config['windows'].append(windowdict)
                continue
            elif isinstance(v, list):
                windowdict['panes'] = v
                tmuxp_config['windows'].append(windowdict)
                continue

            if 'pre' in v:
                windowdict['shell_command_before'] = v['pre']
            if 'panes' in v:
                windowdict['panes'] = v['panes']

            if 'layout' in v:
                windowdict['layout'] = v['layout']
            tmuxp_config['windows'].append(windowdict)
    return tmuxp_config


def import_teamocil(sconf):
    """Return tmuxp config from a `teamocil`_ yaml config.

    .. _teamocil: https://github.com/remiprev/teamocil

    :todo: change  'root' to a cd or start_directory
    :todo: width in pane -> main-pain-width
    :todo: with_env_var
    :todo: clear
    :todo: cmd_separator

    :param sconf: python dict for session configuration
    :type sconf: dict

    """

    tmuxp_config = {}

    if 'session' in sconf:
        sconf = sconf['session']

    if 'name' in sconf:
        tmuxp_config['session_name'] = sconf['name']
    else:
        tmuxp_config['session_name'] = None

    if 'root' in sconf:
        tmuxp_config['start_directory'] = sconf.pop('root')

    tmuxp_config['windows'] = []

    for w in sconf['windows']:

        windowdict = {}

        windowdict['window_name'] = w['name']
        if 'clear' in w:
            windowdict['clear'] = w['clear']

        if 'filters' in w:
            if 'before' in w['filters']:
                for b in w['filters']['before']:
                    windowdict['shell_command_before'] = w['filters']['before']
            if 'after' in w['filters']:
                for b in w['filters']['after']:
                    windowdict['shell_command_after'] = w['filters']['after']

        if 'root' in w:
            windowdict['start_directory'] = w.pop('root')

        if 'splits' in w:
            w['panes'] = w.pop('splits')

        if 'panes' in w:
            for p in w['panes']:
                if 'cmd' in p:
                    p['shell_command'] = p.pop('cmd')
                if 'width' in p:
                    # todo support for height/width
                    p.pop('width')
            windowdict['panes'] = w['panes']

        if 'layout' in w:
            windowdict['layout'] = w['layout']
        tmuxp_config['windows'].append(windowdict)

    return tmuxp_config
