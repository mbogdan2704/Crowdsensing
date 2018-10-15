"""
Utilities for loading input files and generating and representing test cases.

Computer Systems Architecture Course
Assignment 1
March 2018
"""

import os
import re
from collections import namedtuple

# TestCase parameters, the same string as in the test* file format
TESTCASE_NAME = "name"
NUM_DEVICES = "num_nodes"
NUM_LOCATIONS = "num_locations"
NUM_SCRIPTS = "num_scripts"
DURATION = "duration"
TIMEOUT_PERIOD = "timeout"
SCRIPTS_DELAY = "scripts_delay"
SCRIPT_SLEEP = "script_sleep"
PARALLEL_SCRIPT = "parallel_script"
OVERLAP = "overlap"
GEN_SEED = "gen_seed"
RUN_SEED = "run_seed"
EXTRA_DURATION = "extra_duration"
SCRIPT_ASSIGNMENT = "script_assignment"
SCRIPT_ASSIGNMENT_RANDOM = "RANDOM"
SCRIPT_ASSIGNMENT_ALL = "ALL"
SCRIPT_ASSIGNMENT_SINGLE = "SINGLE"

Location = namedtuple("Location", ['id', 'sensor_data'])
Encounter = namedtuple("Encounter", ['time_point', 'devices'])
DeviceTestData = namedtuple("DeviceTestData", ['id', 'locations', 'encounters'])
ScriptTestData = namedtuple("ScriptTestData", ['time_point', 'device', 'location'])


