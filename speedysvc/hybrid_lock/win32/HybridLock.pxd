cdef extern from "windows.h" nogil:
    ctypedef unsigned long DWORD
    ctypedef void *HANDLE
    ctypedef int BOOL
    ctypedef long LONG
    ctypedef void *LPCTSTR
    ctypedef void *LPVOID
    ctypedef void *LPCVOID
    ctypedef char *LPCSTR
    ctypedef Py_UNICODE WCHAR
    ctypedef const WCHAR* LPCWSTR
    ctypedef int* LPLONG
    ctypedef unsigned long long uint64_t
    ctypedef signed long long LONGLONG

    cdef struct SECURITY_ATTRIBUTES:
        pass

    ctypedef struct LARGE_INTEGER:
        DWORD LowPart
        DWORD HighPart
        LONGLONG QuadPart

    ctypedef struct FILETIME:
        DWORD dwLowDateTime
        DWORD dwHighDateTime

    void GetSystemTimeAsFileTime(FILETIME *time)

    DWORD GetLastError()

    # Create ctypes wrapper for Win32 functions we need, with correct argument/return types
    HANDLE CreateSemaphoreW(
            SECURITY_ATTRIBUTES   *lpSemaphoreAttributes,
            LONG                  lInitialCount,
            LONG                  lMaximumCount,
            LPCWSTR               lpName
    )
    HANDLE OpenSemaphoreW( DWORD   dwDesiredAccess,
        BOOL    bInheritHandle,
        LPCWSTR lpName
    )
    DWORD WaitForSingleObject(
        HANDLE hHandle,
        DWORD  dwMilliseconds
    )
    BOOL ReleaseSemaphore(
        HANDLE hSemaphore,
        LONG   lReleaseCount,
        LPLONG lpPreviousCount
    ) nogil
    BOOL CloseHandle(HANDLE hObject)


