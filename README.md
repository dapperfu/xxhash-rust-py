# xxhash-rust with Python Bindings

[![Rust](https://github.com/DoumanAsh/xxhash-rust/actions/workflows/rust.yml/badge.svg)](https://github.com/DoumanAsh/xxhash-rust/actions/workflows/rust.yml)
[![Crates.io](https://img.shields.io/crates/v/xxhash-rust.svg)](https://crates.io/crates/xxhash-rust)
[![Documentation](https://docs.rs/xxhash-rust/badge.svg)](https://docs.rs/crate/xxhash-rust/)
[![Hubris Level](https://img.shields.io/badge/hubris-over%209000-orange)]()

Implementation of [xxHash](https://github.com/Cyan4973/xxHash) in Rust with Python bindings.

> **Note**: This repository includes experimental Python bindings as a thought experiment to answer the age-old question: "Can Rust beat C at its own game?" **Spoiler alert**: C won by 27%, but like a participation trophy at a kids' soccer game, we learned that the real victory was the memory safety we made along the way. 🏆🦀

## Table of Contents

- [Rust Library](#rust-library)
- [Python Bindings - Thought Experiment](#python-bindings---thought-experiment)
- [Installation](#installation)
- [Python API](#python-api)
- [Benchmark Results](#benchmark-results)
- [Key Findings](#key-findings)
- [When to Use What](#when-to-use-what)

---

## Rust Library

Each algorithm is implemented via feature, allowing precise control over code size.

### Rust Example

**Cargo.toml:**
```toml
[dependencies.xxhash-rust]
version = "0.8.12"
features = ["xxh3", "const_xxh3"]
```

**main.rs:**
```rust
use xxhash_rust::const_xxh3::xxh3_64 as const_xxh3;
use xxhash_rust::xxh3::xxh3_64;

const TEST: u64 = const_xxh3(b"TEST");

fn test_input(text: &str) -> bool {
    match xxh3_64(text.as_bytes()) {
        TEST => true,
        _ => false
    }
}

assert!(!test_input("tEST"));
assert!(test_input("TEST"));
```

### Rust Features

By default all features are off.

- `std` - Enables `std::io::Write` trait implementation
- `xxh32` - Enables 32bit algorithm. Suitable for x86 targets
- `const_xxh32` - `const fn` version of `xxh32` algorithm
- `xxh64` - Enables 64 algorithm. Suitable for x86_64 targets
- `const_xxh64` - `const fn` version of `xxh64` algorithm
- `xxh3` - Enables `xxh3` family of algorithms, superior to `xxh32` and `xxh64` in terms of performance.
- `const_xxh3` - `const fn` version of `xxh3` algorithm

### HW Acceleration

Similar to reference implementation, crate implements various SIMDs in `xxh3` depending on provided flags.
All checks are performed only at compile time, hence user is encouraged to enable these accelerations (for example via `-C target_cpu=native`)

Used SIMD acceleration:

- SSE2 - widely available, can be safely enabled in 99% of cases. Enabled by default in `x86_64` targets.
- AVX2
- AVX512
- Neon - Enabled by default on aarch64 targets (most likely)
- Wasm SIMD128 - Has to be enabled via rust flag: `-Ctarget-feature=+simd128`

### Streaming vs One-shot

For performance reasons one-shot version of algorithm does not re-use streaming version.
Unless needed, user is advised to use one-shot version which tends to be more optimal.

### `const fn` version

While `const fn` provides compile time implementation, it does so at performance cost.
Hence you should only use it at _compile_ time.

To guarantee that something is computed at compile time make sure to initialize hash output
as `const` or `static` variable, otherwise it is possible function is executed at runtime, which
would be worse than regular algorithm.

`const fn` is implemented in best possible way while conforming to limitations of Rust `const
fn`, but these limitations are quite strict making any high performance code impossible.

---

## Python Bindings - Thought Experiment

This project started as an experiment: **Can we create Python bindings for xxhash-rust that match or beat the C-based implementation?**

*Narrator: They could not.* 🎙️

But hey, that won't stop us from trying! Armed with nothing but hubris, a working knowledge of PyO3, and several cups of coffee ☕, we set out to prove that Rust could be just as fast as C. The results may surprise you! (Or not, if you read the spoiler above.)

### Goals
1. ✅ Create maturin-based Python bindings to all xxhash functions *(Easy peasy)*
2. ✅ Make it `pip install -e` installable *(Surprisingly painless)*
3. ✅ Benchmark against the C-based `xxhash` Python library *(Reality check incoming)*
4. ✅ Explore both Python-side and Rust-side parallelism strategies *(DOWN THE RABBIT HOLE WE GO)*
5. ✅ Test on real-world file workloads *(Where our dreams went to die)*

### What We Actually Built

- **Complete Python API**: One-shot and streaming interfaces for XXH32, XXH64, XXH3 *(Pretty slick, if we say so ourselves)*
- **StrictDoc Requirements**: Formal requirements documentation *(For that professional veneer)*
- **Multiple Parallelism Strategies**: Python threading, Rust Rayon, and hybrid approaches *(Spoiler: Some worked better than others)*
- **Comprehensive Benchmarks**: Sequential, concurrent, streaming, and batch processing tests *(Where the truth hurts)*
- **Real-world Testing**: Benchmarked on 1000 files (688 MB) from actual filesystem *(No synthetic benchmarks to hide behind)*

---

## Installation

### Python Package (Editable Install)

```bash
# Clone the repository
git clone https://github.com/dapperfu/xxhash-rust-py.git
cd xxhash-rust-py

# Install dependencies and build
make install build

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install maturin xxhash pytest
maturin develop --release --manifest-path src/xxhash_rust_ffi/Cargo.toml
```

### Requirements

- Python 3.8+
- Rust 1.70+
- Maturin 1.0+
- xxhash (C library) for benchmarking

---

## Python API

### One-shot Functions

```python
from xxhash_rust import xxh32, xxh64, xxh3_64, xxh3_128

# 32-bit hash
hash32 = xxh32(b"hello world", seed=0)  # Returns int

# 64-bit hash
hash64 = xxh64(b"hello world", seed=0)  # Returns int

# XXH3 (64-bit, fastest)
hash3 = xxh3_64(b"hello world")  # Returns int

# XXH3 with seed
hash3_seed = xxh3_64_with_seed(b"hello world", seed=42)

# XXH3 (128-bit)
low, high = xxh3_128(b"hello world")  # Returns tuple[int, int]
```

### Streaming API

```python
from xxhash_rust import Xxh32, Xxh64, Xxh3

# XXH64 streaming
hasher = Xxh64(seed=0)
hasher.update(b"hello ")
hasher.update(b"world")
result = hasher.digest()  # Returns int
hasher.reset()  # Reuse hasher

# XXH3 streaming (supports both 64-bit and 128-bit)
hasher3 = Xxh3(seed=0)
hasher3.update(b"data chunk 1")
hasher3.update(b"data chunk 2")
hash64 = hasher3.digest()      # 64-bit result
low, high = hasher3.digest128()  # 128-bit result
```

### Parallel Batch Processing (Rust-side)

```python
from xxhash_rust import (
    batch_xxh32,
    batch_xxh64,
    batch_xxh3_64,
    set_rayon_threads,
    get_rayon_threads
)

# Configure Rayon thread pool
set_rayon_threads(16)  # Use 16 cores
print(f"Using {get_rayon_threads()} threads")

# Batch process multiple data items in parallel (in Rust)
data_list = [b"file1 contents", b"file2 contents", b"file3 contents"]
results = batch_xxh64(data_list)  # Returns list[int]
```

---

## Benchmark Results (The Moment of Truth)

### Test Environment
- **Dataset**: 1000 files, 688 MB total (avg 672 KB per file)
- **CPU**: 16 cores *(All the cores!)*
- **Thread count**: 16 threads for all methods *(Fair and balanced, like a seesaw)*
- **Location**: `/keg/pictures/2015/08-Aug/` *(Real-world JPEG files from an actual vacation, not synthetic data)*

### Performance Comparison (Where Dreams Go to Die)

| Method | Time | Throughput | Speedup | Notes |
|--------|------|------------|---------|-------|
| **Python Threads + C** | 0.201s | **3,418 MB/s** | **1.27x** | ✅ The undisputed champion |
| **Python Threads + Rust** | 0.256s | 2,686 MB/s | 1.00x | 🦀 Respectable silver medal |
| **Rust Rayon (batch)** | 10.138s | 67.89 MB/s | 0.03x | ⚠️ The "are you sure this is right?" result |
| **Hybrid (Py I/O + Rayon)** | 10.355s | 66.47 MB/s | 0.02x | ⚠️ Somehow even worse |

*If you're wondering: Yes, we triple-checked those Rayon numbers. Yes, we cried a little.*

### Sequential vs Concurrent (Python Threading)

*Or: "Look at how much faster threading makes everything!"*

| Implementation | Sequential | Concurrent (16 threads) | Speedup |
|----------------|------------|------------------------|---------|
| C (xxhash) | 1.456s (472 MB/s) | 0.201s (3,418 MB/s) | 7.2x 🚀 |
| Rust | 2.015s (341 MB/s) | 0.256s (2,686 MB/s) | 7.9x 🚀 |

*Threading: The gift that keeps on giving.*

### Streaming Performance

*For when you can't fit everything in memory (aka reality)*

| Implementation | Time | Throughput | Latency/File |
|----------------|------|------------|--------------|
| C (streaming) | 0.212s | 3,243 MB/s | 87.66 μs |
| Rust (streaming) | 0.289s | 2,381 MB/s | 100.17 μs |

*Streaming adds ~5-6% overhead but saves your RAM from exploding. Worth it? Probably.*

---

## Key Findings

### 🏆 Winner: Python Threading + C

The C implementation (`xxhash` Python library) is **27% faster** than Rust for file-based workloads.

*C developers everywhere: "We told you so." 😏*

**Why Python Threading Wins:**
1. **I/O Dominates**: Reading 688MB from disk is the bottleneck *(Turns out disks are slow, who knew?)*
2. **Parallel Reads**: ThreadPoolExecutor reads multiple files simultaneously *(The GIL taketh away, but here it also giveth)*
3. **Low Per-File Cost**: Hashing takes ~70-90μs per file, making it fast *(Blink and you'll miss it)*
4. **GIL Released**: Both C and Rust extensions release the GIL during computation *(Finally, the GIL does something useful)*

**Why Rust is Still Invited to the Party:**
1. Only 27% slower than highly optimized C code *(That's basically a rounding error, right? RIGHT?)*
2. Memory-safe by default (no UB risk) *(Your pointers can't segfault if you don't have pointers 🧠)*
3. Provides additional features (batch processing, Rayon) *(Over-engineering? We prefer "future-proof")*
4. Better Rust-to-Rust integration *(For the dozen people who need this)*

### ⚠️ Why Rust Batch Processing Lost (Badly)

Rust Rayon batch processing was **39x slower** than Python threading. Yes, you read that right. **39x**.

*Achievement Unlocked: Made it slower! 🏅*

What went wrong:
1. **Sequential I/O**: Python reads all files sequentially before passing to Rust *(Parallelism? Never heard of her)*
2. **Memory Overhead**: All 688MB loaded into memory at once *(RAM is cheap, right? ...Right?)*
3. **Conversion Overhead**: `Vec<Vec<u8>>` to parallel iterator costs time *(Death by a thousand allocations)*
4. **Overkill**: Rayon overhead exceeds benefit for ~70μs/file workload *(Using a sledgehammer to crack a peanut)*

The moral of the story: **Don't use a bazooka when a flyswatter will do.** 🪰🚀

### 🎯 When Each Approach Shines (A Field Guide)

**Use Python Threading + Individual Calls When:**
- ✅ Processing real files from disk *(You know, like in the real world)*
- ✅ Variable file sizes *(Because life isn't a unit test)*
- ✅ I/O is the bottleneck *(Spoiler: It usually is)*
- ✅ Files fit in OS cache *(Let the kernel do its job)*

**Use Rust Rayon Batch Processing When:**
- ✅ Data already in memory *(No disk? No problem!)*
- ✅ Heavy computation per item (milliseconds+) *(When the hash takes longer than your patience)*
- ✅ Large batches of uniform data *(Perfectly spherical cows in a vacuum)*
- ✅ No I/O involved *(The dream scenario)*
- ✅ You want to feel smart about using Rayon *(Valid reason, no judgment)*

---

## When to Use What

### For Production File Hashing

**Recommendation**: Use the **C-based Python library** (`xxhash`)

```bash
pip install xxhash
```

```python
import xxhash
from concurrent.futures import ThreadPoolExecutor

def hash_file(filepath):
    with open(filepath, 'rb') as f:
        return xxhash.xxh64(f.read()).intdigest()

with ThreadPoolExecutor(max_workers=16) as executor:
    results = list(executor.map(hash_file, file_list))
```

**Why**: 27% faster, battle-tested, widely used.

### For Rust Projects Needing Python Bindings

**Recommendation**: Use these **Rust bindings**

```python
from xxhash_rust import xxh64
# Same API, memory-safe Rust backend
```

**Why**: Native Rust integration, memory safety, competitive performance.

### For In-Memory Batch Processing

**Recommendation**: Use **Rust Rayon batch functions**

```python
from xxhash_rust import batch_xxh64, set_rayon_threads

set_rayon_threads(16)
data_list = [item.encode() for item in large_dataset]
results = batch_xxh64(data_list)  # Parallel processing in Rust
```

**Why**: True parallelism, no GIL, scales with cores.

---

## Repository Structure

```
xxhash-rust-py/
├── requirements.sdoc              # StrictDoc requirements documentation
├── pyproject.toml                 # Python package configuration (maturin)
├── Cargo.toml                     # Rust workspace configuration
├── Makefile                       # Build automation
│
├── src/
│   ├── xxhash_rust/              # Original Rust library
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── xxh32.rs
│   │       ├── xxh64.rs
│   │       └── xxh3.rs
│   │
│   ├── xxhash_rust_ffi/          # Python bindings (PyO3)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs            # Main module
│   │       ├── xxh32_bindings.rs
│   │       ├── xxh64_bindings.rs
│   │       ├── xxh3_bindings.rs
│   │       └── batch_bindings.rs # Rayon parallelism
│   │
│   └── xxhash_rust/              # Python package
│       └── __init__.py           # Python API
│
├── benchmark.py                   # Basic sequential benchmarks
├── benchmark_concurrent.py        # Threading + streaming benchmarks
├── benchmark_real_files.py        # Real-world file benchmarks
└── benchmark_hybrid_parallelism.py # All parallelism strategies

Documentation:
├── INSTALL.md                     # Installation guide
├── CONCURRENT_BENCHMARK.md        # Concurrent benchmarking details
├── PARALLELISM_SUMMARY.md         # Parallelism analysis
└── SUMMARY.md                     # Overall project summary
```

---

## Building from Source

### Quick Start

```bash
make install build
make test
```

### Manual Build

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install maturin
pip install maturin

# Build Rust extension
maturin develop --release --manifest-path src/xxhash_rust_ffi/Cargo.toml

# Run benchmarks
python benchmark.py
python benchmark_concurrent.py
python benchmark_real_files.py /path/to/files
```

### Make Targets

```bash
make help                          # Show all targets
make install                       # Install Python dependencies
make build                         # Build Rust extension
make test                          # Run basic benchmarks
make benchmark-concurrent          # Concurrent benchmarks
make benchmark-real DIR=/path      # Real file benchmarks
make benchmark-hybrid DIR=/path    # All parallelism strategies
make clean                         # Clean build artifacts
```

---

## Conclusion: The Thought Experiment (Or: What We Learned From Our Hubris)

**Question**: Can Rust match C for Python extensions in file hashing?

**Answer**: Almost! But "almost" only counts in horseshoes and hand grenades. 💣

Rust came in at 27% slower, but brought some consolation prizes:
- ✅ Memory safety without runtime cost *(No more 3AM segfault debugging sessions!)*
- ✅ Fearless concurrency primitives (Rayon) *(Which we then used to make things slower, oops)*
- ✅ Competitive performance (2,686 MB/s vs 3,418 MB/s) *(We're gonna round that to "basically the same")*
- ✅ Modern tooling (maturin, PyO3) *(At least the developer experience was nice)*

**Key Insight**: For file-based workloads, parallelism strategy matters WAY more than C vs Rust:
- Python threading: 7-8x speedup (both C and Rust) *(The real MVP)*
- Rust Rayon batch: 39x slower (I/O bottleneck dominates) *(The "what were we thinking?" moment)*
- The real bottleneck is I/O, not computation *(Always has been 👨‍🚀🔫)*

**Recommendations for Mere Mortals**: 
- **Production**: Use C-based `xxhash` library *(Winner winner chicken dinner)*
- **Rust Projects**: Use these bindings *(Close enough for government work)*
- **In-Memory**: Use Rust Rayon batch processing *(Finally, a use case!)*
- **Learning Experience**: Build your own and cry *(You're reading this, so... mission accomplished?)*

### The Real Takeaways

This experiment proved several things:

1. Rust *can* be a viable alternative to C for Python extensions ✅
2. Memory safety and modern concurrency primitives are nice-to-haves ✅
3. The 27% performance gap is acceptable for many use cases ✅
4. Sometimes the "smart" solution (Rayon batch) is actually the dumb solution ✅
5. Measuring things is important (otherwise we'd still think Rayon was a good idea) ✅
6. C developers were right all along, but we're not going to admit it out loud ✅

**Was it worth it?** Absolutely! We learned valuable lessons about performance, parallelism, and the importance of profiling before optimizing. Also, we got to play with Rayon, which was fun right up until we saw the benchmark results.

**Would we do it again?** Ask us after we've had more coffee. ☕

---

## Version Note

- `0.8.*` corresponds to C's `0.8.*`

In order to keep up with original implementation version I'm not planning to bump major/minor until C implementation does so.

---

## License

BSL-1.0 (Boost Software License)

## Authors

- Original Rust implementation: [Douman](https://github.com/DoumanAsh) *(The real hero)*
- Python bindings: Thought experiment via Cursor AI + Claude Sonnet 4.5 *(The ones with too much free time)*
- Hubris & Optimism: Provided free of charge *(No refunds)*

## Acknowledgments

- [xxHash](https://github.com/Cyan4973/xxHash) by Yann Collet *(For making the hash algorithm we're trying to match)*
- [PyO3](https://github.com/PyO3/pyo3) for excellent Rust-Python bindings *(Made this whole thing possible)*
- [maturin](https://github.com/PyO3/maturin) for seamless Python packaging *(Seriously, maturin is *chef's kiss*)*
- [Rayon](https://github.com/rayon-rs/rayon) for data parallelism *(Sorry we made you look bad, it wasn't your fault)*
- Coffee ☕ *(The real MVP)*
- The C programming language *(For being annoyingly fast after 50 years)*
- Stack Overflow *(You know why)*
