# pyDG1022
A library for controlling Rigol DG1022 Abitrary Waveform Generators

## What is this?
This library is built on top of pyUSB, and allows control of a Rigol DG1022 signal generator via the USB port. 

## Why reinvent the wheel?
Several methods for connecting USBTMC-compliant instruments already exist on Linux. However,
- Ni-VISA only works on certain linux distributions, and not mine
- PyUSBTMC kept giving me timeout errors
- USBTMC on the shell kept giving me timeout errors.

Since none of the existing libraries worked for my device, I wrote this one.

## Project Status
This is just barely working at this point. I've been able to get it going and do some interesting things with Jupyter notebooks and Interact widgets.
Still to do:
- Proper documentation
- Fuller API implementation
- Query commands (right now setting and ID work - but that's all)
