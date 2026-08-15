import sys
import struct

def u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]

def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]

def main():
    # 실행할 때 증거 이미지명을 입력받음
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <image>")
        return

    with open(sys.argv[1], "rb") as f:

        # Boot Sector 읽기
        boot = f.read(512)

        bytes_per_sector = u16(boot, 11)
        sectors_per_cluster = boot[13]
        reserved_sectors = u16(boot, 14)
        num_fats = boot[16]
        fat_size = u32(boot, 36)
        root_cluster = u32(boot, 44)

        cluster_size = bytes_per_sector * sectors_per_cluster

        # FAT 영역 시작 위치
        fat_offset = reserved_sectors * bytes_per_sector

        # Data 영역 시작 Sector
        first_data_sector = reserved_sectors + (num_fats * fat_size)

        # Cluster 번호를 실제 이미지 offset으로 변환
        def cluster_offset(cluster):
            sector = first_data_sector + (cluster - 2) * sectors_per_cluster
            return sector * bytes_per_sector

        # FAT에서 다음 Cluster 번호 읽기
        def next_cluster(cluster):
            f.seek(fat_offset + cluster * 4)
            value = struct.unpack("<I", f.read(4))[0]
            return value & 0x0FFFFFFF

        # Root Directory의 첫 Cluster부터 시작
        cluster = root_cluster

        while cluster < 0x0FFFFFF8:

            f.seek(cluster_offset(cluster))
            data = f.read(cluster_size)

            # Directory Entry는 하나당 32 byte
            for i in range(0, cluster_size, 32):

                entry = data[i:i + 32]

                # Directory 끝
                if entry[0] == 0x00:
                    return

                # 삭제된 Entry
                if entry[0] == 0xE5:
                    continue

                attribute = entry[11]

                # LFN 무시
                if attribute == 0x0F:
                    continue

                # Volume Label 무시
                if attribute & 0x08:
                    continue

                # 8.3 파일명
                name = entry[0:8].decode("ascii", errors="ignore").rstrip()
                ext = entry[8:11].decode("ascii", errors="ignore").rstrip()

                if ext:
                    filename = name + "." + ext
                else:
                    filename = name

                # 시작 Cluster
                cluster_high = u16(entry, 20)
                cluster_low = u16(entry, 26)

                start_cluster = (cluster_high << 16) | cluster_low

                # File Size
                filesize = u32(entry, 28)

                print(f"{filename},{start_cluster},{filesize}")

            # Root Directory가 다음 Cluster로 이어져 있으면 이동
            cluster = next_cluster(cluster)


if __name__ == "__main__":
    main()