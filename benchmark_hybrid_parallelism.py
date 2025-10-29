#!/usr/bin/env python3
"""
Hybrid parallelism benchmark: Compare Python threading vs Rust rayon parallelization.

This benchmark tests both approaches:
1. Python threading: Uses ThreadPoolExecutor to read files and call Rust individually
2. Rust parallelism: Uses rayon to batch process files in parallel within Rust
"""

import sys
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count

try:
    import xxhash
    HAS_XXHASH = True
except ImportError:
    HAS_XXHASH = False

try:
    import sys as sys_module
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    if os.path.exists(src_path):
        sys_module.path.insert(0, src_path)
    from xxhash_rust import xxh64, batch_xxh64, set_rayon_threads, get_rayon_threads
    HAS_RUST = True
except ImportError:
    HAS_RUST = False
    print("Warning: xxhash-rust not available")


def get_files(directory: Path, max_files: int = 1000):
    """Get list of files from directory."""
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            filepath = Path(root) / filename
            try:
                size = filepath.stat().st_size
                files.append((filepath, size))
            except (OSError, PermissionError):
                continue
    files.sort(key=lambda x: x[1])
    return files[:max_files]


def read_file(path: Path) -> bytes:
    """Read file contents."""
    try:
        with open(path, 'rb') as f:
            return f.read()
    except Exception as e:
        return b''


def benchmark_python_threading_rust(files, num_threads: int = 4):
    """Use Python threading + Rust (individual calls)."""
    if not HAS_RUST:
        return 0, []
    
    def worker(filepath: Path) -> float:
        data = read_file(filepath)
        if not data:
            return 0
        start = time.perf_counter()
        xxh64(data, 0)
        return (time.perf_counter() - start) * 1e6
    
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        latencies = list(executor.map(worker, [f for f, _ in files]))
    total_time = time.perf_counter() - start
    
    return total_time, latencies


def benchmark_rust_parallel_batch(files):
    """Use Rust rayon for batch parallel processing."""
    if not HAS_RUST or batch_xxh64 is None:
        return 0, []
    
    # Read all files
    read_start = time.perf_counter()
    data_list = []
    for filepath, size in files:
        data = read_file(filepath)
        if data:
            data_list.append(data)
    read_time = time.perf_counter() - read_start
    
    # Process with Rust parallelism
    process_start = time.perf_counter()
    results = batch_xxh64(data_list)
    process_time = time.perf_counter() - process_start
    
    total_time = read_time + process_time
    latencies = [process_time * 1e6 / len(results)] * len(results) if results else []
    
    print(f"   I/O time: {read_time:.3f}s")
    print(f"   Processing time: {process_time:.3f}s")
    
    return process_time, latencies


def benchmark_rust_parallel_batch_with_reading(files, num_threads: int = 4):
    """Hybrid: Python threading for I/O + Rust parallelism for processing."""
    if not HAS_RUST or batch_xxh64 is None:
        return 0, []
    
    # Read files in parallel using Python threads
    read_start = time.perf_counter()
    
    def read_worker(filepath: Path) -> bytes:
        return read_file(filepath)
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        data_list = list(executor.map(read_worker, [f for f, _ in files]))
        data_list = [d for d in data_list if d]  # Filter empty
    
    read_time = time.perf_counter() - read_start
    
    # Process with Rust parallelism
    process_start = time.perf_counter()
    results = batch_xxh64(data_list)
    process_time = time.perf_counter() - process_start
    
    total_time = read_time + process_time
    latencies = [process_time * 1e6 / len(results)] * len(results) if results else []
    
    print(f"   I/O time: {read_time:.3f}s")
    print(f"   Processing time: {process_time:.3f}s")
    
    return process_time, latencies  # Return just processing for fair comparison


def benchmark_c_threading(files, num_threads: int = 4):
    """Use Python threading + C (individual calls)."""
    if not HAS_XXHASH:
        return 0, []
    
    def worker(filepath: Path) -> float:
        data = read_file(filepath)
        if not data:
            return 0
        start = time.perf_counter()
        xxhash.xxh64_digest(data)
        return (time.perf_counter() - start) * 1e6
    
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        latencies = list(executor.map(worker, [f for f, _ in files]))
    total_time = time.perf_counter() - start
    
    return total_time, latencies


