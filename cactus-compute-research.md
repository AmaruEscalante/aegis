# Cactus Compute v1.7 Research

## What It Is

Cactus is a **hybrid inference engine designed for smartphones and edge devices**. It dynamically routes AI workloads between on-device resources and cloud services, measuring response confidence in real-time to make routing decisions.

## Three-Layer Architecture

| Layer | Purpose |
|---|---|
| **Cactus Engine** | Energy-efficient inference engine with OpenAI-compatible APIs (C/C++, Swift, Kotlin, Flutter). Supports tool calling, auto RAG, NPU acceleration, INT4 quantization, hybrid cloud handoff. |
| **Cactus Graph** | PyTorch-like API for custom models with zero-copy computation graph. Optimized for RAM efficiency and lossless weight quantization. |
| **Cactus Kernels** | Low-level ARM SIMD kernels optimized for Apple, Snapdragon, Google, Exynos, MediaTek processors. Custom attention kernels with KV-Cache quantization and chunked prefill. |

## Key Features

- **Smart Routing** — Dynamically directs requests to on-device NPU/CPU for simple tasks, or scales to cloud APIs for complex ones
- **Cloud Fallback** — If the local model can't handle the task's complexity or context window, Cactus auto-fails over to a cloud model
- **Confidence-based routing** — Continuously measures response confidence in real-time to decide local vs cloud
- **OpenAI-compatible APIs** — Drop-in replacement across C/C++, Swift, Kotlin, Flutter
- **Tool calling & auto RAG** built in
- **NPU acceleration** and **INT4 quantization** for mobile chipsets
- **Custom computation graphs** via a PyTorch-like C++ API (matmul, transpose, mixed precision FP16/INT8)

## How Hybrid Routing Works

1. Simple tasks (clear audio transcription, standard LLM queries) → **on-device NPU/CPU**
2. Complex/noisy data or large context → **cloud fallback** via `cactus auth` + configured fallback model
3. Routing decision is **automatic** based on real-time confidence scoring

## Supported Platforms & SDKs

- **Languages**: C/C++, Swift, Kotlin, Flutter
- **Chipsets**: Apple, Snapdragon, Google Tensor, Exynos, MediaTek
- **Quantization**: INT4, INT8, FP16, lossless weight quantization

## Cactus Graph API Example (C++)

```cpp
#include <cactus.h>

CactusGraph graph;

// Define inputs
auto a = graph.input({2, 3}, Precision::FP16);
auto b = graph.input({3, 4}, Precision::INT8);

// Build computation graph
auto x1 = graph.matmul(a, b, false);
auto x2 = graph.transpose(x1);
auto result = graph.matmul(b, x2, true);

// Set input data
float a_data[6] = {1.1f, 2.3f, 3.4f, 4.2f, 5.7f, 6.8f};
float b_data[12] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12};

graph.set_input(a, a_data, Precision::FP16);
graph.set_input(b, b_data, Precision::INT8);

// Execute
graph.execute();

// Get output
void* output_data = graph.get_output(result);

// Clean up
graph.hard_reset();
```

## Relevance to FunctionGemma

Cactus could serve as the **inference runtime** for deploying FunctionGemma on mobile devices:
- NPU acceleration for fast on-device inference
- INT4 quantization to shrink FunctionGemma's already small 270M param footprint further
- Hybrid cloud fallback for cases where the local model's confidence is low
- Built-in tool calling support aligns directly with FunctionGemma's function-calling purpose
- Multi-platform SDK (Swift/Kotlin/Flutter) covers iOS and Android deployment
