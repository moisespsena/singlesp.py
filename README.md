# singlesp.py

The Single Subprocess usage module.

Author: Moises P. Sena <moisespsena@gmail.com>
License: MIT

# Examples

```python
from singlesp import *

# print all output
print(Proc('date').read())

##### callbacks #####

# async read stdout and stderr

def cb_stdout(p):
    for line in p:
        print("STDOUT: %r" % line)

def cb_stderr(p):
    for line in p.error():
        print("STDERR: %r" % line)

Proc('seq 1 3 | while read l; do echo "i= $l"; echo "i in err: $l" >&2; done',
     callbacks=[cb_stdout, cb_stderr]).wait()

##### many commands async #####

Proc('echo CMD-1: first command with sleep 1; sleep 1; echo CMD-1: done',
     callbacks=[cb_stdout, cb_stderr]).run()
Proc('echo CMD-2: show date; date; echo CMD-2: done',
     callbacks=[cb_stdout, cb_stderr]).run()

# wait all callbacks
print("before wait")
wait()
print("done")

##### get exit status #####

p = Proc('date').run().wait()
# or p = Proc('date').wait()
print(p.status)

##### pipe #####

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
```