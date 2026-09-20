# Jev field tests

Twelve small experiments against [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev),
TypeSafe's model that answers typed questions with probabilities and cannot
write text. Run them with your own API key and compare your numbers with mine.

The write-up is on [my blog](https://abhishekanand.in/blog). This repository is
the code behind it.

Python 3.10 or later. No dependencies.

## Run it

```sh
git clone https://github.com/fly2abhishek/jev-field-tests.git
cd jev-field-tests
cp .env.example .env        # then set TYPESAFE_API_KEY
python run.py list
python run.py scaling weaknesses
python run.py all
```

You can export `TYPESAFE_API_KEY` in your shell instead of using `.env`. A full
run makes about 900 Jev calls, takes about eight minutes, and cost me about two
cents. The two dataset scenarios are most of that; `--n 100` makes them smaller.

Set `GEMINI_API_KEY` as well and two scenarios add an LLM baseline:
`calibration_boolq` and `guardrail`. That adds about 430 Gemini calls. Without
it they run Jev alone.

Each scenario prints a table and writes its raw output to `runs/<name>.json`.
The model is pinned to `jev-1.13.0`. Set `JEV_MODEL` to test another version.

## The scenarios

| Scenario | The question it asks | What I saw on 2026-09-20 |
| --- | --- | --- |
| `scaling` | Does adding questions to a request slow it down? | 1 question 820 ms, 120 questions 850 ms |
| `stability` | Do answers change between runs, or when options are reordered? Do `noul` and `choice` agree? | Third-decimal jitter. Order does not matter. `noul` 0.20 against `choice` 0.01 on the same question |
| `weaknesses` | Can it count, add, and compare dates? | Counts 60 items correctly. Says a total matches when it is $100 off. Unsure on date gaps near a threshold |
| `long_context` | Does it find one line in 12,600 tokens? Where is the limit? | Found at every position. Over 32k tokens is a hard `max_tokens_exceeded` |
| `requirement_evidence` | Does a résumé show a skill? Named tools, described work, keyword stuffing, injection, borderline wording, messy text | 20/20 against labels. The same stuffed résumé scores 0.17 or 0.96 depending on how the question is written |
| `candidate_pool` | Do eight graded candidates for one job come out in order? | Scores span 0.04 to 0.96. In order once answers under 0.3 are treated as zero |
| `identity_swap` | Do answers move when the name, city, university and employers change? | At most 0.01 |
| `interview` | Do answers land on the rubric level? Does it credit a candidate for what the interviewer said? | 5/5 levels. An answer that orders the top score gets the bottom level. The echoing candidate scores 0.09 of 3 |
| `guardrail` | Is this shell command destructive? | 27/28 at 0.8 s. Missed the fork bomb. Gemini 28/28 at 4.9 s |
| `sql_injection` | Can request input change this SQL? | 12/12 |
| `calibration_boolq` | Does 0.9 mean right nine times in ten? 400 labelled yes/no questions | 89% accurate, calibration error 0.03. Gemini Flash 93%, equally calibrated, but only 10 distinct confidence values against 45 |
| `calibration_agnews` | The same for a four-way `choice`, 300 articles | 84% accurate, overconfident: 0.998 stated, 0.90 actual in the top bin. Most errors are technology-company stories the dataset files under sci/tech |

The full console output of my run is in
[`results/reference-run.txt`](results/reference-run.txt). Expect small
differences: Jev moves in the third decimal place between runs, Gemini moves
more, and latency depends on where you are. I ran this from India against a
service hosted on the US West Coast.

## What I took from it

1. **The criteria are the algorithm.** Say what does not count, keep the
   criteria in version control, and write the test cases first.
2. **One judgement per question.** Combine answers in code, where the weights
   are visible. Treat anything under about 0.3 as zero before you add things up.
3. **Do arithmetic and date logic in code** and pass the result in.
4. **Calibration is relative to the question you wrote.** Check it on your own
   labels before you trust a threshold.
5. **There is no explanation in the response.** Keep an LLM, or a person, for
   anything someone has to read.

## How the tests are built

- Every résumé, interview answer and transcript in `scenarios/_data.py` is
  invented. No real person's data is in this repository, and you should not put
  any in: recruiting is a high-risk use under the EU AI Act, and a résumé is
  personal data.
- I wrote the expected labels before the first run of each scenario. They are
  one person's judgement, which is the point of letting you read and change
  them.
- BoolQ and AG News are public, so a model may have seen them in training. They
  are fetched from the Hugging Face datasets server on first use and cached in
  `.cache/`.
- The samples are small. A result of 27 out of 28 is an observation, not a
  benchmark.

## Add a scenario

Create `scenarios/<name>.py` with a `TITLE` and a `run(args)` that prints its
findings and returns something JSON-serialisable, then add the name to
`SCENARIOS` in `run.py`. `jevlab.client.ask(state, questions)` returns the
response and the latency in milliseconds.

## Licence

MIT. Not affiliated with TypeSafe.
