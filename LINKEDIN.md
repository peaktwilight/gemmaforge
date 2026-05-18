Last month I disclosed CVE-2026-33896 in node-forge, a certificate-forgery bug sitting in a package with 33M weekly downloads.

The whole time I kept thinking: if a human reviewer almost missed this, what chance does an LLM have when it cheerfully writes the same pattern at 80 tokens per second?

So for the Gemma 4 Good Hackathon, Mehmet Efe Akça (interpretability researcher at ETH Zürich) and I built GemmaForge.

GemmaForge watches Gemma 4's hidden states and flags vulnerable code mid-generation, before the first risky token is final. Not a post-hoc linter, not a second model rubber-stamping the first. It is a probe sitting inside the activations, calling the risk while the sentence is still being written.

Runs 100% locally on a single GPU. Apache-2.0. No telemetry, no API key, no "trust us".

We think the right place to catch insecure code is the same place the model decided to write it. Submission is up (link in comments).

Would you trust an AI to write code for you if it could honestly flag its own risky lines as it typed them?

#Gemma #GoogleDeepMind #LLMSecurity #Interpretability #ETHZurich
