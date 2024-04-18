import struct
import zlib
import os

GameTime    = b'GameTimeMinutes\x00\x00\x0e\x00\x00\x00FloatProperty\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00'
TicksPassed = b'TicksPassedCount\x00\x00\x0f\x00\x00\x00UInt32Property\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00'
LogicTicks  = b'LogicTicksPassedCount\x00\x1f\x04\x00\x00\x00\x00\x00\x00\x00\x00'
# BetaTimeout = b'BETA TIMEOUT\x00\x02 \x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00PXGameTime\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00ScaledTicks\x00\x13\x04\x00\x00\x00\x00\x00\x00\x00\x00'
CurrentGameTime = b'currentGameTime\x00\x00\x0f\x00\x00\x00StructProperty\x009\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00PXGameTime\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00ScaledTicks\x00\x00\x0c\x00\x00\x00IntProperty\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00'

HeaderSection = b'\xC1\x83\x2A\x9E\x22\x22\x22\x22\x00\x00\x02\x00\x00\x00\x00\x00\x03\xFF\xFF\xFF\xFF\x00\x00\x00\x00\xEE\xEE\xEE\xEE\x00\x00\x00\x00\xFF\xFF\xFF\xFF\x00\x00\x00\x00\xEE\xEE\xEE\xEE\x00\x00\x00\x00'
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

def find_32(decompressed: bytes, to_find: bytes, format='<f'):
    found_pos = decompressed.index(to_find)
    bytes_found = decompressed[found_pos + len(to_find):][:4]
    val = struct.unpack(format, bytes_found)[0]
    return val, bytes_found

def replace_32(decompressed: bytes, to_find: bytes, found:bytes, new_val: float|int, should_replace_times: int, sanity=False, format='<f'):
    to_bytes = struct.pack(format, new_val)
    to_find_original = to_find + found
    to_find_to_replace = to_find + to_bytes
    
    assert times_found(decompressed, to_find_original) == should_replace_times, f"Fail to find the play time, please try resave it. (found {times_found(decompressed, to_find_original)} times)"
    if sanity:
        return decompressed
    else:
        return decompressed.replace(to_find_original, to_find_to_replace)
    
def split_compress(decompressed: bytes, size_limit: int):
    splitted = []
    pos = 0
    while pos < len(decompressed):
        size = min(size_limit, len(decompressed) - pos)
        part = decompressed[pos:pos + size]
        compressed = zlib.compress(part)
        header = HeaderSection\
            .replace(b'\xFF\xFF\xFF\xFF', struct.pack('<I', len(compressed)))\
            .replace(b'\xEE\xEE\xEE\xEE', struct.pack('<I', size))
        splitted.append(header + compressed)
        pos += size
    return splitted

def save_data(filename:str, data: bytes):
    filename_parts = filename.split('/')
    filename_parts.insert(-1, "fixes")
    ptf = filename_parts[:-1]
    if ptf:
        os.makedirs("/".join(ptf), exist_ok=True)
        
    new_name = "/".join(filename_parts)
    with open(new_name, 'wb') as file:
        file.write(data)
    return new_name

def find_and_replace(name:str, decompressed: bytes, prefix: bytes, format: str, to_day: float, factor: int, offset:int=0, sanity=False, replace_times=1):
    val, found = find_32(decompressed=decompressed, to_find=prefix, format=format)
    print(f"Found {name} {val/factor+offset} weeks ({found.hex()})")
    new_val = (to_day - offset) * factor 
    if format[-1].upper() in ['I', 'H', 'L', 'Q']:
        new_val = int(new_val)
    return replace_32(decompressed=decompressed, to_find=prefix, found=found, new_val=new_val, should_replace_times=replace_times, sanity=sanity, format=format)

def split_binary_file(filename: str, to_day: float, sanity=False, write_raw=False):
    if sanity:
        print("Sanity check only")
    with open(filename, 'rb') as file:
        binary_data = file.read()

    splitted = binary_data.split(splitter)

    decompreaable = []
    # skips = []
    # sum = 0
    
    header = splitted[0]
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
    
    size_limit = len(decompreaable[1])
    print(f"Decompressed size = {len(decompressed)} bytes, size limit = {size_limit} bytes")
    
    if write_raw:
        with open(f"{filename}.bin", 'wb') as file:
            file.write(decompressed)
        
    # decompressed = find_and_replace('GameTime', decompressed=decompressed, prefix=GameTime, format='<f', to_day=to_day, factor=60*24*7, sanity=sanity, replace_times=3)
    # decompressed = find_and_replace('TicksPassed', decompressed=decompressed, prefix=TicksPassed, format='<I', to_day=to_day, factor=60*24, sanity=sanity)
    # decompressed = find_and_replace('LogicTicks', decompressed=decompressed, prefix=LogicTicks, format='<I', to_day=to_day, factor=24, offset=1, sanity=sanity)
    # decompressed = find_and_replace('BetaTimeout', decompressed=decompressed, prefix=BetaTimeout, format='<I', to_day=300*16, factor=24*7*10, sanity=sanity)    
    decompressed = find_and_replace('CurrentGameTime', decompressed=decompressed, prefix=CurrentGameTime, format='<i', to_day=to_day, factor=7*24*10, sanity=sanity, replace_times=1)
    
    if write_raw:
        save_data(f"{filename}.bin", decompressed)
            
    new_splits = split_compress(decompressed, size_limit=size_limit)
    splitted = [header] + new_splits
    accu_size = sum([len(part) for part in new_splits])
    
    from_total_size = struct.unpack('<I', header[-4:])[0]
    to_total_size = struct.pack('<I', accu_size)
    print(f"Total size changed from {from_total_size} ({header[-4:].hex()}) to {accu_size} ({to_total_size.hex()})")
    if sanity:
        assert from_total_size == accu_size, "Sanity check failed, the total size is not the same"
        print("Sanity check passed")
        return
    splitted[0] = header[:-4] + to_total_size
    
    new_name = save_data(filename, b''.join(splitted))
    print(f"Fixed file saved as {new_name}, you may replace the origianl file with it (Always make a backup first!)")
    
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Parse binary file')
    parser.add_argument('filename', type=str, help='Binary file to parse')
    parser.add_argument('--to-day', type=float, help='Set the play time to this day (in weeks)')
    parser.add_argument('--sanity', action='store_true', help='Do not replace the play time, only check sanity')
    parser.add_argument('--write-raw', action='store_true', help='Write the raw decompressed data to a file')
    
    args = parser.parse_args()
    split_binary_file(args.filename, to_day=args.to_day if args.to_day else -10000.0, sanity=args.sanity, write_raw=args.write_raw)
