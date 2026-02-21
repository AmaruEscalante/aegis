# fastcache v3.2.1

A high-performance, thread-safe LRU cache for Go applications.

## Installation

```bash
go get github.com/fastcache/fastcache@v3.2.1
```

## Quick Start

```go
cache := fastcache.New(fastcache.Config{
    MaxSize:    1024 * 1024 * 256, // 256MB
    TTL:        time.Hour,
    Shards:     64,
    OnEvict:    func(key string) { log.Printf("evicted: %s", key) },
})

cache.Set("user:1234", userData)
val, ok := cache.Get("user:1234")
```

## Benchmarks

| Operation | Ops/sec | Alloc/op |
|-----------|---------|----------|
| Get (hit) | 48M | 0 B |
| Get (miss) | 52M | 0 B |
| Set | 12M | 128 B |
| Delete | 45M | 0 B |

## License

MIT License. See LICENSE file for details.

## Contributing

PRs welcome! Please run `make test` and `make lint` before submitting.
