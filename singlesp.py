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

    def proc(self, *args, **kwargs):
        kwargs['mgr'] = self
        return Proc(*args, **kwargs)


MANAGER = Manager()


class Reader(object):
    def __init__(self, proc, handle):
        self.proc = proc
        self.handle = handle
        self.read = handle.read
        self.readline = handle.readline

    def __call__(self, buf=1024):
        return iter(lambda: self.read(buf), '')

    def __iter__(self):
        return iter(self.readline, '')


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
    def write(self):
        return self.stdin.write

    @property
    def out(self):
        return Reader(self, self.stdout)

    @property
    def err(self):
        return Reader(self, self.stderr)

    def __iter__(self):
        return self.out()

    def _run(self):
        assert not self.p, "Proc is running."
        self.callbacks.append(lambda p: p.wait())
        self.p = Popen(*self.args, **self.kwargs)

        if self.callbacks:
            self.mgr.run([(fn, (self,), {}) for fn in self.callbacks])

    def run(self):
        assert not self.pipe_to

        if self.pipe_from and not self.pipe_to:
            assert not self.pipe_from.p
            pipes = []
            pf = self

            while pf:
                pipes.append(pf)
                pf = pf.pipe_from

            i = len(pipes) - 1
            while i > 0:
                pipes[i]._run()
                pipes[i - 1].kwargs['stdin'] = pipes[i].stdout
                i -= 1

        self._run()

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

        return proc

    def wait(self):
        if not self.p:
            self.run()
        self.p.wait()
        return self

    @property
    def status(self):
        return self.p.returncode

    def __repr__(self):
        return "Proc(*%r)%s" % (self.args, (' < (%r)' % self.pipe_from if self.pipe_from else ''))

    def __gt__(self, other):
        self.callbacks.append(lambda self: other(Reader(self, self.stdout)))
        return self


def wait():
    return MANAGER.wait()


def proc_factory(name, cmd=None):
    if cmd is None:
        cmd = (name,)

    def alias(*args, **kwargs):
        cmd_ = cmd
        if args:
            assert isinstance(args[0], (list, tuple))
            cmd_ = cmd_ + tuple(args[0])
        return Proc(cmd_, **kwargs)

    alias.__name__ = name
    return alias


bash = proc_factory('bash')
sh = proc_factory('sh')
git = proc_factory('git')
pwd = proc_factory('pwd')


class SSHFactory(object):
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
        return self.pipe(other)

    def writer(self, proc):
        for v in self.it:
            proc.write(v)
        proc.stdin.close()

    def pipe(self, proc):
        proc.kwargs['stdin'] = PIPE
        proc.callbacks.append(self.writer)
        return proc


class Commands(Input):
    def writer(self, proc):
        for v in self.it:
            proc.write("(%s) && " % v)
        proc.write("true")
        proc.stdin.close()


def cb_stdout(p):
    for line in p.out():
        print("STDOUT: %r" % line)

def a_stderr(p):
    for line in p.err():
        print("A-STDERR: %r" % line)

def b_stderr(p):
    for line in p.err():
        print("B-STDERR: %r" % line)

p = Proc('echo "[A] error message" >&2;seq 1 3', callbacks=[a_stderr]) | \
    Proc('while read l; do echo "i= $l"; echo "[B] i in err: $l" >&2; done',
     callbacks=[cb_stdout, b_stderr])
p.run()
wait()