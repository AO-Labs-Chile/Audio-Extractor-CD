import ctypes

kernel32 = ctypes.windll.kernel32

class RAW_READ_INFO(ctypes.Structure):
    _fields_ = [
        ("DiskOffset", ctypes.c_longlong),
        ("SectorCount", ctypes.c_ulong),
        ("TrackMode", ctypes.c_int),
    ]

def test_raw_read():
    drive = r"\\.\H:"
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    OPEN_EXISTING = 3
    IOCTL_CDROM_RAW_READ = 0x2403E
    CDDA = 2

    handle = kernel32.CreateFileW(drive, GENERIC_READ, FILE_SHARE_READ, None, OPEN_EXISTING, 0, None)
    if handle == -1 or handle == 0:
        print("Failed to open drive")
        return

    lba = 150
    num_sectors = 1
    buf_size = 2352 * num_sectors
    buf = (ctypes.c_ubyte * buf_size)()

    rri = RAW_READ_INFO()
    rri.DiskOffset = lba * 2048
    rri.SectorCount = num_sectors
    rri.TrackMode = CDDA

    bytes_returned = ctypes.c_ulong(0)
    res = kernel32.DeviceIoControl(
        handle, IOCTL_CDROM_RAW_READ,
        ctypes.byref(rri), ctypes.sizeof(rri),
        ctypes.byref(buf), buf_size,
        ctypes.byref(bytes_returned), None
    )

    kernel32.CloseHandle(handle)
    
    if res:
        print(f"Success! Read {bytes_returned.value} bytes.")
        print(f"First 10 bytes: {bytes(buf[:10]).hex()}")
    else:
        err = ctypes.GetLastError()
        print(f"DeviceIoControl failed with error {err}")

test_raw_read()
