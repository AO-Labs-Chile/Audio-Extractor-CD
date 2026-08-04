import ctypes
import struct

kernel32 = ctypes.windll.kernel32

class SCSI_PASS_THROUGH_DIRECT(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("Length", ctypes.c_ushort),
        ("ScsiStatus", ctypes.c_ubyte),
        ("PathId", ctypes.c_ubyte),
        ("TargetId", ctypes.c_ubyte),
        ("Lun", ctypes.c_ubyte),
        ("CdbLength", ctypes.c_ubyte),
        ("SenseInfoLength", ctypes.c_ubyte),
        ("DataIn", ctypes.c_ubyte),
        ("DataTransferLength", ctypes.c_ulong),
        ("TimeOutValue", ctypes.c_ulong),
        ("DataBuffer", ctypes.c_void_p),
        ("SenseInfoOffset", ctypes.c_ulong),
        ("Cdb", ctypes.c_ubyte * 16),
    ]

def test_rip():
    drive = r"\\.\H:"
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    IOCTL_SCSI_PASS_THROUGH_DIRECT = 0x4D014

    handle = kernel32.CreateFileW(drive, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
    if handle == -1 or handle == 0:
        print("Failed to open drive")
        return

    lba = 150
    num_sectors = 1
    buf_size = 2352 * num_sectors
    buf = (ctypes.c_ubyte * buf_size)()

    sptd = SCSI_PASS_THROUGH_DIRECT()
    sptd.Length = ctypes.sizeof(SCSI_PASS_THROUGH_DIRECT)
    sptd.CdbLength = 12
    sptd.DataIn = 1
    sptd.DataTransferLength = buf_size
    sptd.TimeOutValue = 10
    sptd.DataBuffer = ctypes.cast(ctypes.pointer(buf), ctypes.c_void_p)
    sptd.SenseInfoLength = 0
    sptd.SenseInfoOffset = 0

    sptd.Cdb[0] = 0xBE
    sptd.Cdb[1] = 0
    sptd.Cdb[2] = (lba >> 24) & 0xFF
    sptd.Cdb[3] = (lba >> 16) & 0xFF
    sptd.Cdb[4] = (lba >> 8) & 0xFF
    sptd.Cdb[5] = lba & 0xFF
    sptd.Cdb[6] = (num_sectors >> 16) & 0xFF
    sptd.Cdb[7] = (num_sectors >> 8) & 0xFF
    sptd.Cdb[8] = num_sectors & 0xFF
    sptd.Cdb[9] = 0x10
    sptd.Cdb[10] = 0
    sptd.Cdb[11] = 0

    bytes_returned = ctypes.c_ulong(0)
    res = kernel32.DeviceIoControl(
        handle, IOCTL_SCSI_PASS_THROUGH_DIRECT,
        ctypes.byref(sptd), ctypes.sizeof(sptd),
        ctypes.byref(sptd), ctypes.sizeof(sptd),
        ctypes.byref(bytes_returned), None
    )

    kernel32.CloseHandle(handle)
    
    if res:
        print(f"Success! Read {buf_size} bytes.")
    else:
        err = ctypes.GetLastError()
        print(f"DeviceIoControl failed with error {err}")

test_rip()
