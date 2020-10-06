cdef extern from "process.h" nogil:
    int _getpid();

cdef extern from "windows.h" nogil:
    ctypedef unsigned long DWORD
    ctypedef DWORD *LPDWORD
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
    ctypedef Py_ssize_t SIZE_T

    BOOL TRUE, FALSE

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


    # https://github.com/sturlamolden/sharedmem-numpy/blob/master/sharedmem/sharedmemory_win.pyx
    DWORD ERROR_ALREADY_EXISTS, ERROR_INVALID_HANDLE

    HANDLE OpenFileMapping(
        DWORD dwDesiredAccess,
        BOOL bInheritHandle,
        LPCTSTR lpName)
    HANDLE CreateFileMapping(
        HANDLE hFile,
        SECURITY_ATTRIBUTES *lpAttributes,
        DWORD flProtect,
        DWORD dwMaximumSizeHigh, DWORD dwMaximumSizeLow,
        LPCTSTR lpName)
    DWORD PAGE_READWRITE
    LPVOID MapViewOfFile(
        HANDLE hFileMappingObject,
        DWORD dwDesiredAccess,
        DWORD dwFileOffsetHigh, DWORD dwFileOffsetLow,
        DWORD dwNumberOfBytesToMap)
    BOOL  UnmapViewOfFile(LPCVOID lpBaseAddress)

    HANDLE LoadLibrary(LPCTSTR lpFileName)
    BOOL FreeLibrary(HANDLE hModule)
    LPVOID GetProcAddress(HANDLE hModule, LPCSTR lpProcName)

    HANDLE OpenProcess(
        DWORD dwDesiredAccess,
        BOOL  bInheritHandle,
        DWORD dwProcessId
    )
    BOOL GetExitCodeProcess(
        HANDLE  hProcess,
        LPDWORD lpExitCode
    );