def main():
    if len(sys.argv) < 2:
        print("Usage: python benchmark_hybrid_parallelism.py <directory>")
        sys.exit(1)
    
    directory = Path(sys.argv[1])
    if not directory.exists():
        print(f"Error: Directory does not exist: {directory}")
        sys.exit(1)
    
    print(f"Scanning directory: {directory}")
    files = get_files(directory)
    print(f"Found {len(files)} files")
    
    total_size = sum(size for _, size in files)
    print(f"Total size: {total_size / 1e6:.2f} MB")
    print(f"Average file size: {total_size / len(files) / 1024:.2f} KB")
    print(f"CPU cores: {cpu_count()}")
    
    num_threads = cpu_count()
    print(f"Thread count (Python & Rust): {num_threads}")
    
    # Configure rayon threads
    if HAS_RUST:
        try:
            set_rayon_threads(num_threads)
            print(f"Rayon threads configured: {get_rayon_threads()}")
        except:
            pass
    print()
    
    if not HAS_RUST or not HAS_XXHASH:
        print("Error: Both libraries required")
        sys.exit(1)
    
    print("=" * 100)
    print("Hybrid Parallelism Comparison")
    print("=" * 100)
    
    # Benchmark 1: Python threading + Rust (individual calls)
    print("\n1. Python Threading + Rust (individual calls, reads in parallel)")
    python_time, python_latencies = benchmark_python_threading_rust(files, num_threads=cpu_count())
    print(f"   Total time: {python_time:.3f}s")
    if python_latencies:
        print(f"   Avg latency: {sum(python_latencies)/len(python_latencies):.2f}μs")
    print(f"   Throughput: {total_size / python_time / 1e6:.2f} MB/s")
    
    # Benchmark 2: Rust native parallelism (batch, reads sequentially)
    print("\n2. Rust Rayon Parallelism (batch processing, reads sequentially)")
    rust_time, rust_latencies = benchmark_rust_parallel_batch(files)
    print(f"   Total time: {rust_time:.3f}s")
    if rust_latencies:
        print(f"   Avg latency: {sum(rust_latencies)/len(rust_latencies):.2f}μs")
    print(f"   Throughput: {total_size / rust_time / 1e6:.2f} MB/s")
    
    # Benchmark 3: Hybrid - Python threading for I/O + Rust parallelism
    print("\n3. Hybrid: Python threads (I/O) + Rust Rayon (processing)")
    hybrid_time, hybrid_latencies = benchmark_rust_parallel_batch_with_reading(files, num_threads=cpu_count())
    print(f"   Processing time: {hybrid_time:.3f}s")
    if hybrid_latencies:
        print(f"   Avg latency: {sum(hybrid_latencies)/len(hybrid_latencies):.2f}μs")
    print(f"   Throughput: {total_size / hybrid_time / 1e6:.2f} MB/s")
    
    # Benchmark 4: Python threading + C
    print("\n4. Python Threading + C (individual calls)")
    c_time, c_latencies = benchmark_c_threading(files, num_threads=cpu_count())
    print(f"   Total time: {c_time:.3f}s")
    if c_latencies:
        print(f"   Avg latency: {sum(c_latencies)/len(c_latencies):.2f}μs")
    print(f"   Throughput: {total_size / c_time / 1e6:.2f} MB/s")
    
    # Summary
    print("\n" + "=" * 100)
    print("Performance Summary")
    print("=" * 100)
    print(f"{'Method':<45} {'Time (s)':<15} {'Throughput (MB/s)':<20} {'vs Python+Rust'}")
    print("-" * 100)
    print(f"{'Python Threads + Rust (individual)':<45} {python_time:<15.3f} {total_size/python_time/1e6:<20.2f} {'baseline'}")
    print(f"{'Rust Rayon (batch, seq I/O)':<45} {rust_time:<15.3f} {total_size/rust_time/1e6:<20.2f} {python_time/rust_time:.2f}x")
    print(f"{'Hybrid: Py Threads + Rust Rayon':<45} {hybrid_time:<15.3f} {total_size/hybrid_time/1e6:<20.2f} {python_time/hybrid_time:.2f}x")
    print(f"{'Python Threads + C (individual)':<45} {c_time:<15.3f} {total_size/c_time/1e6:<20.2f} {python_time/c_time:.2f}x")
    
    # Analysis
    print("\nAnalysis:")
    fastest_time = min(python_time, rust_time, hybrid_time, c_time)
    if hybrid_time == fastest_time:
        print(f"✅ Hybrid approach (Py I/O + Rust Rayon) is best at {fastest_time:.3f}s")
    elif python_time == fastest_time:
        print(f"✅ Python threading + Rust is best at {fastest_time:.3f}s")
    elif c_time == fastest_time:
        print(f"✅ Python threading + C is best at {fastest_time:.3f}s")
    else:
        print(f"✅ Rust Rayon batch is best at {fastest_time:.3f}s")
    

if __name__ == "__main__":
    main()

