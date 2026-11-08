---
title: kcbert-profanity
colorFrom: gray
colorTo: red
sdk: static
app_file: index.html
pinned: false
license: cc-by-nc-4.0
models:
- illimax/kcbert-profanity
short_description: Korean offensive text classifier
---

# kcbert-profanity demo

Type a Korean sentence and the model tells you whether it is clean or offensive.

Model card: [illimax/kcbert-profanity](https://huggingface.co/illimax/kcbert-profanity)

The model runs in your browser with transformers.js, using the 8-bit quantized ONNX weights (about 110MB, downloaded once).
Your text is not sent to a server.

"Offensive" here includes swear words, insults, and hate speech.
Input is cut at 128 tokens.
