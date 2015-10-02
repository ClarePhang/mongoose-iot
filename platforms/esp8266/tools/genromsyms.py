#!/usr/bin/env python

'''
Generate ROM function symbols out of Espressif ROM linker script.

A simple way to use the output of this script is to assembly it with xt-as
and used as additional symbol file to gdb (with add-symbol-file)

Rationale:

ROM symbols are already provided byte the linker script and end up the `*.out` image.
However they are absolute non-text symbols and thus don't get propertly recognized by
GDB when it tries to figure out in which function the program counter currently is.

This is very important in case the program crashes in a ROM function; otherwise
GDB is unable to locate the function prologue and thus compute the stack frame fixup
required to generate the stack trace.

In order to do so, it needs to access the symbols of the right type and with a size
that spans the actualy function body.
We don't know the actual lengths of the functions in ROM. A simple workaround is
to treat each function as spanning until the beginning of the next symbols.

We treat all ROM symbols as functions. Most are, and for those that are not, we
don't really care.

NOTE: that ROM functions such as strcpy are also GCC builtins, meaning that it code
compiled with optimizations on and with debugging symbols might correctly show a stacktrace
even without this fix. Compile with e.g. -fno-builtin-strcpy if you want to generate
a real call to ROM in case you fancy debugging the debugger.
'''

import re
import sys

ROM_LD_SCRIPT = 'tools/eagle.rom.addr.v6.ld'
ROM_BASE = 0x40000000

class Entry(object):
    def __init__(self, addr, name):
        self.addr = addr
        self.name = name

def parse_provide(l):
    m = re.match("PROVIDE \( (.*) = (.*) ?\);", l)
    return Entry(int(m.group(2), 16), m.group(1))

syms = []
for l in open(ROM_LD_SCRIPT):
    if l.strip():
        entry = parse_provide(l)
        if entry.addr >= ROM_BASE:
            syms.append(entry)

syms.sort(key=lambda x: x.addr)

print '// THIS FILE IS AUTOMATICALLY GENERATED, DO NOT MODIFY'
print '// generated with: %s' % ' '.join(sys.argv)
print '// meant to be assembled with:'
print '//     xt-as tools/romsyms.s -o tools/romsyms'
print '// and loaded in gdb with:'
print '//     add-symbol-file romsyms %s' % hex(ROM_BASE)
print '  .section        .text,"ax",@progbits'
print '  .literal_position'

for cur, next in zip(syms, syms[1:]):
    size = next.addr - cur.addr
    print '''  .align  4
  .global {1}
  .type   {1}, @function
  .org    {0}
{1}:
  .size   {1}, {2}
'''.format(hex(cur.addr - ROM_BASE), cur.name, size)