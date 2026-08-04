import os
import sys
import ctypes
import struct
import subprocess
from typing import List, Dict, Any, Optional, Tuple

# Suppress Windows "No disk in drive" modal dialogs
if sys.platform == 'win32':
    try:
        ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x8000)
    except Exception:
        pass

class CDRipper:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32 if sys.platform == 'win32' else None

    def get_cd_drives(self) -> List[Dict[str, str]]:
        """
        Instant 0ms enumeration of CD/DVD drives on Windows.
        """
        drives = []
        if not self.kernel32:
            return drives

        bitmask = self.kernel32.GetLogicalDrives()
        for letter_code in range(26):
            if bitmask & (1 << letter_code):
                drive_letter = f"{chr(65 + letter_code)}:"
                drive_path = f"{drive_letter}\\"
                try:
                    drive_type = self.kernel32.GetDriveTypeW(drive_path)
                    # DRIVE_CDROM = 5
                    if drive_type == 5:
                        drives.append({
                            "drive": drive_letter,
                            "label": f"Lector {drive_letter}",
                            "has_disc": True
                        })
                except Exception:
                    pass

        return drives

    def check_disc_present(self, drive_letter: str) -> Tuple[bool, int]:
        """
        Directly checks for .cda files or SPTI TOC in drive.
        """
        cda_files = self.get_cda_files(drive_letter)
        if cda_files:
            return True, len(cda_files)

        toc = self.read_toc_spti(drive_letter)
        if toc and toc.get('tracks'):
            return True, len(toc['tracks'])

        return False, 0

    def get_cda_files(self, drive_letter: str) -> List[str]:
        """
        Returns list of .cda file paths in drive root sorted by track number.
        """
        drive_path = f"{drive_letter}\\"
        try:
            if not os.path.exists(drive_path):
                return []
            files = os.listdir(drive_path)
            cda_list = [os.path.join(drive_path, f) for f in files if f.lower().endswith('.cda')]
            
            def get_track_num(filepath):
                name = os.path.basename(filepath)
                digits = ''.join(filter(str.isdigit, name))
                return int(digits) if digits else 999
            
            return sorted(cda_list, key=get_track_num)
        except Exception as e:
            print(f"[CDRipper] Error reading CDA files from {drive_letter}: {e}")
            return []

    def parse_cda_file(self, cda_path: str) -> Optional[Dict[str, Any]]:
        """
        Parses binary RIFF CDA track header.
        """
        try:
            with open(cda_path, 'rb') as f:
                data = f.read(44)
                if len(data) < 44 or data[:4] != b'RIFF' or data[8:12] != b'CDDA':
                    return None
                
                track_num = struct.unpack_from('<H', data, 22)[0]
                start_sector = struct.unpack_from('<I', data, 28)[0]   # Offset 28 is Track Start (LBA)
                length_sectors = struct.unpack_from('<I', data, 32)[0] # Offset 32 is Track Length (LBA)
                duration_sec = length_sectors // 75
                
                return {
                    "track": track_num,
                    "cda_path": cda_path,
                    "start_sector": start_sector,
                    "length_sectors": length_sectors,
                    "duration_sec": duration_sec
                }
        except Exception as e:
            print(f"[CDRipper] Error parsing CDA file {cda_path}: {e}")
            return None

    def read_toc(self, drive_letter: str) -> Dict[str, Any]:
        """
        Reads complete CD Table of Contents (TOC).
        """
        cda_files = self.get_cda_files(drive_letter)
        tracks_data = []
        total_sectors = 0

        for cda in cda_files:
            info = self.parse_cda_file(cda)
            if info:
                tracks_data.append(info)
                total_sectors = max(total_sectors, info['start_sector'] + info['length_sectors'])
        
        if not tracks_data:
            spti_toc = self.read_toc_spti(drive_letter)
            if spti_toc:
                return spti_toc

        return {
            "tracks": tracks_data,
            "leadout_sector": total_sectors,
            "total_duration_sec": sum(t['duration_sec'] for t in tracks_data)
        }

    def read_toc_spti(self, drive_letter: str) -> Optional[Dict[str, Any]]:
        """
        Direct SPTI IOCTL_CDROM_READ_TOC_EX read via Windows kernel32 API.
        """
        if sys.platform != 'win32' or not self.kernel32:
            return None

        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        IOCTL_CDROM_READ_TOC_EX = 0x00240054

        device_name = f"\\\\.\\{drive_letter}"
        handle = self.kernel32.CreateFileW(
            device_name,
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None
        )

        if handle == -1 or handle == 0:
            return None

        try:
            buf_size = 804
            buf = (ctypes.c_ubyte * buf_size)()
            bytes_returned = ctypes.c_ulong(0)
            
            in_buf = (ctypes.c_ubyte * 4)()
            in_buf[0] = 0

            res = self.kernel32.DeviceIoControl(
                handle,
                IOCTL_CDROM_READ_TOC_EX,
                in_buf, 4,
                buf, buf_size,
                ctypes.byref(bytes_returned),
                None
            )

            if res:
                first_tr = buf[2]
                last_tr = buf[3]
                tracks = []
                total_sectors = 0
                
                idx = 4
                while idx + 8 <= bytes_returned.value:
                    tr_num = buf[idx + 2]
                    # Since we didn't set the MSF flag (in_buf[2] = 0), the address is a 32-bit big-endian LBA
                    lba_sector = (buf[idx + 4] << 24) | (buf[idx + 5] << 16) | (buf[idx + 6] << 8) | buf[idx + 7]
                    
                    if tr_num != 0xAA:
                        tracks.append({
                            "track": tr_num,
                            "start_sector": lba_sector,
                            "cda_path": os.path.join(f"{drive_letter}\\", f"Track{tr_num:02d}.cda")
                        })
                    else:
                        total_sectors = lba_sector
                    idx += 8
                
                for i in range(len(tracks)):
                    next_start = tracks[i+1]['start_sector'] if i+1 < len(tracks) else total_sectors
                    length_sec = next_start - tracks[i]['start_sector']
                    tracks[i]['length_sectors'] = length_sec
                    tracks[i]['duration_sec'] = length_sec // 75
                
                return {
                    "tracks": tracks,
                    "leadout_sector": total_sectors,
                    "total_duration_sec": sum(t['duration_sec'] for t in tracks)
                }
        except Exception as e:
            print(f"[CDRipper] SPTI error: {e}")
        finally:
            self.kernel32.CloseHandle(handle)
        
        return None

    def rip_track_to_wav(self, cda_path: str, start_lba: int, total_sectors: int, output_wav_path: str, progress_callback=None) -> bool:
        """
        Rips a single track natively via Windows IOCTL_CDROM_RAW_READ.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
        
        class RAW_READ_INFO(ctypes.Structure):
            _pack_ = 1
            _fields_ = [
                ("DiskOffset", ctypes.c_longlong),
                ("SectorCount", ctypes.c_ulong),
                ("TrackMode", ctypes.c_int),
            ]
        
        IOCTL_CDROM_RAW_READ = 0x2403E
        CDDA = 2
        
        # Find the correct CdRom device handle (drive letter handle might not support RAW_READ)
        handle = None
        for i in range(10):
            drive = fr"\\.\CdRom{i}"
            h = self.kernel32.CreateFileW(drive, 0x80000000, 1 | 2, None, 3, 0, None)
            if h != -1 and h != 0:
                # Test read 1 sector to verify this is the right CD
                rri = RAW_READ_INFO()
                rri.DiskOffset = start_lba * 2048
                rri.SectorCount = 1
                rri.TrackMode = CDDA
                buf = (ctypes.c_ubyte * 2352)()
                br = ctypes.c_ulong(0)
                res = self.kernel32.DeviceIoControl(h, IOCTL_CDROM_RAW_READ, ctypes.byref(rri), ctypes.sizeof(rri), ctypes.byref(buf), 2352, ctypes.byref(br), None)
                if res:
                    handle = h
                    break
                self.kernel32.CloseHandle(h)
                
        if not handle:
            print("[CDRipper] Could not find or access the CDROM device for RAW READ.")
            return False
            
        try:
            # WAV Header
            data_size = total_sectors * 2352
            byte_rate = 44100 * 2 * 2
            block_align = 4
            
            header = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVEfmt ' + struct.pack('<I', 16)
            header += struct.pack('<H', 1) + struct.pack('<H', 2) + struct.pack('<I', 44100)
            header += struct.pack('<I', byte_rate) + struct.pack('<H', block_align) + struct.pack('<H', 16)
            header += b'data' + struct.pack('<I', data_size)
            
            with open(output_wav_path, 'wb') as f_out:
                f_out.write(header)
                
                chunk_sectors = 27 # 27 sectors = ~63 KB, safe for IOCTL
                buf_size = 2352 * chunk_sectors
                buf = (ctypes.c_ubyte * buf_size)()
                bytes_returned = ctypes.c_ulong(0)
                
                sectors_read = 0
                while sectors_read < total_sectors:
                    to_read = min(chunk_sectors, total_sectors - sectors_read)
                    
                    rri = RAW_READ_INFO()
                    rri.DiskOffset = (start_lba + sectors_read) * 2048
                    rri.SectorCount = to_read
                    rri.TrackMode = CDDA
                    
                    res = self.kernel32.DeviceIoControl(
                        handle, IOCTL_CDROM_RAW_READ,
                        ctypes.byref(rri), ctypes.sizeof(rri),
                        ctypes.byref(buf), 2352 * to_read,
                        ctypes.byref(bytes_returned), None
                    )
                    
                    if not res:
                        print(f"[CDRipper] Raw read failed at sector {start_lba + sectors_read}")
                        break
                        
                    f_out.write(bytearray(buf)[:2352 * to_read])
                    sectors_read += to_read
                    
                    if progress_callback:
                        progress_callback(int((sectors_read / total_sectors) * 100))
                    
            return (sectors_read == total_sectors)
        except Exception as e:
            print(f"[CDRipper] Native rip error: {e}")
            return False
        finally:
            self.kernel32.CloseHandle(handle)
