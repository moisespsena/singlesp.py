# singlesp.py

The Single Subprocess usage module.

Author: Moises P. Sena <moisespsena@gmail.com>

License: MIT

## Examples

```python
from singlesp import *
```

## Instantiate

```python
p = Proc('date')
# or
p = Proc(['echo', __file__])
```

## stdout

For set **stdout** callback, use the `>` operator.

```python
print(p.read())
# or
print(p.wait().read())
# or
print(p.run().wait().read())

def cb_out(proc):
    for line in proc.out:
        print("STDOUT: %r" % line)
        
Proc('date', callbacks=[cb_out]).wait()

def cb_outreader(reader):
    for line in reader:
        print("STDOUT: %r" % line)

(Proc('date') > cb_outreader).wait()

# or

p = Proc('date') > cb_outreader
p.wait()
```

### buffer

```python
def cb_outreader(reader):
    for data in reader(10):
        print("STDOUT: %r" % data)

(Proc('date') > cb_outreader).wait()
```

## stderr

For set **stderr** callback, use the `>>` operator.

```python
def cb_errreader(reader):
    for data in reader:
        print("ERR: %r" % data)

(Proc('date') >> cb_outreader).wait()
```

## stdout and stderr callbacks

```python
def cbo(reader):
    for data in reader:
        print("OUT: %r" % data)
        
def cbe(reader):
    for data in reader:
        print("ERR: %r" % data)

(Proc('echo out data;echo err data >&2;') > cbo >> cbe).wait()
```

## callbacks

```python
# async read stdout and stderr

def cb_stdout(proc):
    for line in proc.out:
        print("STDOUT: %r" % line)

def cb_stderr(proc):
    for line in proc.err:
        print("STDERR: %r" % line)

Proc('seq 1 3 | while read l; do echo "i= $l"; echo "i in err: $l" >&2; done',
     callbacks=[cb_stdout, cb_stderr]).wait()
```

## Many commands async

```python
Proc('echo CMD-1: first command with sleep 1; sleep 1; echo CMD-1: done',
     callbacks=[cb_stdout, cb_stderr]).run()
Proc('echo CMD-2: show date; date; echo CMD-2: done',
     callbacks=[cb_stdout, cb_stderr]).run()

# wait all callbacks
print("before wait")
wait()
print("done")
```

## Get exit status

```python
p = Proc('date').run().wait()
# or p = Proc('date').wait()
print(p.status)
```

## Pipes

Simple:

```python
(Input(['God ', 'is ', 'Love!!']) | Proc(['cat'])).read()

def cb_stdout(reader):
    for line in reader:
        print("STDOUT: %r" % line)
        
p = Proc('seq 1 3') | Proc('grep 2') > cb_stdout
# or p = Proc('seq 1 3').pipe(Proc('grep 2')) > cb_stdout

p.run()
wait()

print(Input(['God ', 'is ', 'Love!!']) | Proc(['cat'])).read()


def gen():
    yield 'God '
    yield 'is '
    yield 'Love!!'


print(Input(gen()) | Proc(['cat'])).read()

print(Commands(['date']) | Proc(['bash'])).read()

print(Commands(['date']) | bash()).read()

print(Commands(['date']) | sh()).read()

wait()
```

Simple:

```python
       
p = Proc('seq 1 3') | Proc('grep 2') > cb_stdout
p.run()
wait()
```

Complex:

```python
def cb_stdout(proc):
    for line in proc.out:
        print("STDOUT: %r" % line)

def a_stderr(proc):
    for line in proc.err:
        print("A-STDERR: %r" % line)

def b_stderr(proc):
    for line in proc.err:
        print("B-STDERR: %r" % line)

p = Proc('echo "[A] error message" >&2;seq 1 3', callbacks=[a_stderr]) | \
    Proc('while read l; do echo "i= $l"; echo "[B] i in err: $l" >&2; done',
     callbacks=[cb_stdout, b_stderr])
p.run()
wait()
```