class TestCase(object):
    """
    Class representing a test case: various parameters and lists of devices and scripts.
    """

    def __init__(self):

        self.name = None
        self.num_locations = None
        self.duration = None
        self.scripts = None
        self.devices = None
        self.script_delay = None
        self.script_sleep = None
        self.parallel_script = None
        self.timeout = None
        self.num_iterations = None
        self.crt_iteration = None

    @staticmethod
    def create_simple_test_case():
        """
        Creates a basic test case without using parameters provided in a test file.

        @rtype: TestCase
        @return: a TestCase object
        """
        test_case = TestCase()
        test_case.name = "Test 0"
        test_case.script_delay = (0.5, 0.5)
        test_case.parallel_script = False
        test_case.duration = 1
        test_case.extra_duration = 0
        test_case.timeout = 4
        test_case.num_locations = 2
        dev0_loc0 = Location(id=0, sensor_data=42.0)
        dev1_loc1 = Location(id=1, sensor_data=64.0)
        dev0 = DeviceTestData(id=0, locations=[dev0_loc0], encounters=[])
        dev1 = DeviceTestData(id=1, locations=[dev1_loc1], encounters=[])
        test_case.devices = [dev0, dev1]
        dev0_script0 = ScriptTestData(time_point=0, device=0, location=0)
        dev1_script0 = ScriptTestData(time_point=0, device=1, location=1)
        test_case.scripts = [dev0_script0, dev1_script0]
        return test_case

    @staticmethod
    def create_sharing1_test_case():
        """
        Creates a stress test for shared data synchronization.

        @rtype: TestCase
        @return: a TestCase object
        """
        test_case = TestCase()
        test_case.name = "Test 9"
        test_case.script_delay = (0.01, 0.01)
        test_case.script_sleep = (0.01, 0.01)
        test_case.parallel_script = True
        test_case.duration = 3
        test_case.extra_duration = 0
        test_case.timeout = 7
        test_case.num_locations = 2
        locations = [Location(id=0, sensor_data=64.0) for i in range(98)]
        locations.append(Location(id=0, sensor_data=100.0))
        locations.append(Location(id=0, sensor_data=42.0))
        test_case.devices = [DeviceTestData(id=i, locations=[locations[i]], encounters=[Encounter(time_point=1, devices=[99]), Encounter(time_point=2, devices=[98])]) for i in range(100)]
        test_case.scripts = [ScriptTestData(time_point=0, device=i, location=0) for i in range(99)]

        return test_case

    @staticmethod
    def create_sharing2_test_case():
        """
        Creates a stress test for shared data synchronization.

        @rtype: TestCase
        @return: a TestCase object
        """
        test_case = TestCase()
        test_case.name = "Test 10"
        test_case.script_delay = (0, 0)
        test_case.script_sleep = (0.05, 0.05)
        test_case.parallel_script = False
        test_case.duration = 3
        test_case.extra_duration = 0
        test_case.timeout = 12
        test_case.num_locations = 2
        locations = [Location(id=0, sensor_data=56.0) for i in range(58)]
        locations.append(Location(id=0, sensor_data=73.0))
        locations.append(Location(id=0, sensor_data=50.0))
        test_case.devices = [DeviceTestData(id=i, locations=[locations[i]], encounters=[Encounter(time_point=1, devices=[59]), Encounter(time_point=2, devices=[58])]) for i in range(60)]
        test_case.scripts = [ScriptTestData(time_point=0, device=i, location=0) for i in range(59)]

        return test_case

    @staticmethod
    def create_test_case(params, rand_gen):
        """
        Creates a test case using the provided parameters.
        @type params: TestParams
        @param params: a TestCase specification
        @type rand_gen: Random
        @param rand_gen: a random generator used for creating the test case's components
        @return: a TestCase object
        """
        test_case = TestCase()
        test_case.name = params.name
        test_case.num_locations = params.num_locations
        test_case.duration = params.duration
        test_case.script_delay = params.script_delay
        test_case.script_sleep = params.script_sleep
        test_case.parallel_script = params.parallel_script
        test_case.timeout = params.timeout
        test_case.run_seed = params.run_seed
        test_case.extra_duration = params.extra_duration

        if params.gen_seed is not None:
            rand_gen = random.Random(params.gen_seed)

        test_case.generate_test_data(params, rand_gen)

        return test_case

    def generate_test_data(self, params, rand_gen):
        """
        Creates the elements of a test case: lists of devices, locations, encounters, scripts
        @type params: TestParams
        @param params: the test for which the elements are generated
        @type rand_gen: Random
        @param rand_gen: a random generator
        """

        """ Create devices """

        # each location i has a list of indexes of devices
        # i-th elem in locations corresponds to the i-th elem in devices_for_location
        devices_for_locations = [None] * self.num_locations

        if params.overlap == 1: # one location per device

            # aka device i has location j
            location_for_each_device = rand_gen.sample(xrange(self.num_locations),
                                                       params.num_devices)

            location_for_each_device_as_list = [[Location(location_for_each_device[i],
                                                          rand_gen.randint(30, 100))]
                                                for i in range(params.num_devices)]
            self.devices = [DeviceTestData(i, location_for_each_device_as_list[i], [])
                            for i in range(params.num_devices)]

            # aka location j has device j
            for device_id in range(len(location_for_each_device)):
                devices_for_locations[location_for_each_device[device_id]] = [device_id]

        else:
            self.devices = [DeviceTestData(i, [], []) for i in range(params.num_devices)]

            # assign visited locations to devices

            for i in range(self.num_locations):
                num_devices = rand_gen.randint(1, params.overlap)
                devices_for_locations[i] = rand_gen.sample(xrange(params.num_devices), num_devices)

            for device in self.devices:
                for i in range(len(devices_for_locations)):
                    if device.id in devices_for_locations[i]:
                        device.locations.append(Location(i, rand_gen.randint(30, 100)))

        """ Create Scripts """

        if params.script_assignment == SCRIPT_ASSIGNMENT_SINGLE:
            # all scripts use the same location (picked randomly)
            location = rand_gen.randint(1, self.num_locations-1)

            self.scripts = [ScriptTestData(rand_gen.randint(0, self.duration-1),
                            rand_gen.randint(0, params.num_devices-1),
                            location) for _ in range(params.num_scripts)]

        if params.script_assignment == SCRIPT_ASSIGNMENT_RANDOM:
            # scripts use a random location
            self.scripts = [ScriptTestData(rand_gen.randint(0, self.duration-1),
                            rand_gen.randint(0, params.num_devices-1),
                            rand_gen.randint(0, self.num_locations-1))
                            for _ in range(params.num_scripts)]

        if params.script_assignment == SCRIPT_ASSIGNMENT_ALL:
            # each script uses a different location
            script_locations = rand_gen.sample(xrange(self.num_locations), params.num_scripts)
            self.scripts = [ScriptTestData(rand_gen.randint(0, self.duration-1),
                            rand_gen.randint(0, params.num_devices-1),
                            script_locations[i])
                            for i in range(params.num_scripts)]

        self.scripts = sorted(self.scripts, key=lambda s: s.time_point)

        """ Create encounters """

        for script in self.scripts:
            loc = script.location
            time = script.time_point
            device = script.device

            location_devices = devices_for_locations[loc]
            encounters = []
            num_encouters = rand_gen.randint(1, self.duration+self.extra_duration-time)

            set_of_unique_devices = set()
            for i in range(num_encouters):

                encountered_devices = rand_gen.sample(location_devices,
                                                    rand_gen.randint(1, len(location_devices)/2+1))
                set_of_unique_devices |= set(encountered_devices)

                encounters.append(Encounter(time+i, encountered_devices))

            for dev in location_devices:
                if dev not in set_of_unique_devices:
                    encounters[rand_gen.randint(0, len(encounters)-1)].devices.append(dev)

            for d in self.devices:
                if d.id == device:
                    d.encounters.extend(encounters)
                    break

        # print "Locations: ",
        # for loc in range(len(devices_for_locations)):
        #     print "%d:%s " % (loc, str(devices_for_locations[loc])),
        # print
        #
        # for script in self.scripts:
        #     print script
        #
        # for encounter in sorted([e for dev in self.devices for e in dev.encounters], key=lambda e : e.time_point):
        #     print encounter, [d.id for d in self.devices if encounter in d.encounters]
        #
        # for dev in self.devices:
        #     print "DeviceTestData(id=", dev.id
        #     print "\tlocations="
        #     for loc in dev.locations:
        #         print "\t\t", loc
        #     print "\tencounters="
        #     for enc in dev.encounters:
        #         print "\t\t", enc



