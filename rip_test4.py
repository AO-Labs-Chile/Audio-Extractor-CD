import ctypes

kernel32 = ctypes.windll.kernel32

class RAW_READ_INFO(ctypes.Structure):
    _fields_ = [
        ("DiskOffset", ctypes.c_longlong),
        ("SectorCount", ctypes.c_ulong),
        ("TrackMode", ctypes.c_int),
    ]

def test_raw_read():
    for i in range(4):
        drive = fr"\\.\CdRom{i}"
        handle = kernel32.CreateFileW(drive, 0x80000000, 1, None, 3, 0, None)
        if handle == -1 or handle == 0:
            continue
        
        print(f"Opened {drive}")
        
        lba = 150
        num_sectors = 1
        buf_size = 2352 * num_sectors
        buf = (ctypes.c_ubyte * buf_size)()

        rri = RAW_READ_INFO()
        rri.DiskOffset = lba * 2048
        rri.SectorCount = num_sectors
        rri.TrackMode = 2 # CDDA

        bytes_returned = ctypes.c_ulong(0)
        res = kernel32.DeviceIoControl(
            handle, 0x2403E,
            ctypes.byref(rri), ctypes.sizeof(rri),
            ctypes.byref(buf), buf_size,
            ctypes.byref(bytes_returned), None
        )

        kernel32.CloseHandle(handle)
        
        if res:
            print(f"Success on {drive}! Read {bytes_returned.value} bytes.")
            print(f"First 10 bytes: {bytes(buf[:10]).hex()}")
            return
        else:
            err = ctypes.GetLastError()
            print(f"DeviceIoControl failed on {drive} with error {err}")

test_raw_read()
