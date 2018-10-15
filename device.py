"""
This module represents a device.

Computer Systems Architecture Course
Assignment 1
March 2018
"""

from threading import Event, Thread, Lock
from barrier import ReusableBarrierSem
class Device(object):
    """
    Class that represents a device.
    """

    def __init__(self, device_id, sensor_data, supervisor):
        """
        Constructor.

        @type device_id: Integer
        @param device_id: the unique id of this node; between 0 and N-1

        @type sensor_data: List of (Integer, Float)
        @param sensor_data: a list containing (location, data) as measured by this device

        @type supervisor: Supervisor
        @param supervisor: the testing infrastructure's control and validation component
        @type script_received: Un event folosit pentru a astepta sa se primeasca toate scripturile
        @type scripts:Unde pastrez scripturile
        @type devices = o lista unde pastrez device-urile
        @type barrier = o bariera folosita pentru a sincroniza threadurile Master
        @type thread = thread-urile Master
        @type locations = Un vector de lock-uri pentru Locatii
        @type data_lock = Un lock folosit pentru a nu se accesa sensor_data de pe mai multe
        threaduri
        @type setup = Un event folosit pentru a face threadurile Master sa astepte setup-ul
        """
        self.device_id = device_id
        self.sensor_data = sensor_data
        self.supervisor = supervisor
        self.script_received = Event()
        self.scripts = []
        self.timepoint_done = Event()
        self.devices = None
        self.barrier = None
        self.thread = DeviceThread(self)
        self.locations = []
        self.data_lock = Lock()
        self.get_lock = Lock()
        self.setup = Event()
        self.thread.start()
    def __str__(self):
        """
        Pretty prints this device.

        @rtype: String
        @return: a string containing the id of this device
        """
        return "Device %d" % self.device_id

    def setup_devices(self, devices):
        """
        Setup the devices before simulation begins.

        @type devices: List of Device
        @param devices: list containing all devices
        O functie folosita pentru a initializa device-urile.In acestea eu pun o bariera
        comuna si o lista de lock-uri comune pentru fiecare locatie in parte,
        Tot aici dau set la un event, Setup, al carui rol este sa faca threadurile
        Master sa astepte dupa setup
        """
        # we don't need no stinkin' setup
        self.devices = devices
        barrier = ReusableBarrierSem(len(devices))
        if self.device_id == 0:
            for _ in range(100):
                self.locations.append(Lock())
            for dev in devices:
                dev.barrier = barrier
                dev.locations = self.locations
                dev.setup.set()
    def assign_script(self, script, location):
        """
        Provide a script for the device to execute.

        @type script: Script
        @param script: the script to execute from now on at each timepoint; None if the
            current timepoint has ended

        @type location: Integer
        @param location: the location for which the script is interested in
        Functia din schelet, am mutat doar eventul script_received(l-am pus pe else
        pentru a face threadurile Master sa astepte dupa toate scripturile)
        """
        if script is not None:
            self.scripts.append((script, location))
        else:
            self.script_received.set()

    def get_data(self, location):
        """
        Returns the pollution value this device has for the given location.

        @type location: Integer
        @param location: a location for which obtain the data

        @rtype: Float
        @return: the pollution value
        Fata de schelet am restrictionat accesul(un singur thread are acces
        in acelasi timp pe sensor_data)
        """
        with self.get_lock:
            return self.sensor_data[location] if location in self.sensor_data else None

    def set_data(self, location, data):
        """
        Sets the pollution value stored by this device for the given location.

        @type location: Integer
        @param location: a location for which to set the data

        @type data: Float
        @param data: the pollution value
        Fata de schelet am restrictionat accesul(un singur thread are acces
        in acelasi timp la sensor_data)
        """
        with self.data_lock:
            if location in self.sensor_data:
                self.sensor_data[location] = data

    def shutdown(self):
        """
        Instructs the device to shutdown (terminate all threads). This method
        is invoked by the tester. This method must block until all the threads
        started by this device terminate.
        functie nemodificata
        """
        self.thread.join()


class DeviceThread(Thread):
    """
    Class that implements the device's worker thread.
    """

    def __init__(self, device):
        """
        Constructor.

        @type device: Device
        @param device: the device which owns this thread
        """
        Thread.__init__(self, name="Device Thread %d" % device.device_id)
        self.device = device

    def run(self):
        """
        Aici sunt threadurile Master
        In primul rand, astept sa mi se dea set pe eventul "setup", adica
        astept sa se faca setup-ul prima data.Dupa care, intru in bucla while
        care se va opri atunci cand nu mai sunt vecini(s-au terminat timepoint-urile).
        Apoi, creez threadurile, si pornesc doar 8 threaduri pana cand termin script-urile.
        Dupa, am grija sa dau join la aceste treaduri(sa le astept sa se termine), dupa care
        intru in bariera si astept ca toate threadurile Master sa ajunga acolo, si apoi trec
        la urmatorul timepoint
        """
        self.device.setup.wait()
        while True:
            threads = []
            neighbours = self.device.supervisor.get_neighbours()
            if neighbours is None:
                break
            self.device.script_received.wait()
            self.device.script_received.clear()
            i = 0
            for _ in self.device.scripts:
                threads.append(MyThread(self.device, self.device.scripts, neighbours, i))
                i = i + 1
            scripts_rem = len(self.device.scripts)
            start = 0
            if len(self.device.scripts) < 8:
                for thr in threads:
                    thr.start()
                for thr in threads:
                    thr.join()
            else:
                while True:
                    if scripts_rem == 0:
                        break
                    if scripts_rem >= 8:
                        for i in xrange(start, start + 8):
                            threads[i].start()
                        for i in xrange(start, start + 8):
                            threads[i].join()
                        start = start + 8
                        scripts_rem = scripts_rem - 8
                    else:
                        for i in xrange(start, start + scripts_rem):
                            threads[i].start()
                        for i in xrange(start, start + scripts_rem):
                            threads[i].join()
                        break
            self.device.barrier.wait()

class MyThread(Thread):
    """
    O clasa folosita pentru a folosi 8 threaduri care vor lucra cu scripturile
    device = device-ul respectiv
    scripts = lista de scripturi a device-ului
    neighbours = lista cu vecini
    indice = indicele din lista de scripturi cu care threadul trebuie sa lucreze
    """
    def __init__(self, device, scripts, neighbours, indice):
        Thread.__init__(self, name="Device Thread %d" % device.device_id)
        self.device = device
        self.scripts = scripts
        self.neighbours = neighbours
        self.indice = indice

    def run(self):
        """
        Extrag din lista de scripturi scriptul cu care trebuie sa lucrez, dupa care dau
        acquire pe locatia respectiva pentru a nu lasa alt thread care doreste sa foloseasca
        aceasta locatie sa o foloseasca.Fac operatiile din schelet(Adun date de la vecini,
        rulez scriptul si trimit vecinilor noile date), dupa care dau release pe locatie
        pentru a putea fi folosita si de alt thread
        """
        (script, location) = self.scripts[self.indice]
        self.device.locations[location].acquire()
        script_data = []
        for device in self.neighbours:
            data = device.get_data(location)
            if data is not None:
                script_data.append(data)
        data = self.device.get_data(location)
        if data is not None:
            script_data.append(data)
        if script_data != []:
            result = script.run(script_data)
            for device in self.neighbours:
                device.set_data(location, result)
                self.device.set_data(location, result)
        self.device.locations[location].release()

