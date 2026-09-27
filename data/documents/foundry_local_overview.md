# Microsoft Foundry Local

Foundry Local is Microsoft's runtime for running language models directly on a
user's own device, instead of calling a cloud API. It ships a local service
plus a small SDK: an application asks the SDK for a model by alias (for
example, a compact chat model or an embedding model), Foundry Local downloads
an optimized version of that model on first use, caches it locally, and then
serves inference over CPU, GPU, or NPU acceleration depending on what
hardware is available.

Because everything runs on-device, an application built on Foundry Local can
work with zero outbound network calls once the model has been downloaded.
That matters for offline scenarios, for handling sensitive documents that
should never leave a machine, and for avoiding per-token cloud costs during
development.

## How applications talk to it

Foundry Local exposes an OpenAI-compatible chat and embeddings endpoint on
localhost. In practice this means an application can use the same client
library it would use for a cloud provider - just pointed at the local
endpoint address that the Foundry Local SDK reports - and call familiar
methods such as creating a chat completion or an embedding. This makes it
straightforward to write code that can fall back between a local model and a
cloud model with minimal changes.

## Model catalog and aliases

Models are referred to by short aliases rather than long file paths. Running
a model by alias lets Foundry Local pick the build that best matches the
current machine's hardware (for example, a version accelerated for an
available NPU) without the application needing to know the details. Typical
aliases used in small local projects include compact instruction-tuned chat
models in the few-billion-parameter range and small dedicated embedding
models, both chosen to keep memory use and response latency low enough for a
laptop.
