---
language:
- ko
license: cc-by-nc-4.0
library_name: transformers
pipeline_tag: text-classification
base_model: beomi/kcbert-base
datasets:
- smilegate-ai/kor_unsmile
tags:
- korean
- bert
- kcbert
- profanity
- hate-speech
- toxicity
metrics:
- accuracy
- f1
model-index:
- name: kcbert-profanity
  results:
  - task:
      type: text-classification
      name: Text Classification
    dataset:
      name: Korean UnSmile
      type: smilegate-ai/kor_unsmile
      split: valid
    metrics:
    - type: accuracy
      value: 0.8764
      name: Accuracy
    - type: f1
      value: 0.9184
      name: F1
---

# kcbert-profanity

A binary classifier for offensive Korean text.
Given a sentence, it predicts whether the sentence is clean (0) or offensive (1).

I fine-tuned [beomi/kcbert-base](https://huggingface.co/beomi/kcbert-base) on the [Korean UnSmile dataset](https://huggingface.co/datasets/smilegate-ai/kor_unsmile).
I use it as the detection step in my Discord bot, [profanity-cleaner](https://github.com/lkw-k/profanity-cleaner).
Masking and rewriting in the bot are done by a separate LLM, not by this model.

## Labels

| ID | Output | Meaning |
|---|---|---|
| 0 | `LABEL_0` | clean |
| 1 | `LABEL_1` | offensive (swear words, insults, hate speech) |

`id2label` is not set in the config, so the output is `LABEL_0` / `LABEL_1`.

Korean UnSmile is a multi-label dataset with 10 labels.
I only used the `clean` column and flipped it (`label = 1 - clean`).
As a result, label 1 covers all 9 non-clean categories:

| Category | Meaning |
|---|---|
| 여성/가족 | women / family |
| 남성 | men |
| 성소수자 | sexual minorities |
| 인종/국적 | race / nationality |
| 연령 | age |
| 지역 | region |
| 종교 | religion |
| 기타 혐오 | other hate |
| 악플/욕설 | malicious comments / swear words |

Hate speech without any swear words is also labeled 1.

## Usage

```python
from transformers import pipeline

classifier = pipeline("text-classification", model="illimax/kcbert-profanity")
names = {"LABEL_0": "clean", "LABEL_1": "offensive"}

for text in ["오늘 날씨 정말 좋다", "아 시발 진짜 짜증나네"]:
    out = classifier(text, truncation=True, max_length=128)[0]
    print(text, names[out["label"]], round(out["score"], 4))
```

```python
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_id = "illimax/kcbert-profanity"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForSequenceClassification.from_pretrained(model_id).eval()

inputs = tokenizer("아 시발 진짜 짜증나네", return_tensors="pt", truncation=True, max_length=128)
with torch.no_grad():
    probs = model(**inputs).logits.softmax(-1)[0]

print(probs)  # [clean, offensive]
```

Keep `max_length` at 128. The model was trained with 128 tokens, and inputs over 300 tokens will raise an error (`max_position_embeddings = 300`).

## Training data

Korean UnSmile: comments from Korean news sites and online communities, labeled by hand.

| Split | Sentences |
|---|---|
| train | 15,005 |
| valid | 3,737 |

The train split is imbalanced: 11,266 offensive (75.1%) and 3,739 clean (24.9%).
I did not add other data, and the only preprocessing was tokenization.

## Training

| | |
|---|---|
| Base model | beomi/kcbert-base (BERT-base, 12 layers, about 110M parameters) |
| Max length | 128 |
| Epochs | 3 |
| Batch size | 16 (train) / 32 (eval) |
| Learning rate | 2e-5 |
| Warmup ratio | 0.1 |
| Weight decay | 0.01 |
| Precision | fp16 |
| Steps | 2,814 |
| Checkpoint selection | best F1 on valid, checked every epoch |

## Results

Evaluated on the valid split (3,737 sentences). F1 is computed for label 1.

| Epoch | Train loss | Valid loss | Accuracy | F1 |
|---|---|---|---|---|
| 1 | 0.315 | 0.306 | 0.8614 | 0.9107 |
| 2 | 0.195 | 0.371 | 0.8721 | 0.9184 |
| 3 | 0.088 | 0.548 | 0.8764 | 0.9184 |

The uploaded weights are from epoch 3.

There is no separate test set. The valid split was also used to pick the checkpoint, so these numbers may be slightly optimistic.
Valid loss rises after epoch 1 while accuracy and F1 barely change, so the model is starting to overfit.
Since label 1 is the majority class, F1 looks higher than accuracy. I did not measure precision, recall, or per-class scores.

## Limitations

- The training set is small (about 15,000 sentences), so misclassification is expected, especially on sentences unlike the training data.
- Label 1 mixes swear words, insults, and hate speech. The model does not tell you which one it found.
- It looks at one sentence at a time, without conversation context.
- 75% of the training data is offensive, so expect some false positives on slang, jokes between friends, or strongly worded opinions.
- The data comes from news comments and community posts. Game chat, formal writing, and very short messages may work worse.
- Swear words written in unusual ways (spaces in the middle, symbols, consonants only like ㅅㅂ) can be missed if they did not appear in training.
- Korean only. English swear words such as "fuck" or "shit" are not detected.
- Anything after 128 tokens was cut off during training.

Do not use this model alone to ban or punish users. Have a person check the results.

## License

CC BY-NC 4.0. Non-commercial use only.

The base model (beomi/kcbert-base) is Apache 2.0, but the training data (Korean UnSmile) is CC BY-NC-ND 4.0, which does not allow commercial use.
For commercial use of the dataset, contact Smilegate AI (smilegate_ai@smilegate.com).

## Citation

```bibtex
@misc{lee2020kcbert,
  author = {Junbum Lee},
  title = {KcBERT: Korean Comments BERT},
  year = {2020},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/Beomi/KcBERT}}
}

@misc{SmilegateAI2022KoreanUnSmileDataset,
  title = {Korean UnSmile dataset: Human-annotated Multi-label Korean Hate Speech Dataset},
  author = {Seonghyun Kim},
  year = {2022},
  howpublished = {\url{https://github.com/smilegate-ai/korean_unsmile_dataset}}
}

@misc{kang2022korean,
  title = {Korean Online Hate Speech Dataset for Multilabel Classification: How Can Social Science Improve Dataset on Hate Speech?},
  author = {TaeYoung Kang and Eunrang Kwon and Junbum Lee and Youngeun Nam and Junmo Song and JeongKyu Suh},
  year = {2022},
  eprint = {2204.03262},
  archivePrefix = {arXiv},
  primaryClass = {cs.CL}
}
```
