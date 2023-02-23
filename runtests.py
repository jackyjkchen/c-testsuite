#!/usr/bin/env python
# -*- coding: utf-8 -*-

# python deps
import os
import sys
import glob
import subprocess
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
    s, r = get_status_output("echo $((`cat /sys/devices/system/cpu/online |awk -F '-' '{print$2}'` + 1))")
    if s != 0:
        raise Exception(str((s, r)))
    else:
        return int(r)

def _get_cpu_count_cygwin():
    s, r = get_status_output('cat /proc/cpuinfo | grep process | wc -l')
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
            return _get_cpu_count_cygwin()
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

class WorkerThread(threading.Thread):
    def __init__(self, task_queue, cond):
        super(self.__class__, self).__init__()
        self._task_queue = task_queue
        self._cond = cond
        self._exit = False
        self.start()

    def run(self):
        while True:
            try:
                func, args, kwargs = self._task_queue.get(block=False)
                try:
                    func(*args, **kwargs)
                except:
                    pass
                self._task_queue.task_done()
            except queue.Empty:
                self._cond.acquire()
                if self._exit:
                    self._cond.release()
                    break
                self._cond.wait()
                self._cond.release()

    def exit(self):
        self._cond.acquire()
        self._exit = True
        self._cond.release()

class ThreadPool(object):
    def __init__(self, worker_num=0):
        if worker_num == 0:
            worker_num = get_cpu_count()
        self.worker_num = int(worker_num)
        self.workers = []
        self.worker_class = None
        self.task_queue = queue.Queue()
        self.cond = threading.Condition(threading.Lock())
        self.ctrl_lock = threading.Lock()

    def __del__(self):
        self.wait_all_thrd()

    def start_pool(self):
        self.ctrl_lock.acquire()
        if not self.workers:
            for _ in range(self.worker_num):
                self.workers.append(WorkerThread(self.task_queue, self.cond))
        self.cond.acquire()
        self.cond.notify_all()
        self.cond.release()
        self.ctrl_lock.release()

    def add_task(self, func, *args, **kwargs):
        self.cond.acquire()
        self.task_queue.put((func, args, kwargs))
        self.cond.notify()
        self.cond.release()

    def get_worker_num(self):
        return self.worker_num

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
        finally:
            self.ctrl_lock.release()

def command_runner_nopipe(command):
    process = subprocess.Popen(command, stdin=None, stdout=None, stderr=None, shell=True, close_fds=True)
    process.communicate()
    return process.returncode

def run_test(result, lock, case):
    result_case = {}
    result_case["ret"] = False
    result_case["output"] = ""
    try:
        ret = command_runner_nopipe(extract_env('$CC {case} $CFLAGS -o {case}.bin >{case}.ccout 2>{case}.ccerr'.format(case = case)))
        if ret != 0:
            return False
        ret = command_runner_nopipe('./{case}.bin > {case}.output 2>&1'.format(case = case))
        if ret != 0:
            return False
        ret = command_runner_nopipe('diff -u {case}.expected {case}.output >{case}.outdiff 2>/dev/null'.format(case = case))
        if ret != 0:
            result_case["output"] = open('{case}.outdiff'.format(case = case)).read().strip()
            return False
        result_case["ret"] = True
        return True
    finally:
        lock.acquire()
        result[case] = result_case
        lock.release()

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
    lock = threading.Lock()
    thrd_pool = ThreadPool()

    cases = glob.glob('*.c')
    cases.sort()
    TOTAL=len(cases)
    for case in cases:
        thrd_pool.add_task(run_test, result, lock, case)
    thrd_pool.start_pool()
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
