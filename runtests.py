#!/usr/bin/env python
# -*- coding: utf-8 -*-

# python deps
import os
import sys
import glob
if sys.version_info[0] >= 3:
    import queue as queue
    import subprocess as command
else:
    import Queue as queue
    import commands as command
import threading

def get_status_output(cmd):
    return command.getstatusoutput(cmd)

def extract_env(env):
    return os.path.expandvars(env)

def _get_cpu_count_linux():
    s, r = get_status_output("LANG=C lscpu | grep 'CPU(s):' | grep -v 'NUMA' | awk '{print$2}'")
    if s != 0:
        raise Exception(str((s, r)))
    else:
        return int(r)

def _get_cpu_count_bsd():
    s, r = get_status_output('sysctl -n hw.ncpu')
    if s != 0:
        raise Exception(str((s, r)))
    else:
        return int(r)

def _get_cpu_count_osx():
    s, r = get_status_output('sysctl -n hw.logicalcpu')
    if s != 0:
        raise Exception(str((s, r)))
    else:
        return int(r)

def _get_cpu_count_solaris():
    s, r = get_status_output('kstat -m cpu_info | egrep "module: cpu_info" | wc -l')
    if s != 0:
        raise Exception(str((s, r)))
    else:
        return int(r)

def _get_cpu_count_win32():
    return int(os.environ['NUMBER_OF_PROCESSORS'])

def get_cpu_count():
    try:
        if 'linux' in sys.platform:
            return _get_cpu_count_linux()
        elif 'bsd' in sys.platform:
            return _get_cpu_count_bsd()
        elif 'cygwin' in sys.platform:
            return _get_cpu_count_linux()
        elif 'darwin' in sys.platform:
            return _get_cpu_count_osx()
        elif 'sunos5' in sys.platform:
            return _get_cpu_count_solaris()
        elif 'win32' in sys.platform:
            return _get_cpu_count_win32()
        else:
            return 1
    except:
        return 1

class ThreadRWLock(object):
    def __init__(self):
        self._lock = threading.Condition(threading.Lock())
        self._readers = 0

    def acquire_read(self):
        self._lock.acquire()
        self._readers += 1
        self._lock.release()

    def release_read(self):
        self._lock.acquire()
        if self._readers == 0:
            self._lock.release()
            raise RuntimeError('the lock is not acquired')
        self._readers -= 1
        if self._readers == 0:
            self._lock.notify_all()
        self._lock.release()

    def acquire_write(self):
        self._lock.acquire()
        while self._readers > 0:
            self._lock.wait()

    def release_write(self):
        self._lock.release()

    def acquire(self):
        self.acquire_write()

    def release(self):
        self.release_write()


class WorkerThread(threading.Thread):
    def __init__(self, task_queue, cond):
        super(self.__class__, self).__init__()
        self._task_queue = task_queue
        self._cond = cond
        self._exit = False
        self._active = False
        self.start()

    def run(self):
        while True:
            try:
                func, args, kwargs = self._task_queue.get(block=False)
                self._active = True
                try:
                    func(*args, **kwargs)
                except:
                    pass
                self._active = False
                self._task_queue.task_done()
            except:
                self._cond.acquire()
                if self._exit:
                    self._cond.release()
                    break
                else:
                    self._cond.wait()
                self._cond.release()

    def exit(self):
        self._cond.acquire()
        self._exit = True
        self._cond.release()

    def is_active(self):
        return self._active

class ThreadPool(object):
    def __init__(self, worker_num=0):
        if worker_num == 0:
            worker_num = get_cpu_count()
        self.worker_num = int(worker_num)
        self.workers = []
        self.worker_class = None
        self.task_queue = queue.Queue()
        self.cond = threading.Condition(threading.Lock())
        self.ctrl_lock = ThreadRWLock()

    def __del__(self):
        self.wait_all_thrd()

    def start_pool(self):
        self.ctrl_lock.acquire()
        if not self.workers:
            for _ in range(self.worker_num):
                self.workers.append(WorkerThread(self.task_queue, self.cond))
        self.ctrl_lock.release()

    def add_task(self, func, *args, **kwargs):
        self.task_queue.put((func, args, kwargs))
        self.cond.acquire()
        self.cond.notify_all()
        self.cond.release()

    def get_worker_num(self):
        return self.worker_num

    def get_active_worker_num(self):
        self.ctrl_lock.acquire()
        sum = 0
        for worker in self.workers:
            if worker.is_active():
                sum += 1
        self.ctrl_lock.release()
        return sum
    
    def wait_all_thrd(self):
        try:
            self.ctrl_lock.acquire()
            for worker in self.workers:
                worker.exit()
            self.cond.acquire()
            self.cond.notify_all()
            self.cond.release()
            for worker in self.workers:
                if worker.is_alive():
                    worker.join()
            self.workers = []
        except:
            raise
        finally:
            self.ctrl_lock.release()


def run_test(result, lock, case):
    lock.acquire()
    result[case] = {}
    result[case]["ret"] = False
    result[case]["output"] = ""
    lock.release()
    ret, _ = get_status_output(extract_env('$CC $CFLAGS {case} -o {case}.bin >{case}.ccout 2>{case}.ccerr'.format(case = case)))
    if ret != 0:
        return False
    ret, _ = get_status_output(extract_env('./{case}.bin > {case}.output 2>&1'.format(case = case)))
    if ret != 0:
        return False
    ret, output = get_status_output('diff -u {case}.expected {case}.output'.format(case = case))
    if ret != 0:
        lock.acquire()
        result[case]["output"] = output
        lock.release()
        return False
    lock.acquire()
    result[case]["ret"] = True
    lock.release()
    return True

def execute_tests():
    print(extract_env('CC=${CC}'))
    print(extract_env('CFLAGS=${CFLAGS}'))

    TOTAL=0
    PASS=0
    FAIL=0
    FAIL_CASES=[]

    cwd=os.getcwd()
    os.chdir('testcases')
    result = {}
    lock = ThreadRWLock()
    thrd_pool = ThreadPool()

    cases = glob.glob('*.c')
    cases.sort()
    TOTAL=len(cases)
    thrd_pool.start_pool()
    for case in cases:
        thrd_pool.add_task(run_test, result, lock, case)
    thrd_pool.wait_all_thrd()
    for case in cases:
        if result[case]["ret"]:
            PASS += 1
        else:
            FAIL += 1
            if result[case]["output"]:
                print(result[case]["output"])
            FAIL_CASES.append(case)
    print('Summary')
    print('Total:')
    print(TOTAL)
    print('Pass:')
    print(PASS)
    print('Fail:')
    print(FAIL)
    print('Failed Cases:')
    print(' '.join(FAIL_CASES))
    os.chdir(cwd)

if __name__ == "__main__":
    execute_tests()
