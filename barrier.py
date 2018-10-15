import sys

from threading import *

""" 
    Ugly comments are ugly - nu folositi comentarii lungi pe aceeasi linie cu 
    codul, aici sunt doar pentru 'teaching purpose'
"""

class SimpleBarrier():
    """ Bariera ne-reentranta, implementata folosind un semafor """
    
    def __init__(self, num_threads):
        self.num_threads = num_threads
        self.count_threads = self.num_threads   # contorizeaza numarul de thread-uri ramase
        self.counter_lock = Lock()              # protejeaza accesarea/modificarea contorului
        self.threads_sem = Semaphore(0)         # blocheaza thread-urile ajunse
    
    def wait(self):
        with self.counter_lock:
            self.count_threads -= 1
            if self.count_threads == 0:          # a ajuns la bariera si ultimul thread
                for i in range(self.num_threads):
                    self.threads_sem.release()   # incrementeaza semaforul pentru a debloca num_threads thread-uri
        self.threads_sem.acquire()               # num_threads-1 threaduri se blocheaza aici
                                                 # contorul semaforului se decrementeaza de num_threads ori

class ReusableBarrierCond():
    """ Bariera reentranta, implementata folosind o variabila conditie """
    
    def __init__(self, num_threads):
        self.num_threads = num_threads
        self.count_threads = self.num_threads
        self.cond = Condition()                  # blocheaza/deblocheaza thread-urile
                                                 # protejeaza modificarea contorului
    
    def wait(self):
        self.cond.acquire()                      # intra in regiunea critica
        self.count_threads -= 1;
        if self.count_threads == 0:
            self.cond.notify_all()               # deblocheaza toate thread-urile
            self.count_threads = self.num_threads
        else:
            self.cond.wait();                    # blocheaza thread-ul eliberand in acelasi timp lock-ul
        self.cond.release();                     # iese din regiunea critica

class ReusableBarrierSem():
    """ Bariera reentranta, implementata folosind semafoare """
    
    def __init__(self, num_threads):
        self.num_threads = num_threads
        self.count_threads1 = self.num_threads
        self.count_threads2 = self.num_threads
        self.counter_lock = Lock()               # protejam accesarea/modificarea contoarelor
        self.threads_sem1 = Semaphore(0)         # blocam thread-urile in prima etapa
        self.threads_sem2 = Semaphore(0)         # blocam thread-urile in a doua etapa
    
    def wait(self):
        self.phase1()
        self.phase2()
    
    def phase1(self):
        with self.counter_lock:
            self.count_threads1 -= 1
            if self.count_threads1 == 0:
                for i in range(self.num_threads):
                    self.threads_sem1.release()
                self.count_threads1 = self.num_threads
        
        self.threads_sem1.acquire()
    
    def phase2(self):
        with self.counter_lock:
            self.count_threads2 -= 1
            if self.count_threads2 == 0:
                for i in range(self.num_threads):
                    self.threads_sem2.release()
                self.count_threads2 = self.num_threads
        
        self.threads_sem2.acquire()

class MyThread(Thread):
    """ Dummy thread pentru a testa comportamentul barierei """
    
    def __init__(self, tid, barrier):
        Thread.__init__(self)
        self.tid = tid
        self.barrier = barrier
    
    def run(self):
        for i in xrange(10): 
            self.barrier.wait()
            print "I'm Thread " + str(self.tid) + " after barrier, in step " + str(i) + "\n",

if __name__ == "__main__":
    if len(sys.argv) == 2:
        num_threads = int(sys.argv[1])
    else: 
        print "Usage: python " + sys.argv[0] + " num_threads"
        sys.exit(0)

    barrier = SimpleBarrier(num_threads)
    barrier = ReusableBarrierSem(num_threads)
    barrier = ReusableBarrierCond(num_threads)
    
    threads = []
    for i in xrange(num_threads):
        threads.append(MyThread(i, barrier))
        threads[-1].start()

    for t in threads:
        t.join()
