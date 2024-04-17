import zlib


# binary_pattern = b'\xC1\x83\x2A\x9E\x22\x22\x22\x22\x00\x00\x02\x00\x00\x00\x00\x00\x03..\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00..\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00'
skip = len("C1832A9E222222220000020000000000036221000000000000000002000000000062210000000000000000020000000000") // 2 - 8
def split_binary_file(filename):
    with open(filename, 'rb') as file:
        binary_data = file.read()

    parts = binary_data.split(b"\xC1\x83\x2A\x9E\x22\x22\x22\x22")[1:]

    filename_part = filename.split('/')[-1]
    decompressed = []
    for index, part in enumerate(parts):
        r = part[skip:]
        try:
            decompressed.append(zlib.decompress(r))
        except Exception as e:
            raise Exception(f'Error decompressing part {index}: {e}')
            
    decompressed = b''.join(decompressed)
    with open(f"{filename}.decompressed.bin", 'wb') as file:
        file.write(decompressed)



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Parse binary file')
    parser.add_argument('filename', type=str, help='Binary file to parse')

    args = parser.parse_args()
    split_binary_file(args.filename)
