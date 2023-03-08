#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import glob
import queue
import threading
import subprocess

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
                    import traceback
                    sys.stderr.write('%s%s' % (traceback.format_exc(), os.linesep))
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
    def __init__(self, worker_num=os.cpu_count()):
        self.worker_num = int(worker_num)
        self.workers = []
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

def run_test(result, lock, case):
    result_case = {}
    result_case["ret"] = False
    result_case["output"] = ""
    process = None
    while True:
        try:
            case_ccout = open('{case}.ccout'.format(case = case), 'w')
            case_ccerr = open('{case}.ccerr'.format(case = case), 'w')
            process = subprocess.Popen(os.path.expandvars('$CC {case} $CFLAGS -o {case}.bin'.format(case = case)).split(' '), stdin=open(os.devnull), stdout=case_ccout, stderr=case_ccerr, shell=False, close_fds=True)
            process.communicate(60)
            if process.returncode != 0:
                return False
            case_output = open('{case}.output'.format(case = case), 'w')
            process = subprocess.Popen(['./{case}.bin'.format(case = case)], stdin=open(os.devnull), stdout=case_output, stderr=open(os.devnull, 'w'), shell=False, close_fds=True)
            process.communicate(60)
            if process.returncode != 0:
                return False
            case_outdiff = open('{case}.outdiff'.format(case = case), 'w')
            process = subprocess.Popen('diff --ignore-trailing-space -u {case}.expected {case}.output'.format(case = case).split(' '), stdin=open(os.devnull), stdout=case_outdiff, stderr=open(os.devnull, 'w'), shell=False, close_fds=True)
            process.communicate(60)
            if process.returncode != 0:
                result_case["output"] = open('{case}.outdiff'.format(case = case)).read().strip()
                return False
            result_case["ret"] = True
            return True
        except subprocess.TimeoutExpired:
            process.kill()
            sys.stderr.write('Retry hang, case: %s%s' % (case, os.linesep))
        finally:
            lock.acquire()
            result[case] = result_case
            lock.release()

def execute_tests():
    print(os.path.expandvars('CC=${CC}'))
    print(os.path.expandvars('CFLAGS=${CFLAGS}'))

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
        if not result[case]["ret"]:
            FAIL += 1
            if result[case]["output"]:
                print(result[case]["output"])
            FAIL_CASES.append(case)
    PASS = TOTAL - FAIL
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