class TestParams(object):
    """
    Class representing the parameters of a test case, as specified in test input files.
    """

    def __init__(self, name="TestCase", num_devices=0, num_locations=0, num_scripts=0,
                    script_delay=None, script_sleep=None, parallel_script=False, timeout=0, duration=1,
                    overlap=1, gen_seed = None, run_seed = None, extra_duration = 0, script_assignment="RANDOM"):
        self.name = name
        self.num_devices = num_devices
        self.num_locations = num_locations
        self.num_scripts = num_scripts
        self.script_delay = script_delay
        self.script_sleep = script_sleep
        self.parallel_script = parallel_script
        self.timeout = timeout
        self.duration = duration
        self.overlap = overlap
        self.gen_seed = gen_seed
        self.run_seed = run_seed
        self.extra_duration = extra_duration
        self.script_assignment = script_assignment

    @staticmethod
    def load_test(filename):
        """
        Loads the test description from a file with the following format:

        param_name1 = value
        param_name2 = value
        [...]

        Blank lines or lines starting with # (comments) are ignored

        Parameter names are defined in this class. Parameters can be
        declared in any order in the file.

        @type filename: str
        @param filename: the test file
        @return: a TestCase object
        """
        params_names = [NUM_DEVICES, TESTCASE_NAME, NUM_LOCATIONS, NUM_SCRIPTS,
                        DURATION, TIMEOUT_PERIOD, SCRIPTS_DELAY,
                        PARALLEL_SCRIPT, OVERLAP, SCRIPT_ASSIGNMENT, SCRIPT_SLEEP, GEN_SEED, RUN_SEED, EXTRA_DURATION]

        test_params = dict.fromkeys(params_names, 0)

        test_name, num_devices, num_locations, num_scripts = None, None, None, None
        timeout, scripts_delay, duration, overlap, script_assignment = None, None, None, None, None
        parallel_script, script_sleep, gen_seed, run_seed, extra_duration = None, None, None, None, 0

        try:
            with open(filename, "r") as test_file:
                for line in test_file:
                    line = line.strip()
                    if len(line) == 0 or line.startswith('#'):
                        continue

                    parts = [i.strip() for i in re.split("=", line)]
                    if len(parts) != 2:
                        raise StandardError("Wrong test file format")

                    if parts[0] not in test_params:
                        raise StandardError("Wrong parameter name: %s" % parts[0])

                    elif parts[0] == TESTCASE_NAME:
                        test_name = parts[1]
                    elif parts[0] == NUM_DEVICES:
                        num_devices = int(parts[1])
                    elif parts[0] == NUM_LOCATIONS:
                        num_locations = int(parts[1])
                    elif parts[0] == NUM_SCRIPTS:
                        num_scripts = int(parts[1])
                    elif parts[0] == SCRIPT_SLEEP:
                        if len(parts[1].split(",")) != 2:
                            raise StandardError("Wrong format for specifying output"
                                                + "script sleep : %s" % parts[1])
                        script_sleep = (float(parts[1].split(",")[0].strip()),
                                        float(parts[1].split(",")[1].strip()))
                    elif parts[0] == PARALLEL_SCRIPT:
                        parallel_script = bool(parts[1])
                    elif parts[0] == SCRIPTS_DELAY:
                        if len(parts[1].split(",")) != 2:
                            raise StandardError("Wrong format for specifying output"
                                                + "scripts delay : %s" % parts[1])
                        script_delay = (float(parts[1].split(",")[0].strip()),
                                        float(parts[1].split(",")[1].strip()))
                    elif parts[0] == DURATION:
                        duration = int(parts[1])
                    elif parts[0] == TIMEOUT_PERIOD:
                        timeout = int(parts[1])
                    elif parts[0] == OVERLAP:
                        overlap = int(parts[1])
                    elif parts[0] == GEN_SEED:
                        gen_seed = int(parts[1])
                    elif parts[0] == RUN_SEED:
                        run_seed = int(parts[1])
                    elif parts[0] == EXTRA_DURATION:
                        extra_duration = int(parts[1])
                    elif parts[0] == SCRIPT_ASSIGNMENT:
                        if parts[1] not in [SCRIPT_ASSIGNMENT_ALL, SCRIPT_ASSIGNMENT_RANDOM,
                                            SCRIPT_ASSIGNMENT_SINGLE]:
                            raise StandardError("Wrong script assignment type %s"%parts[1])
                        script_assignment = parts[1]

            # some basic validation
            if script_assignment == SCRIPT_ASSIGNMENT_ALL and num_scripts > num_locations:
                raise StandardError("Too many scripts (%d) for the given locations (%d)"
                                    % (num_scripts, num_locations))
            if overlap > num_devices:
                raise StandardError("Too many devices for the overlap parameter %d" % overlap)
            if overlap == 1 and num_locations != num_devices:
                raise StandardError("When overlap is %d, the number of locations must be equal\
                                    to the number of devices" % overlap)

        except StandardError, err:
            print err
            os.abort()

        return (TestParams(name=test_name,
                           num_devices=num_devices,
                           num_locations=num_locations,
                           num_scripts=num_scripts,
                           script_delay=script_delay,
                           script_sleep=script_sleep,
                           parallel_script=parallel_script,
                           timeout=timeout,
                           duration=duration,
                           overlap=overlap,
                           gen_seed=gen_seed,
                           run_seed=run_seed,
                           extra_duration=extra_duration,
                           script_assignment=script_assignment))

    def __str__(self):
        # TODO this is missing some fields
        return "{} devices\n{} locations\n{} scripts\n{}s timeout\n{}s duration\n" \
               "{}s min script delay\n{}s max script delay\n" \
               "max {} device per location\n{} script assignment".format(self.num_devices,
                                                                   self.num_locations,
                                                                   self.num_scripts,
                                                                   self.timeout,
                                                                   self.duration,
                                                                   self.script_delay[0],
                                                                   self.script_delay[1],
                                                                   self.overlap,
                                                                   self.script_assignment)

if __name__ == "__main__":
    params = TestParams.load_test("../tests/test1")
    print params
    import random
    TestCase.create_test_case(params, random.Random())
