A few months ago I disclosed CVE-2026-33896 in node-forge, a certificate-forgery bug in a package with 33 million weekly downloads. The whole time I kept thinking: if a human reviewer almost missed this, what chance does an LLM have when it cheerfully writes the same pattern at 80 tokens per second?

So for the Gemma 4 Good Hackathon, Mehmet Efe Akça (interpretability research, ETH Zürich) and I built GemmaForge.

GemmaForge watches Gemma 4's hidden states and flags vulnerable code mid-generation, before the first risky token is final. Not a post-hoc linter, not a second model rubber-stamping the first. It is a probe sitting inside the activations, calling the risk while the sentence is still being written.

Headline numbers on Gemma 4 E2B:
- AUC 0.963 in-distribution, 0.907 cross-language (Python to JavaScript)
- 5-CWE multi-head probe, macro-AUC 0.9726
- A LoRA fine-tune on the side that measurably reduces vulnerable-pattern emission on the demo prompts

Roughly 1,500 weights doing the work. Runs 100% locally on a single laptop GPU. Apache-2.0. No telemetry, no API key, no "trust us".

Would you trust an AI to write code for you if it could honestly flag its own risky lines as it typed them?

(Submission link in comments.)

#Gemma #GoogleDeepMind #LLMSecurity #Interpretability #ETHZurich
