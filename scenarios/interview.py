"""Rubric scoring of interview answers, including an answer that instructs the model and a candidate who only agrees."""
from jevlab import client

from . import _data as d

TITLE = "Interview answers against a rubric"


def run(args):
    print("1. One question, five answers. Expected level in brackets.")
    answers = []
    for expected, label, text in d.INCIDENT_ANSWERS:
        response, _ = client.ask({"question": d.INCIDENT_QUESTION, "candidate_answer": text}, {"ownership": d.INCIDENT_RUBRIC})
        a = response["answers"]["ownership"]
        answers.append({"label": label, "expected": expected, "score": a["score"], "confidence": a["confidence"]})
        dist = " ".join(f"{k}={v:.2f}" for k, v in sorted(a["probabilities"].items()))
        print(f"  {label:9} [{expected}] score {a['score']:.2f}  conf {a['confidence']:.2f}  {dist}")

    print("\n2. Two transcripts, three criteria in one request.")
    transcripts = {}
    for label, text in (("reasons alone (expect 3 / 2 / yes)", d.TRANSCRIPT_OWN), ("echoes the interviewer (expect 0 / 1 / no)", d.TRANSCRIPT_ECHO)):
        response, ms = client.ask({"transcript": text}, d.TRANSCRIPT_RUBRIC)
        a = response["answers"]
        transcripts[label] = {k: client.value(a[k]) for k in a}
        print(f"  {label:42} design {a['system_design']['score']:.2f}  communication {a['communication']['score']:.2f}  raised failure modes {a['raised_failure_modes']['noul']:.2f}  ({ms:.0f} ms)")
    return {"answers": answers, "transcripts": transcripts}
