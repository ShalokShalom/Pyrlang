# Copyright 2018, Erlang Solutions Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gevent
from gevent import Greenlet
from typing import Set

from Pyrlang import mailbox
from Pyrlang.Term.pid import Pid


class Process(Greenlet):
    """ Implements Erlang process semantic and lifetime.
        Registers itself in the process registry, can receive and send messages.
        To optionally register self with a name, call
        ``node.register_name(self, term.Atom('fgsfds'))``
    """

    def __init__(self, node) -> None:
        """ Create a process and register itself. Pid is generated by the node
            object.
        """
        Greenlet.__init__(self)
        self.node_name_ = node.node_name_
        """ Convenience field to see the Node (from Node.all_nodes[name]). """

        self.inbox_ = mailbox.Mailbox()
        """ Message queue (gevent.Queue). Messages are detected by the ``_run``
            loop and handled one by one in ``handle_one_inbox_message()``. 
        """

        self.pid_ = node.register_new_process(self)
        """ Process identifier for this object. Remember that when creating a 
            process, it registers itself in the node, and this creates a
            reference. 
            References prevent an object from being garbage collected.
            To destroy a process, get rid of this extra reference by calling
            ``exit()`` and telling it the cause of its death.
        """

        self.is_exiting_ = False

        self.monitors_ = set()  # type: Set[Pid]
        """ Who monitors us. Either local or remote processes. """

        self.monitor_targets_ = set()  # type: Set[Pid]
        """ Who we monitor. """

        self.start()  # greenlet has to be scheduled for run

    def _run(self):
        while not self.is_exiting_:
            self.handle_inbox()
            gevent.sleep(0)

    def handle_inbox(self):
        """ Do not override `handle_inbox`, instead go for
            `handle_one_inbox_message`
        """
        while True:
            # Block, but then gevent will allow other green-threads to
            # run, so rather than unnecessarily consuming CPU block
            msg = self.inbox_.get()
            # msg = self.inbox_.receive(filter_fn=lambda _: True)
            print("%s: handle_inbox %s" % (self, msg))
            if msg is None:
                break
            self.handle_one_inbox_message(msg)

    def handle_one_inbox_message(self, msg):
        """ Override this method to handle new incoming messages. """
        print("%s: Handling msg %s" % (self.pid_, msg))

    def exit(self, reason=None):
        """ Marks the object as exiting with the reason, informs links and
            monitors and unregisters the object from the node process
            dictionary.
        """
        # TODO: Inform links and monitors

        from Pyrlang import Node
        n = Node.all_nodes[self.node_name_]
        n.on_exit_process(self.pid_, reason)
