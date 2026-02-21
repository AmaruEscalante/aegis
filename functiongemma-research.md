# FunctionGemma Research

## What It Is

FunctionGemma is a **270M parameter** model by Google, built on Gemma 3 architecture, purpose-built for **function calling / tool use**. It's not a general-purpose LLM — it's a specialist.

## Capabilities

- **Tiny footprint**: Runs at full precision on **550MB RAM (CPU)**. ~50 tokens/sec on Pixel 8 / iPhone 15 Pro
- **Multi-turn tool calling**: Can handle extended conversations with multiple function calls across turns
- **Chain-of-thought reasoning**: Generates thinking blocks before deciding which function to call
- **Structured I/O**: Takes function declarations as input, outputs structured tool calls
- **Built-in function types**: Calendar events, reminders, timers, weather queries, date retrieval, math operations
- **32K context window**
- **Fine-tunable**: Supports full fine-tuning and LoRA via Unsloth/Colab notebooks

## Limitations

1. **Not general-purpose** — It only does function calling. No chat, no summarization, no code generation. It's a router, not a thinker.
2. **Requires fine-tuning** — Google explicitly says it's "intended to be fine-tuned" for your specific functions. Out of the box, it only knows its built-in demo functions.
3. **Text-only** — No vision, no audio, no multimodal capabilities despite being based on Gemma 3.
4. **Small model trade-offs** — At 270M params, it will struggle with complex reasoning or ambiguous user intents compared to larger models.
5. **Rigid prompt format** — Expects a specific system prompt structure (`"You are a model that can do function calling with the following functions"`). Deviating from this format degrades performance.
6. **Limited out-of-distribution generalization** — If a user request doesn't map cleanly to a declared function, it's likely to hallucinate a call or fail silently.

## When To Use It

| Good fit | Bad fit |
|---|---|
| On-device / edge deployment | Cloud-first apps with budget for large models |
| Privacy-sensitive apps (offline) | Tasks requiring general reasoning |
| Mobile assistants with fixed tool sets | Open-ended tool discovery |
| Resource-constrained environments | Complex multi-step planning |

## Privacy-Sensitive App Examples

### Personal Health & Wellness
- **Medication reminder apps** — "Set a reminder to take my blood pressure meds at 8am" (processes health data locally, never hits a server)
- **Symptom trackers** — "Log that I had a migraine today at 3pm" (medical data stays on device)
- **Fertility/cycle tracking** — scheduling and logging without cloud sync

### Financial & Banking
- **Personal budgeting assistants** — "Add $45 grocery expense to today" (spending habits never leave the phone)
- **Local payment scheduling** — "Remind me to pay rent on the 1st"
- **Expense categorization** — classifying transactions on-device

### Communication & Contacts
- **Smart dialer / contact lookup** — "Call my dentist" → maps to a contact lookup function
- **Local SMS scheduling** — "Text Mom happy birthday tomorrow at 9am"
- **On-device email triage** — sorting/flagging without sending content to a cloud LLM

### Kids & Family
- **Parental control assistants** — "Block YouTube after 8pm" → maps to device restriction APIs
- **Children's educational apps** — voice-driven math/spelling tools that don't transmit child data
- **Family calendar management** — offline scheduling for minors' activities (COPPA compliance)

### Enterprise / Workplace
- **Offline field worker tools** — technicians in secure facilities querying local manuals ("What's the torque spec for valve B7?")
- **Legal document assistants** — lawyers triggering local search/retrieval over privileged documents
- **Healthcare kiosks** — patient check-in devices that route voice commands to local APIs without cloud processing

### Smart Home / IoT
- **Local home automation** — "Turn off the lights and lock the door" → function calls to local smart home APIs, no cloud relay
- **Voice assistants without cloud dependency** — privacy-first alternative to Alexa/Google Home for basic commands

### The Common Thread

In all these cases, the key pattern is:
1. **Sensitive user data** (health, financial, children's, legal) is involved
2. The user intent maps to a **fixed, well-defined set of functions**
3. Processing must happen **on-device** to avoid regulatory risk (HIPAA, GDPR, COPPA) or user trust concerns
4. The model only needs to **route intent → function call**, not generate free-form text

That's exactly FunctionGemma's sweet spot — a tiny on-device router that keeps private data private.
