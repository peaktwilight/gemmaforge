---
title: GemmaForge
emoji: 🔥
colorFrom: red
colorTo: yellow
sdk: gradio
sdk_version: 4.44.1
python_version: "3.12"
app_file: app.py
pinned: true
license: apache-2.0
short_description: Real-time vulnerability detection inside Gemma 4
suggested_hardware: zero-a10g
---

# GemmaForge

A linear probe trained on Gemma 4's hidden states. Watch each generated token coloured by how much the model's internal activations look like a known vulnerability pattern. Detection happens **inside the model**, in real time, before the code is finished.

Built for the Gemma 4 Good Hackathon by [Doruk Tan Ozturk](https://doruk.ch) (security researcher, 4 published CVEs) and Mehmet Efe Akça (MSc Data Science @ ETH Zürich, interpretability research).

[GitHub repo](https://github.com/peaktwilight/gemmaforge) · [Writeup](https://kaggle.com/competitions/gemma-4-good-hackathon)
