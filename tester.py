#!/usr/bin/python

"""
Testing infrastructure - generates and executes tests

Computer Systems Architecture Course
Assignment 1
March 2018
"""
import getopt
import os
import pickle
import random
import subprocess
import sys
from threading import Timer

from supervisor import Supervisor
from test import TestCase, TestParams

# Tester messages
START_TEST_MSG       = "**************** Start %10s *****************"      # pylint: disable=bad-whitespace
END_TEST_MSG         = "***************** End %10s ******************"      # pylint: disable=bad-whitespace
TEST_ERRORS_MSG      = "Errors in iteration %d of %d:"                      # pylint: disable=bad-whitespace
TEST_FINISHED_MSG    = "%-10s finished.................%d%% completed"      # pylint: disable=bad-whitespace
TIMEOUT_MSG          = "%-10s timeout..................%d%% completed"      # pylint: disable=bad-whitespace

class Tester(object):
    """
    Runs the test.
    """
    def __init__(self, output_filename):
        """
        Constructor.
        @type output_filename: String
        @param output_filename: the file in which the tester logs results
        """
        self.output_filename = output_filename

        self.passed_tests = 0

        self.rand_gen = random.Random()
        self.rand_gen.seed(0)

    def run_test(self, testcase, num_iterations=1):
        """
        Performs a testcase generated from a given file or randomly.
        To better check for synchronization errors the testcase is run several
        times, as given by the 'num_iterations' parameter.
        @type testcase: TestCase
        @param testcase: the testcase to run
        @type num_iterations: Integer
        @param num_iterations: number of time to run the test
        """
        print START_TEST_MSG % testcase.name

        self.passed_tests = 0

        testcase.num_iterations = num_iterations
        for i in range(num_iterations):
            print TEST_ERRORS_MSG % (i + 1, num_iterations)
            testcase.crt_iteration = i + 1
            if self.start_test(testcase) == 0:
                self.passed_tests += 1
                print "No errors"

        print END_TEST_MSG % testcase.name

        out_file = open(self.output_filename, "a")

        msg = TEST_FINISHED_MSG % (testcase.name, 100.0 * self.passed_tests / num_iterations)

        out_file.write(msg + "\n")
        out_file.close()

    @staticmethod
    def timer_fn(iteration, num_iterations):
        """
        Timer function, it's executed in case of timeout when running a testcase
        @type iteration: integer
        @param iteration: the current iteration of the given testcase
        @type num_iterations: integer
        @param num_iterations: the total number of iterations for the given testcase
        """
        print >> sys.stderr, "timeout"

        os.abort()

    def start_test(self, test):
        """
        Starts a child process that will run the test case.

        @type test: TestCase
        @param test: an object containing all the information necessary for
        running the test case
        """
        path = os.path.dirname(sys.argv[0])
        path = "." if path == "" else path
        command = "python %s/tester.py" % path
        test = pickle.dumps(test)
        process = subprocess.Popen(command, stdin=subprocess.PIPE, shell=True)
        process.communicate(test)

        return process.returncode


def usage(argv):
    print "Usage: python %s [OPTIONS]"%argv[0]
    print "options:"
    print "\t-t,   --test\tspecial test to run"
    print "\t-f,   --testfile\ttest file, if not specified run a pickled test from stdin"
    print "\t-o,   --out\t\toutput file"
    print "\t-i,   --iterations\t\tthe number of times the test is run (iterations), defaults to 2"
    print "\t-h,   --help\t\tprint this help screen"


def main():
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "h:t:f:o:i:",
                                ["help", "--test", "testfile=", "out=", "iterations="])

    except getopt.GetoptError, err:
        print str(err)
        usage(sys.argv)
        sys.exit(2)

    test_name = None
    test_file = ""
    iterations = 2
    output_file = "tester.out"

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage(sys.argv)
            sys.exit(0)
        elif opt in ("-t", "--test"):
            test_name = arg
        elif opt in ("-f", "--testfile"):
            test_file = arg
        elif opt in ("-o", "--out"):
            output_file = arg
        elif opt in ("-i", "--iterations"):
            try:
                iterations = int(arg)
            except TypeError, err:
                print str(err)
                sys.exit(2)
        else:
            assert False, "unhandled option"

    if test_name == "test0":
        tester = Tester(output_file)
        test = TestCase.create_simple_test_case()
        tester.run_test(test, iterations)
    elif test_name == "test9":
        tester = Tester(output_file)
        test = TestCase.create_sharing1_test_case()
        tester.run_test(test, iterations)
    elif test_name == "test10":
        tester = Tester(output_file)
        test = TestCase.create_sharing2_test_case()
        tester.run_test(test, iterations)
    elif test_file:
        tester = Tester(output_file)
        test_params = TestParams.load_test(test_file)
        test = TestCase.create_test_case(test_params, tester.rand_gen)
        tester.run_test(test, iterations)

    else:  # I'm the child process :D
        test = pickle.loads("".join(sys.stdin.readlines()))

        watchdog = Timer(interval=test.timeout,
                         function=Tester.timer_fn,
                         args=(test.crt_iteration, test.num_iterations))

        watchdog.start()

        supervisor = Supervisor(test)
        supervisor.register_banned_thread(watchdog)
        supervisor.register_banned_thread()
        return_code = supervisor.run_testcase()

        watchdog.cancel()

        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(return_code)


if __name__ == "__main__":
    main()
