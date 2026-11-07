"""Windows Job Object: kernel-enforced tree teardown and aggregate commit limit."""
import ctypes
from ctypes import wintypes
import os

from ..traffic_collection.schema import require


class IO_COUNTERS(ctypes.Structure):
    _fields_=[(name,ctypes.c_ulonglong) for name in ['ReadOperationCount','WriteOperationCount','OtherOperationCount',
                                                   'ReadTransferCount','WriteTransferCount','OtherTransferCount']]


class BASIC_LIMIT(ctypes.Structure):
    _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),
              ('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),
              ('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),
              ('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]


class EXTENDED_LIMIT(ctypes.Structure):
    _fields_=[('BasicLimitInformation',BASIC_LIMIT),('IoInfo',IO_COUNTERS),
              ('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),
              ('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]


class WindowsJob:
    def __init__(self,memory_cap):
        require(os.name=='nt','windows_job_required')
        self.api=ctypes.WinDLL('kernel32',use_last_error=True)
        signatures={'CreateJobObjectW':([ctypes.c_void_p,wintypes.LPCWSTR],wintypes.HANDLE),
                    'SetInformationJobObject':([wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD],wintypes.BOOL),
                    'AssignProcessToJobObject':([wintypes.HANDLE,wintypes.HANDLE],wintypes.BOOL),
                    'OpenProcess':([wintypes.DWORD,wintypes.BOOL,wintypes.DWORD],wintypes.HANDLE),
                    'TerminateJobObject':([wintypes.HANDLE,wintypes.UINT],wintypes.BOOL),
                    'CloseHandle':([wintypes.HANDLE],wintypes.BOOL)}
        for name,(args,result) in signatures.items():
            function=getattr(self.api,name);function.argtypes=args;function.restype=result
        self.handle=self.api.CreateJobObjectW(None,None);require(bool(self.handle),'job_create_failed')
        info=EXTENDED_LIMIT();info.BasicLimitInformation.LimitFlags=0x2000|0x200  # kill-on-close + aggregate memory
        info.JobMemoryLimit=memory_cap
        if not self.api.SetInformationJobObject(self.handle,9,ctypes.byref(info),ctypes.sizeof(info)):
            self.close();require(False,'job_limits_failed')

    def assign(self,pid):
        process=self.api.OpenProcess(0x0100|0x0001|0x0400,False,pid)
        require(bool(process),'job_process_open_failed')
        try:require(bool(self.api.AssignProcessToJobObject(self.handle,process)),'job_assignment_failed')
        finally:self.api.CloseHandle(process)

    def terminate(self):
        if self.handle:self.api.TerminateJobObject(self.handle,72)

    def close(self):
        if self.handle:self.api.CloseHandle(self.handle);self.handle=None
