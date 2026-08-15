import sys
import struct


def read_u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def read_u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def get_short_filename(entry):
    name = entry[0:8].decode("ascii", errors="ignore").rstrip()
    ext = entry[8:11].decode("ascii", errors="ignore").rstrip()

    if ext:
        return name + "." + ext

    return name


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <fat32 image>")
        return

    image_name = sys.argv[1]

    with open(image_name, "rb") as f:

        # -------------------------
        # 1. FAT32 Boot Sector
        # -------------------------
        boot = f.read(512)

        bytes_per_sector = read_u16(boot, 11)
        sectors_per_cluster = boot[13]
        reserved_sector_count = read_u16(boot, 14)
        number_of_fats = boot[16]
        fat_size = read_u32(boot, 36)
        root_cluster = read_u32(boot, 44)

        cluster_size = bytes_per_sector * sectors_per_cluster

        # FAT 시작 위치
        fat_offset = reserved_sector_count * bytes_per_sector

        # Data 영역 시작 위치
        first_data_sector = (
            reserved_sector_count
            + number_of_fats * fat_size
        )

        # cluster 번호 -> 실제 이미지 offset
        def cluster_offset(cluster):
            sector = (
                first_data_sector
                + (cluster - 2) * sectors_per_cluster
            )

            return sector * bytes_per_sector

        # -------------------------
        # 2. FAT에서 다음 Cluster 찾기
        # -------------------------
        def next_cluster(cluster):
            offset = fat_offset + cluster * 4

            f.seek(offset)

            value = struct.unpack("<I", f.read(4))[0]

            # FAT32에서는 하위 28bit만 사용
            return value & 0x0FFFFFFF

        # -------------------------
        # 3. Root Directory 탐색
        # -------------------------
        current_cluster = root_cluster

        while current_cluster < 0x0FFFFFF8:

            f.seek(cluster_offset(current_cluster))

            cluster_data = f.read(cluster_size)

            for i in range(0, cluster_size, 32):

                entry = cluster_data[i:i + 32]

                first_byte = entry[0]

                # 0x00 : 이후 Directory Entry 없음
                if first_byte == 0x00:
                    return

                # 0xE5 : 삭제된 파일
                if first_byte == 0xE5:
                    continue

                attribute = entry[11]

                # LFN Entry
                if attribute == 0x0F:
                    continue

                # Volume Label
                if attribute & 0x08:
                    continue

                filename = get_short_filename(entry)

                # 시작 Cluster
                cluster_high = read_u16(entry, 20)
                cluster_low = read_u16(entry, 26)

                start_cluster = (
                    (cluster_high << 16)
                    | cluster_low
                )

                # 파일 크기
                filesize = read_u32(entry, 28)

                print(f"{filename},{start_cluster},{filesize}")

            current_cluster = next_cluster(current_cluster)


if __name__ == "__main__":
    main()