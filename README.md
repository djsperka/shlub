# SHLUB

SHLUB is an awesome name for a simple serial hub program.

## Description

The software that runs experiment/DAQ code is in Spike2. The only avenues for IPC with Spike2 are
digital I/O via the sequencer and the Serial port. While we need the digital I/O for communications with our
visual stimuli application *fixstim*, we sometimes must also use a serial connection. 

On the Windows machine that hosts Spike2 and *fixstim*, [com0com](https://com0com.sourceforge.net/) is installed, which
allows the creation of *virtual serial port pairs*. The DAQ computer has a pair of serial ports, **COM7** and **COM8**, that
are connected to one another. There is no physical port, but *com0com* instead provides a driver which passes all bytes written to 
one port to the *waiting input* queue of its partner. So, our stimulus program can open one of the pair and have direct communication
with the *spike2* script driving a particular experiment. 

With the new eye tracking system, a new communication problem arose. The new system is on a separate computer. The process of 
calibrating the tracker requires that we record the tracker's eye position measurements at moments of fixation on a target at a 
known screen location. This is typically done by presenting a series of fixation dots, and the experimenter presses a button
when they observe the eye fixating. We must also communicate the stimulus position to the calibration process on the tracker's 
computer. We could go one of three ways:
- Present the stimuli in a fixed order, figure it out on the fly (BAD IDEA)
- Intall a serial port on the tracker computer (NO) and use existing serial hub applications (CHEESY STUFF, SO NO)
- Use TCP listener on the tracker side (modify existing code) and create this program to take serial input and send it to one or more outputs

TODO: NEED A GOOD DIAGRAM HERE! 


## Getting Started

Make sure there are enough serial port pairs installed. A *pair* is needed for *SHLUB*'s input, and a *pair* is needed for each *serial* output
required. In our lab, we use a single serial output, so we have two *com0com* pairs available. 



### Dependencies

* Designed to work on Windows, but also works on my linux desktop. 
* I used mostly python 3.12. I'd judge it likely to work fine with other 3.x versions. 

### Installing

* Fetch github repo. 
* Create a virtual env (repo has requirements.txt)

### Executing program

* Which serial port pair will be used for input to SHLUB? One side of this pair will be the serial port opened in the Spike2 script, used to broadcast the stimulus position. The other side will be the input port. It is named SHLUB-IN below, but substitute COM6 or COM7 or whatever name you used when you created the virtual pair. 
* Which serial port pair will be used for input to *fixstim*. One side of this pair is specified on the *fixstim* command line. The other side of this pair is specified here as one of the *outlets* for the hub. It is named SHLUB-OUT-SERIAL below. 
* What is the ip address and port (TRACKER-IP and TRACKER-PORT below) for the calibration process on the tracker computer? The ip address depends on the current DHCP offering (on Windows, use Command Prompt, command *ipconfig*). The port must be coordinated with the startup of the calibration process, where it is also specified on the command line. 
* Armed with that info, run the application like this:
```
python serial-repeater.py --port SHLUB-IN --outlet serial,SHLUB-OUT-SERIAL --outlet tcp,TRACKER-IP,TRACKER-PORT
```

### Interacting with the hub

All messages through the port are to be terminated with a semicolon! 

After starting the application, the *input* port is opened, but the *outlets* are not connected. The hub watches for two special commands:
- *connect;* - will open outlets, and attempt to connect to any tcp ports. 
- *disconnect;* - will close/disconnect outlets and wait for a *connect;* message

There is no feedback that the connection has been made. It is up to the user to verify that connections (especially the tcp connection) have been made. 

## Authors

Daniel Sperka <djsperka@ucdavis.edu> 
https://github.com/djsperka

## Version History

* 1.0
    * this one

## License

Copyright &copy; 2026 The Regents of the University of California, Davis campus. All Rights Reserved.

Please see the [LICENSE](LICENSE.md) file for more information.


## Acknowledgments

Development of this software was supported by NIH Vision Research Core Grant, P30EY012576. 
