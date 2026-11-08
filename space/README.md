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

# kcbert-profanity

Type a Korean sentence and the model tells you whether it is clean or offensive.

Model card: [illimax/kcbert-profanity](https://huggingface.co/illimax/kcbert-profanity)

The model runs in your browser with transformers.js, using the 8-bit quantized ONNX weights (about 110MB, downloaded once).
Your text is not sent to a server.

The model was trained on only about 15,000 sentences, so it can make mistakes.
It works for Korean only and does not detect English swear words.

"Offensive" here includes swear words, insults, and hate speech.
Input is cut at 128 tokens.
