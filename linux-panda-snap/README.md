Snap of Linux ARM Kernel for TI PandaBoard
==========================================

This repository provides a first approximation to a snap
that builds the kernel, modules and device tree binaries
to support PandaBoard and PandaBoard ES devices.

Assemble
--------

**1. Install Snapcraft 2.x**

    $ sudo apt-get install snapcraft

**2. Build**

    $ sudo snapcraft --targetarch armhf
