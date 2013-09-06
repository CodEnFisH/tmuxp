# -*- coding: utf8 - *-
"""
    tmuxwrapper.pane
    ~~~~~~~~~~~~~~~~

    tmuxwrapper helps you manage tmux workspaces.

    :copyright: Copyright 2013 Tony Narlock <tony@git-pull.com>.
    :license: BSD, see LICENSE for details
"""
from .util import live_tmux
from .formats import PANE_FORMATS
from sh import tmux
from logxtreme import logging
import collections


class Pane(collections.MutableMapping):
    '''
        ``tmux(1)`` pane

        ``tmux(1)`` holds a psuedoterm and linked to tmux windows.
    '''

    def __init__(self, **kwargs):
        self._session = None
        self._window = None

        #self._TMUX(**kwargs)
        self._TMUX = {}
        self.update(**kwargs)

    def __getitem__(self, key):
        return self._TMUX[key]

    def __setitem__(self, key, value):
        self._TMUX[key] = value
        self.dirty = True

    def __delitem__(self, key):
        del self._TMUX[key]
        self.dirty = True

    def keys(self):
        return self._TMUX.keys()

    def __iter__(self):
        return self._TMUX.__iter__()

    def __len__(self):
        return len(self._TMUX.keys())

    @classmethod
    def from_tmux(cls, session=None, window=None, **kwargs):
        '''
        Retrieve a tmux pane from server. Returns :class:`Pane`

        Used for freezing live sessions.

        Iterates ``tmux list-panes``, ``-F`` for return formatting.

        session
            :class:`Session` object
        window
            :class:`Window` object
        '''

        if not session:
            raise ValueError('Pane generated using ``from_tmux`` must have \
                             ``Session`` object')
        #else:
        #    if not isinstance(session, Session):
        #        raise TypeError('session must be a Session object')

        if not window:
            raise ValueError('Pane generated using ``from_tmux`` must have \
                             ``Window`` object')
        #else:
        #    if not isinstance(window, Window):
        #        raise TypeError('window must be a Window object')

        pane = cls()

        pane.update(**kwargs)

        pane._session = session
        pane._window = window

        return pane

    def send_keys(self, cmd, enter=True):
        '''
            ```tmux send-keys``` to the pane

            enter
                boolean. send enter after sending the key
        '''
        tmux('send-keys', '-t', int(self.get('pane_index')), cmd)

        if enter:
            self.enter()

    def enter(self):
        '''
            ```tmux send-keys``` send Enter to the pane
        '''
        tmux('send-keys', '-t', int(self.get('pane_index')), 'Enter')

    def __repr__(self):
        # todo test without session_name
        return "%s(%s)" % (self.__class__.__name__, self._window)
