import gc
import os
import sys
import psutil


def get_memory_usage_mb() -> float:
    """
    Returns current process Resident Set Size (RSS) in Megabytes.
    """
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def optimize_memory(tag: str = "") -> dict:
    """
    Aggressively triggers garbage collection and instructs the C library
    allocator (glibc on Linux) to release freed heap pages back to the OS.
    Critical for free-tier containers with 512 MB memory constraints.
    """
    before_mb = get_memory_usage_mb()

    # Step 1: Force Python garbage collection
    collected = gc.collect()

    # Step 2: Linux glibc heap trimming
    # When deployed on Linux containers (Render, Railway, Fly.io, etc.),
    # malloc_trim(0) returns unmapped memory directly to the OS kernel.
    trimmed = False
    if sys.platform.startswith("linux"):
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            if hasattr(libc, "malloc_trim"):
                libc.malloc_trim(0)
                trimmed = True
        except Exception:
            pass

    after_mb = get_memory_usage_mb()
    freed_mb = max(0.0, before_mb - after_mb)

    prefix = f"[{tag}] " if tag else ""
    print(
        f"{prefix}Memory cleanup: collected {collected} objects, "
        f"freed {freed_mb:.2f} MB (Current RSS: {after_mb:.2f} MB, malloc_trim={trimmed})"
    )

    return {
        "before_mb": before_mb,
        "after_mb": after_mb,
        "freed_mb": freed_mb,
        "collected_objects": collected,
        "malloc_trim_invoked": trimmed,
    }

