# Jev experiment records

These files support the draft [Testing Jev](https://abhishekanand.in/blog/testing-jev-system-one-model). They contain public-dataset numeric results and synthetic inputs. No real candidate records, API keys, or authentication headers are included.

## Recompute the results without API calls

From the repository root, using Python 3.10 or newer and only its standard library:

```bash
python followup/summarize.py
```

The command prints JSON with accuracy, calibration bins, Brier scores, confidence thresholds, latency, token counts, injection comparisons, repeats, and exact checks. It validates the synthetic-case hash, request states, returned model IDs, probability bounds, and probability-distribution sums. It fails on incomplete or unsuccessful saved runs. It never reads credentials or calls an API.

The follow-up comprises **105 successful requests**: 49 to Jev, 28 to Gemini 3.7 Flash, and 28 to Gemini 3.8 Flash. The summary also works without the optional `gemini-3.8-results.json` file, in which case it reports 77 requests.

These are the article’s original results and later diagnostic tests. The root
`results/reference-run.txt` records a separate run of the twelve scenarios; its
figures differ slightly. Neither run replaces the other.

## Files and provenance

| File                         | What it preserves                                                                                                                              |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `boolq-jev-original.json`    | 400 probabilities, labels, latencies, and input-token counts from the original BoolQ run                                                       |
| `boolq-gemini-original.json` | The same 400 items in the same order, with Boolean answers, chosen-answer confidence, latency, input tokens, and response-plus-thinking tokens |
| `agnews-jev-original.json`   | 300 labels, predictions, selected-option probabilities, and separate API confidence values                                                     |
| `cases.json`                 | 24 synthetic evidence cases and four appended-instruction variants, with labels frozen before the follow-up                                    |
| `followup-results.json`      | 28 evidence cases per provider, 12 Jev repeats, and four Jev requests with 30 additional questions: 72 requests                                |
| `gemini-3.8-results.json`    | The 28 original Gemini request bodies replayed against Gemini 3.8 Flash                                                                        |
| `exact-results.json`         | Three invoice-total checks and the same fork-bomb text under two policies: five Jev requests                                                   |

The original numeric exports do not contain response model IDs, dataset row IDs, timestamps, full prompts, or raw responses. They allow recomputing the reported metrics, but not reconstructing the entire original run. The original script pinned `jev-1.13.0`. Experiment notes name Gemini 3.7 Flash, but the saved baseline does not independently establish that version. The article therefore calls that baseline **Gemini Flash**. The newer records preserve requested and returned model IDs.

The original BoolQ sample contains 400 validation items. Its row-selection provenance was not preserved here. The AG News script selected test rows 0–99, 3000–3099, and 6000–6099; that is a fixed, nonrandom sample. Public datasets may overlap model training data. Original rows are paired by saved order; matching labels do not independently prove item identity.

The original exploratory batching, résumé, SQL-injection, log-needle, and interview results survive as experiment notes and scripts outside this published folder, rather than saved request/response records. The article identifies the few retained exploratory observations separately. The batching test used three calls per size and repeated 20 question templates in its larger batches. The summary cannot independently verify those timings or the original résumé scores. Invoice and fork-bomb examples have fresh saved responses here.

## Metric definitions and limits

- Binary predictions use `p >= 0.5`. Chosen-answer confidence is `max(p, 1 - p)`. Gemini's original answer/confidence pair is converted to a probability of yes for Brier score.
- The original Gemini script clipped reported confidence to the range 0.5–1 before saving. Its export cannot establish whether any values were clipped. Follow-up responses preserve the original values.
- ECE is the count-weighted absolute confidence/accuracy gap within bins. BoolQ edges are 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, and 1.00. The last bin includes 1.00. The script also prints a 20-bin sensitivity check; the ranking changes with the bins.
- Confidence-threshold results report retained count, coverage, and accuracy among retained answers. More distinct probability values do not necessarily improve this trade-off.
- AG News calibration uses the **selected option's probability**. The API's separate `confidence` statistic is also reported for comparison; the two are not interchangeable. Its bins are 0, 0.60, 0.80, 0.90, 0.97, and 1.00.
- Synthetic results measure agreement with the frozen rubric, not objective reasoning ability. “Only administrators can delete” is an ambiguous permission example; Gemini 3.8's `not_stated` answer is logically defensible. The rubric also distinguishes documentation languages from support languages and requires explicit evidence of exclusion between plans.
- Four appended-instruction examples do not estimate attack resistance. Four repeated cases do not establish stability across days or versions. No calibration claim is based on this small synthetic set.

Follow-up evidence runs use four workers, fresh HTTP connections, no retries, temperature zero for Gemini, and provider-default Gemini thinking settings. The Gemini 3.8 replay happened later than the first comparison. Exact checks run sequentially. Latency includes connection setup and network time from the client in India; it is not server inference time or a matched-compute benchmark. The original clients handled retries differently: Jev retained successful-attempt latency, while Gemini timing could include retries.

The author supplied a Jev usage-dashboard snapshot showing 943 requests, 650,464 tokens, and USD 0.0251 estimated spend after the original experiments and follow-up. The dashboard warns that statistics may be delayed and estimates spend at $0.042 per million input tokens, with output free. This is not a billing receipt. The displayed token counter is not identified as input-only in the supplied snapshot; do not multiply it by the input rate to reconstruct the spend. These dashboard totals have not been reconciled with individual saved requests.

Jev costs shown by the summary are calculations at the published 20 September 2026 price of $0.042 per million input tokens. They cover the saved runs, not every original exploratory call. Token counts use each provider's tokenizer. Gemini output counts in the original export include thinking tokens; newer records preserve both fields separately.

## Run new requests

These commands make paid API calls only with `--run`. Without that flag, they print a plan and do not read credentials. Choose a new output filename; runners refuse to overwrite an existing result file.

```bash
# Jev evidence checks, repeats, and bundled questions: 44 calls.
python followup/run_followup.py --run --output /tmp/jev-new.json

# Add the 28-case Gemini 3.7 baseline; both keys can live in the local .env.
python followup/run_followup.py --run --gemini-env .env --output /tmp/jev-gemini-new.json

# Replay the saved Gemini request bodies against another model: 28 calls.
python followup/run_gemini_baseline.py --run --model gemini-3.8-flash --output /tmp/gemini-new.json

# Invoice and guardrail policy checks: five Jev calls.
python followup/run_exact_checks.py --run --output /tmp/jev-exact-new.json
```

Set `TYPESAFE_API_KEY` or `GEMINI_API_KEY` in the environment, or keep them in the local `.env`. The original `JEV_API_KEY` name is also accepted as an alias. The evidence runner also accepts `--jev-env`; the exact-check and Gemini-replay runners accept `--env`. Credentials are sent only as request headers and are not written to result files. Shell commands in the cases are classification input; the runners never execute them.

## Offline checks

Run `python -m unittest discover -s tests -v` from the repository root. These checks use synthetic responses and make no API calls.
