"""
singlesp.py
===========

The Single Subprocess usage module.

Author: Moises P. Sena <moisespsena@gmail.com>
License: MIT
"""

import sys
import threading
import time
from subprocess import Popen, PIPE

PROC_FACTORIES = {}


class ProcManager(object):
    def __init__(self, stdout=None, stderr=None):
        self.stdout = stdout
        self.stderr = stderr
        self.threads = []

    def wait(self):
        while self.threads:
            time.sleep(.3)
            self.threads = filter(lambda t: t.is_alive(), self.threads)

    def run(self, cbs):
        threads = [threading.Thread(target=cb, args=args, kwargs=kwargs) for
                   cb, args, kwargs in cbs]
        self.threads.extend(map(lambda t: t.start() or t, threads))

    def proc(self, *args, **kwargs):
        kwargs['mgr'] = self
        if not self.stdout is None:
            kwargs.setdefault('stdout', self.stdout)
        if not self.stderr is None:
            kwargs.setdefault('stderr', self.stderr)
        return Proc(*args, **kwargs)

    def __getattr__(self, item):
        if item[0] != '_' and item in PROC_FACTORIES:
            pf = PROC_FACTORIES[item]
            proxy = pf.proxifier(self)
            return proxy
        raise AttributeError(item)


MANAGER = ProcManager()


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


class ProcFailedException(Exception):
    def __init__(self, status, cmd, err=''):
        super(ProcFailedException, self).__init__(status, cmd, err)

    @property
    def cmd(self):
        return self.args[1]

    @property
    def status(self):
        return self.args[0]

    @property
    def err(self):
        return self.args[2]

    def __str__(self):
        return "Command '%s' returned non-zero exit status %d: %s" % (
            self.cmd, self.status, self.err)


class Proc(object):
    def __init__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], basestring):
            kwargs['shell'] = True

            format_options = kwargs.pop('foptions', None)
            if format_options:
                args = (args[0].format(**format_options),)

        kwargs.setdefault('stdin', PIPE)
        kwargs.setdefault('stdout', sys.stdout)
        kwargs.setdefault('stderr', sys.stderr)
        self.mgr = kwargs.pop('mgr', MANAGER)
        self.callbacks = list(kwargs.pop('callbacks', []))
        self.args, self.kwargs = args, kwargs
        self.p = None
        self.pipe_to = False
        self.pipe_from = False
        self.cb_err = kwargs.pop('cb_err', None)
        self.cb_out = kwargs.pop('cb_out', None)
        self.async = kwargs.pop('async', True)

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
        self.p = Popen(*self.args, **self.kwargs)

        if self.callbacks:
            self.mgr.run([(fn, (self,), {}) for fn in self.callbacks])

    def run(self):
        assert not self.pipe_to

        if self.async:
            self.callbacks.append(lambda p: p.wait())
        if self.cb_err:
            self.callbacks.append(
                lambda self: self.cb_err(Reader(self, self.stderr)))
        if self.cb_out:
            self.callbacks.append(
                lambda self: self.cb_out(Reader(self, self.stdout)))

        if self.pipe_from and not self.pipe_to:
            assert not self.pipe_from.p
            pipes = []
            pf = self

            while pf:
                pipes.append(pf)
                pf = pf.pipe_from

            i = len(pipes) - 1
            while i > 0:
                op = pipes[i]

                if self.cb_err and not op.cb_err:
                    op.cb_err = self.cb_err

                op._run()
                pipes[i - 1].kwargs['stdin'] = op.stdout
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
        if not kwargs and len(args) == 1 and isinstance(args[0],
                                                        self.__class__):
            proc = args[0]
        else:
            proc = self.__class__(*args, **kwargs)

        self.pipe_to = proc
        proc.pipe_from = self
        self.kwargs['stdout'] = PIPE

        return proc

    def wait(self, check=False):
        if not self.p:
            self.run()
        self.p.wait()

        if check and self.status:
            raise ProcFailedException(self.status, self.args,
                                      self.p.stderr.read())

        return self

    @property
    def status(self):
        return self.p.returncode

    def ok(self):
        self.wait()
        return self.status == 0

    def __repr__(self):
        return "Proc(*%r)%s" % (
            self.args, (' < (%r)' % self.pipe_from if self.pipe_from else ''))

    def __gt__(self, other):
        self.cb_out = other
        return self

    def __rshift__(self, other):
        self.cb_err = other
        return self


def wait():
    return MANAGER.wait()


class ProcFactory(object):
    def __init__(self, name, cmd=None, env=None, mgr=None):
        if cmd is None:
            cmd = (name,)
        self.name = name
        self.cmd = cmd
        self.env = env
        self.mgr = mgr

    def __call__(self, *args, **kwargs):
        cmd = self.cmd
        if self.env:
            env = {}
            env.update(self.env)
            env.update(kwargs.get('env', {}))
            kwargs['env'] = env
        if args:
            assert isinstance(args[0], (list, tuple)), \
                ("Args[0] is not a list or tuple instance: %s:%r" % (
                    args[0].__class__, args[0]))
            cmd = cmd + tuple(args[0])
        mgr = kwargs.pop('mgr', None) or self.mgr or MANAGER

        return mgr.proc(cmd, **kwargs)

    def new(self, env=None, mgr=None, options=None, **kwargs):
        cmd = self.cmd
        if isinstance(cmd, basestring) and options:
            cmd = cmd % options

        env_ = {}

        if self.env:
            env_.update(self.env)

        if env:
            env_.update(env)

        return self.__class__(self.name, cmd=cmd, env=env_,
                              mgr=(mgr or self.mgr))

    def proxifier(self, mgr):
        return self.new(mgr=mgr)


def proc_factory(name, cmd=None, env=None, cls=ProcFactory):
    factory = cls(name, cmd=cmd, env=env)
    PROC_FACTORIES[name] = factory
    return factory


bash = proc_factory('bash')
sh = proc_factory('sh')
git = proc_factory('git')
pwd = proc_factory('pwd')


class SSHProcFactory(ProcFactory):
    def __init__(self, name, cmd=None, **kwargs):
        if not cmd:
            cmd = "ssh-keygen -R %(host)s >/dev/null 2>&1 || true;" \
                  "sshpass -e ssh -oStrictHostKeyChecking=no " \
                  "'%(user)s@%(host)s' -p %(port)s '{cmd};exit $?'"
        return super(SSHProcFactory, self).__init__(name, cmd=cmd, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs.setdefault('foptions', {'cmd': 'bash'})
        return super(SSHProcFactory, self).__call__(*args, **kwargs)

    def connector(self, host, user, password, port=22):
        return self.new(env={'SSHPASS': password},
                        options=dict(user=user, host=host, port=port))


ssh = proc_factory('ssh', cls=SSHProcFactory)


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


class InputLines(Input):
    def writer(self, proc):
        for v in self.it:
            proc.write(v)
            proc.write("\n")
        proc.stdin.close()
