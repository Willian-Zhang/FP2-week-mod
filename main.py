import struct
import zlib

GameTime = b'GameTimeMinutes\x00\x00\x0e\x00\x00\x00FloatProperty\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00'
HeaderSection = b'\xC1\x83\x2A\x9E\x22\x22\x22\x22\x00\x00\x02\x00\x00\x00\x00\x00\x03\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00'
splitter = HeaderSection[:8]
skip = len(HeaderSection) - len(splitter)
magic_num = 41
size_seek_back = -9

def times_found(data: bytes, to_find: bytes):
    found = 0
    pos = 0
    while True:
        pos = data.find(to_find, pos)
        if pos == -1:
            break
        found += 1
        pos += len(to_find)
    return found

def find_float(decompressed: bytes, to_find: bytes):
    found_pos = decompressed.index(to_find)
    bytes_found = decompressed[found_pos + len(to_find):][:4]
    val = struct.unpack('<f', bytes_found)[0]
    return val, bytes_found

def replace_float(splitted: list[bytes], decompreaable: list[bytes], found:bytes, to_find: bytes, new_float: float, should_replace_times: int, sanity=False):
    to_time = struct.pack('<f', new_float)
    to_find_original = to_find + found
    to_find_to_replace = to_find + to_time
    
    replaced = 0
    for index, part in enumerate(decompreaable, start=1):
        found = times_found(part, to_find_original)
        if found > 0:
            if sanity: 
                replaced_decoded = part
            else:
                replaced_decoded = part.replace(to_find_original, to_find_to_replace)
            encoded = zlib.compress(replaced_decoded)
            size = struct.pack('<H', len(encoded))
            assert len(size) == 2
            section = HeaderSection.replace(b'\xFF\xFF', size)[len(splitter):] + zlib.compress(replaced_decoded)
            splitted[index] = section
            replaced += found
    assert replaced == should_replace_times, f"Fail to fix the file, please try resave it. (replaced {replaced} times)"
    
def split_binary_file(filename: str, to_day: float, sanity=False, write_raw=False):
    if sanity:
        print("Sanity check only")
    with open(filename, 'rb') as file:
        binary_data = file.read()

    splitted = binary_data.split(splitter)

    decompreaable = []
    # skips = []
    # sum = 0
    
    for index, part in enumerate(splitted[1:], start=1):
        r = part[skip:]
        skipped = part[:skip]
        mid_code = skipped[25:27]
        assert struct.unpack('<H', mid_code)[0] == len(r)
        
        try:
            decompreaable.append(zlib.decompress(r))
            # skips.append(skipped)
        except Exception as e:
            raise Exception(f'Error decompressing part {index}: {e}')
    # print(f"Total file size = {sum} bytes, count = {len(decompreaable)}")
    decompressed = b''.join(decompreaable)
    
    if write_raw:
        with open(f"{filename}.bin", 'wb') as file:
            file.write(decompressed)
    
    time, time_found = find_float(decompressed=decompressed, to_find=GameTime)
    print(f"Found play time {time/1440/7} ({time_found.hex()}) weeks") 
    assert times_found(decompressed, GameTime + time_found) == 3
    
    replace_float(splitted=splitted, decompreaable=decompreaable, found=time_found, to_find=GameTime,  new_float=to_day * 1440 * 7, should_replace_times=3, sanity=sanity)

    # + len(splitter) for splitter
    accu_size = sum([len(part) + len(splitter) for part in splitted[1:]])
    
    from_total_size = struct.unpack('<I', splitted[0][-4:])[0]
    to_total_size = struct.pack('<I', accu_size)
    print(f"Total size changed from {from_total_size} ({splitted[0][-4:].hex()}) to {accu_size} ({to_total_size.hex()})")
    if sanity:
        assert from_total_size == accu_size, "Sanity check failed, the total size is not the same"
        print("Sanity check passed")
        return
    splitted[0] = splitted[0][:-4] + to_total_size
    
    # filename_part = filename.split('/')[-1]
    new_name = f"{filename}.fixed"
    with open(new_name, 'wb') as file:
        file.write(splitter.join(splitted))
        
    print(f"Fixed file saved as {new_name}, you may replace the origianl file with it (Always make a backup first!)")
    



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Parse binary file')
    parser.add_argument('filename', type=str, help='Binary file to parse')
    parser.add_argument('--to-day', type=float, help='Set the play time to this day (default 301.0)')
    parser.add_argument('--sanity', action='store_true', help='Do not replace the play time, only check sanity')
    
    args = parser.parse_args()
    split_binary_file(args.filename, to_day=args.to_day if args.to_day else 100.0, sanity=args.sanity)
