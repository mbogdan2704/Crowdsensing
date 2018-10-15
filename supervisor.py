"""
Testing infrastructure - enforce runtime restrictions

Computer Systems Architecture Course
Assignment 1
March 2018
"""

import os
import random
import sys
import time
import threading

from collections import namedtuple
from device import Device
from random import shuffle, uniform
from threading import current_thread, Event, Semaphore, Thread
from time import sleep
from traceback import print_stack


class Supervisor(object):
    """
    Class used to globally check accesses from device threads and verify result
    correctness.
    """

    # pylint: disable=protected-access

    def __init__(self, testcase, die_on_error=True):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Create a new supervisor for the test case.

        @type testcase: testcase.TestCase
        @param testcase: the test to supervise

        @type die_on_error: Boolean
        @param die_on_error: true for the test to be killed on first error
        """
        self.testcase = testcase
        self.setup_event = Event()
        self.start_event = Event()
        self.devices = {}
        self.threads = {}
        self.waits = {}
        self.die_on_error = die_on_error
        self.banned_threads = set()
        self.messages = []
        self.scripts = {i : {j : [] for j in range(len(self.testcase.devices))} for i in range(self.testcase.duration + self.testcase.extra_duration)}
        for script_td in self.testcase.scripts:
            script = Script(self.testcase.script_sleep)
            script._Script__set_supervisor(self)
            self.scripts[script_td.time_point][script_td.device].append(ScriptRunData(script=script, location=script_td.location))

    def register_banned_thread(self, thread=None):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Registers a tester thread. This thread must not be used by devices for
        any method execution.

        @type thread: Thread
        @param thread: the thread
        """
        if thread is None:
            thread = current_thread()
        self.banned_threads.add(thread)

    def check_execution(self, method, device):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Check device execution.

        @type method: String
        @param method: the name of the checked method
        @type device: device.Device
        @param device: the device which is checked
        """
        thread = current_thread()
        if thread in self.banned_threads:
            # ERROR: called from tester thread
            self.report("device '%s' is trying to execute %s on \
tester thread '%s'" % (str(device), method, thread.name))
            return

    def check_termination(self):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Checks for correct device shutdown. There must not be any active
        device threads.
        """
        for thrd in threading.enumerate():
            if thrd in self.banned_threads:
                continue
            self.report("thread '%s' did not terminate"
                        % str(thrd.name), die_on_error=False)

    def validate(self, crt_timepoint):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Validates the current state of the data.
        """
        data = {}
        for device_testdata in self.testcase.devices:
            device_id = device_testdata.id
            sensor_data = {loc : data for (loc, data) in device_testdata.locations}
            data[device_id] = sensor_data

        for tpt in range(crt_timepoint + 1):
            # print "timepoint %d" % tpt
            # for (dev, dat) in data.items():
            #     print "dev: %d %s" % (dev, str(dat))

            for run_tpt in range(tpt + 1):
                for (dev, scripts) in self.scripts[run_tpt].items():
                    for script_rd in scripts:
                        scrpt = script_rd.script
                        location = script_rd.location
                        neighbour_ids = self.__compute_neighbour_ids(dev, tpt)

                        # print "dev: %d %s" % (dev, neighbour_ids)

                        script_data = []
                        # collect data from current neighbours
                        for neigh in neighbour_ids:
                            if location in data[neigh]:
                                script_data.append(data[neigh][location])
                        # add our data, if any
                        if location in data[dev]:
                            script_data.append(data[dev][location])

                        # run script on data
                        if script_data != []:
                            result = scrpt._Script__update(script_data)

                            # update data of neighbours
                            for neigh in neighbour_ids:
                                if location in data[neigh]:
                                    data[neigh][location] = result
                            # update our data
                            if location in data[dev]:
                                data[dev][location] = result

        for (dev_id, sens_data) in data.items():
            for (loc, ref_data) in sens_data.items():
                calc_data = self.devices[dev_id].device.get_data(loc)
                if ref_data != calc_data:
                    self.report("after timepoint %d, data for location %d on device %d differs: expected %f, found %f\n" % (crt_timepoint, loc, dev_id, ref_data, calc_data))

    def report(self, message, die_on_error=None):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Reports an error message. All messages are stored in a list for
        retrieval at the end of the test.

        @type message: String
        @param message: the error message to log
        """
        if die_on_error is None:
            die_on_error = self.die_on_error

        if die_on_error:
            print >> sys.stderr, message + "\n",
            print_stack()
            os.abort()

        self.messages.append(message)

    def status(self):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Returns the list of logged error messages.

        @rtype: List of String
        @return: the list of encountered errors
        """
        return self.messages

    @staticmethod
    def __setup_devices(setup_event, device, neighbours):
        setup_event.wait()
        device.setup_devices(neighbours)
    
    @staticmethod
    def __send_scripts(device, scripts, delay, wait):
        time.sleep(delay)
        for script_rd in scripts:
            if script_rd is scripts[-1]:
                time.sleep(delay)
            device.assign_script(script_rd.script, script_rd.location)
        wait.release()

    @staticmethod
    def __send_end(device, wait, count):
        for i in range(count):
            wait.acquire()
        device.assign_script(None, None)

    def __compute_neighbour_ids(self, device_id, time_point):
        neighbours = set()
        # ugly linear search is ugly
        for enc in self.testcase.devices[device_id].encounters:
            if enc.time_point != time_point:
                continue
            neighbours |= set(enc.devices)
        return list(neighbours)

    def get_neighbours(self, device_id):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Returns the list of neighbours for device_id for the current timepoint, and increments the
        timepoint for the next invocation. This method is wrapped by Runtime.
        WARNING: this method is not thread-safe and must not be called concurrently with
        the same device_id.

        @type device_id: Integer
        @param device_id: the id of the device for which neighbours must be returned

        @rtype: List of device.Device
        @return: the list of neighbours for the current timepoint
        """
        self.start_event.wait()

        device = self.devices[device_id].device
        crt_timepoint = self.devices[device_id].crt_timepoint

        self.check_execution("get_neighbours", device)

        for dev_rd in self.devices.values():
            if dev_rd.crt_timepoint < crt_timepoint or dev_rd.crt_timepoint > crt_timepoint + 1:
                self.report("device %d called 'get_neighbours' without waiting for other devices\n" % device_id, True)

        for thrd in self.threads[device_id]:
                    thrd.join()

        if crt_timepoint == self.testcase.duration + self.testcase.extra_duration:
            return None

        if crt_timepoint > self.testcase.duration + self.testcase.extra_duration:
            self.report("called 'get_neighbours' from device %d, on timepoint %d, after simulation end at %d\n" % (device_id, crt_timepoint, self.testcase.duration + self.testcase.extra_duration), True)

        neighbour_ids = self.__compute_neighbour_ids(device_id, crt_timepoint)

        neighbours = [self.devices[neigh_id].device for neigh_id in neighbour_ids]

        scripts = self.scripts[crt_timepoint][device_id]

        for scrpt in scripts:
            scrpt.script._Script__set_device(device)

        if self.testcase.parallel_script:
            scripts = [[script] for script in scripts]
        else:
            scripts = [scripts]

        self.waits[device_id] = Semaphore(0)

        self.threads[device_id] = []
        for scrpt in scripts:
            delay_min = self.testcase.script_delay[0]
            delay_max = self.testcase.script_delay[1]
            thread = Thread(name="Sender",
                            target=Supervisor.__send_scripts,
                            args=(device, scrpt, random.uniform(delay_min, delay_max), self.waits[device_id]))
            self.register_banned_thread(thread)
            self.threads[device_id].append(thread)
            thread.start()

        thread = Thread(name="Ender",
                        target=Supervisor.__send_end,
                        args=(device, self.waits[device_id], len(scripts)))
        self.threads[device_id].append(thread)
        thread.start()

        self.devices[device_id].crt_timepoint = crt_timepoint + 1

        return neighbours

    def run_testcase(self):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Runs the test case by creating the devices, unblocking the script assignment and waiting
        for device termination.

        @rtype: Integer
        @return: the number of errors
        """
        for device_testdata in self.testcase.devices:
            device_id = device_testdata.id
            sensor_data = {loc : data for (loc, data) in device_testdata.locations}
            supervisor = Runtime(self, device_id)
            device = Device(device_id, sensor_data, supervisor)
            self.devices[device_id] = DeviceRunData(device=device, crt_timepoint=0)
            self.threads[device_id] = []

        devices = [device_rd.device for device_rd in self.devices.values()]
        setup_threads = []
        for dev in devices:
            neighbours = devices[:]
            shuffle(neighbours)
            setup_threads.append(Thread(name = "Setup",
                                        target = Supervisor.__setup_devices,
                                        args = (self.setup_event, dev, neighbours)))
            setup_threads[-1].start()
        
        self.setup_event.set()
        
        for thread in setup_threads:
            thread.join()

        self.start_event.set()

        for dev in self.devices.values():
            dev.device.shutdown()

        self.check_termination()

        self.validate(self.testcase.duration + self.testcase.extra_duration - 1)

        for msg in self.status():
            print >> sys.stderr, msg

        return len(self.status())


class Runtime(object):
    """
    Object called by a device to get its neighbours at each timepoint. Each device will get a
    different instance of this type which wraps the Supervisor object.
    """
    def __init__(self, supervisor, device_id):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Creates a new Runtime object.

        @type supervisor: Supervisor
        @param supervisor: the supervisor object to wrap
        @type device_id: Integer
        @param device_id: the id of the device which uses this Runtime instance
        """
        self.supervisor = supervisor
        self.device_id = device_id

    def get_neighbours(self):
        """
        Returns the list of neighbours for the current timepoint and increments the timepoint for
        the next invocation.
        WARNING: this method is not thread-safe, do not call it concurrently

        @rtype: List of Device
        @return: the list of current neighbours
        """
        return self.supervisor.get_neighbours(self.device_id)


class DeviceRunData:
    def __init__(self, device, crt_timepoint):
        self.device = device
        self.crt_timepoint = crt_timepoint


ScriptRunData = namedtuple("ScriptRunData", ['script', 'location'])


class Script(object):
    """
    Encapsulates the algoritm for improving noisy measurement data.
    """
    def __init__(self, delay=None, threshold=30):
        """
        !!! This is not part of the assignment API, do not call it !!!

        Creates a new script.
        """
        self.__delay = delay
        self.__threshold = threshold
        self.__supervisor = None
        self.__device = None

    def run(self, data):
        """
        Executes this script.

        @type data: List of Integer
        @param data: list containing data relevant for location, from one or multiple devices

        @rtype: Integer
        @return: improved measurement for the location
        """
        self.__supervisor.check_execution("run", self.__device)

        if self.__delay is not None:
            sleep(uniform(self.__delay[0], self.__delay[1]))

        return self.__update(data)

    def __update(self, sensor_data):
        # sa nu uit sa implementez algoritmul ;)
        return max(self.__threshold, max(sensor_data))

    def __set_supervisor(self, supervisor):
        self.__supervisor = supervisor

    def __set_device(self, device):
        self.__device = device
