import os


def get_uptime_seconds() -> float:
    try:
        with open('/proc/uptime') as f:
            uptime_str = f.readline().split()[0]
            return float(uptime_str)
    except Exception:
        return 0.0


def format_uptime(seconds: float) -> str:
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    parts = []
    if days > 0:
        parts.append(f'{days}d')
    if hours > 0:
        parts.append(f'{hours}h')
    parts.append(f'{minutes}m')
    return ' '.join(parts)


def get_kernel_info() -> tuple[str, str]:
    uts = os.uname()
    return uts.sysname, uts.release


def get_cpu_counts() -> int:
    cores = set()
    try:
        with open('/proc/cpuinfo') as f:
            for line in f:
                if line.startswith('processor'):
                    cores.add(line.split(':')[1].strip())
        logical = len(cores)
    except Exception:
        logical = 0
    return logical


def get_cpu_name() -> str:
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line.startswith('model name'):
                name = line.split(':')[1].strip()
                return name.split("@")[0]
    return 'Unknown CPU'


def get_cpu_percent(
    prev_total: int, prev_idle: int
) -> tuple[int, int, int]:
    with open("/proc/stat") as f:
        fields = list(map(int, f.readline().strip().split()[1:]))
        total = sum(fields)
        idle = fields[3]

    delta_total = total - prev_total
    delta_idle = idle - prev_idle

    if delta_total == 0:
        return 0.0

    return int(100.0 * (delta_total - delta_idle) / delta_total), total, idle


def get_memory_total() -> float:
    meminfo: dict[str, int] = {}

    with open("/proc/meminfo") as f:
        for line in f:
            key, value, *_ = line.strip().split()
            meminfo[key.rstrip(":")] = int(value)

    total = meminfo.get("MemTotal", 0)
    return total / 1024


def get_memory_usage() -> tuple[float, float, float]:
    meminfo: dict[str, int] = {}

    with open("/proc/meminfo") as f:
        for line in f:
            key, value, *_ = line.strip().split()
            meminfo[key.rstrip(":")] = int(value)

    total = meminfo.get("MemTotal", 0)
    free = (
        meminfo.get("MemFree", 0)
        + meminfo.get("Buffers", 0)
        + meminfo.get("Cached", 0)
    )
    used = total - free
    percent = 100.0 * used / total

    return total / 1024, used / 1024, percent


def get_swap_total() -> float:
    meminfo: dict[str, int] = {}

    with open("/proc/meminfo") as f:
        for line in f:
            key, value, *_ = line.strip().split()
            meminfo[key.rstrip(":")] = int(value)
    total = meminfo.get("SwapTotal", 0)
    return total / 1024


def get_swap_usage() -> tuple[float, float, float]:
    meminfo: dict[str, int] = {}

    with open("/proc/meminfo") as f:
        for line in f:
            key, value, *_ = line.strip().split()
            meminfo[key.rstrip(":")] = int(value)

    total = meminfo.get("SwapTotal", 0)
    free = meminfo.get("SwapFree", 0)
    used = total - free
    percent = 100.0 * used / total if total > 0 else 0.0

    return total / 1024, used / 1024, percent
