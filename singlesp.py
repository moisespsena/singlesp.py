"""
singlesp.py
===========

The Single Subprocess usage module.

Author: Moises P. Sena <moisespsena@gmail.com>
License: MIT
"""

import threading
import time
from subprocess import Popen, PIPE

class Manager(object):
    def __init__(self):
        self.threads = []

    def wait(self):
        while self.threads:
            time.sleep(.3)
            self.threads = filter(lambda t: t.is_alive(), self.threads)

    def run(self, cbs):
        threads = [threading.Thread(target=cb, args=args, kwargs=kwargs) for cb, args, kwargs in cbs]
        self.threads.extend(map(lambda t: t.start() or t, threads))

MANAGER = Manager()


class Proc(object):
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], basestring):
            kwargs['shell'] = True
        kwargs.setdefault('stdin', PIPE)
        kwargs.setdefault('stdout', PIPE)
        kwargs.setdefault('stderr', PIPE)
        self.mgr = kwargs.pop('mgr', MANAGER)
        self.callbacks = list(kwargs.pop('callbacks', []))
        self.args, self.kwargs = args, kwargs
        self.p = None
        self.pipe_to = False
        self.pipe_from = False
        self._status = None

    @property
    def stdin(self):
        return self.p.stdin

    @property
    def stderr(self):
        return self.p.stderr

    @property
    def stdout(self):
        return self.p.stdout

    def read(self, *args, **kwargs):
        if not self.p:
            self.run()
        return self.stdout.read(*args, **kwargs)

    @property
    def readline(self):
        return self.stdout.readline

    @property
    def returncode(self):
        return self.p.returncode

    @property
    def write(self):
        return self.stdin.write

    def output(self, buffer=4):
        return iter(lambda: self.read(buffer), '')

    def __iter__(self):
        return iter(self.readline, '')

    def error(self, buffer=None, all=False):
        if all:
            return self.stderr.read()
        elif buffer:
            return iter(lambda: self.stderr.read(buffer), '')
        else:
            return iter(self.stderr.readline, '')

    def run(self):
        assert not self.p, "Proc is running."
        self.callbacks.append(lambda p: p.wait())
        self.p = Popen(*self.args, **self.kwargs)

        if self.callbacks:
            self.mgr.run([(fn, (self,), {}) for fn in self.callbacks])

        return self

    def __or__(self, other):
        if isinstance(other, self.__class__):
            return self.pipe(other)
        else:
            assert isinstance(other, tuple)
            args, kwargs = other[0], {} if len(other) == 1 else other[1]
            return self.pipe(*args, **kwargs)

    def pipe(self, *args, **kwargs):
        if not kwargs and len(args) == 1 and isinstance(args[0], self.__class__):
            proc = args[0]
        else:
            proc = self.__class__(*args, **kwargs)

        self.pipe_to = proc
        proc.pipe_from = self
        self.kwargs['stdout'] = PIPE
        self.run()
        proc.kwargs['stdin'] = self.stdout

        return proc

    def wait(self):
        if not self.p:
            self.run()
        self.p.wait()
        return self

    @property
    def status(self):
        if not self._status is None:
            return self._status
        return self.returncode

    def __repr__(self):
        return "%r%s" % (self.args, (' < (%r)' % self.pipe_from if self.pipe_from else ''))


def wait():
    return MANAGER.wait()


class SSH(object):
    def __init__(self, host, user, password, port=22):
        self.host, self.user, self.password, self.port = host, user, password, port

    def __call__(self, **kwargs):
        cmds = [
            'ssh-keygen -R %s >/dev/null 2>&1 || true' % self.host,
            ("sshpass -e ssh -oStrictHostKeyChecking=no '%s@%s' -p %s "
             "'bash;exit $?'") % (self.user, self.host, self.port),
        ]
        cmd = ';'.join(cmds)
        return Proc(cmd, env={'SSHPASS': self.password}, **kwargs)


class Input(object):
    def __init__(self, it):
        self.it = it

    def __or__(self, other):
        if not isinstance(other, Proc):
            assert isinstance(other, tuple)
            args, kwargs = other[0], {} if len(other) == 1 else other[1]
            return self.pipe(*args, **kwargs)
        return self.pipe(other)

    def pipe(self, *args, **kwargs):
        def writer(p):
            for v in self.it:
                p.write("(%s) && " % v)
            p.write("true")
            p.stdin.close()

        other = Proc(*args, **kwargs)
        other.kwargs['stdin'] = PIPE
        other.callbacks.append(writer)
        return other

def cb_stdout(p):
    for line in p:
        print("STDOUT: %r" % line)

def a_stderr(p):
    for line in p.error():
        print("A-STDERR: %r" % line)

def b_stderr(p):
    for line in p.error():
        print("B-STDERR: %r" % line)

p = Proc('echo "[A] error message" >&2;seq 1 3', callbacks=[a_stderr]) | \
    Proc('while read l; do echo "i= $l"; echo "[B] i in err: $l" >&2; done',
     callbacks=[cb_stdout, b_stderr])
p.run()
wait()