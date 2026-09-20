"""Does a résumé show a skill? Named tools, described-but-unnamed work, keyword stuffing, injection, borderline wording."""
from jevlab import client

from . import _data as d

TITLE = "Requirement evidence on synthetic résumés"


def _ask(text, questions):
    response, _ = client.ask({"resume": text}, questions)
    return {k: response["answers"][k]["noul"] for k in questions}


def run(args):
    contrastive = {k: d.requirement(q) for k, q in d.REQUIREMENTS.items()}
    keys = list(contrastive)
    short = [k[:12] for k in keys]

    print("1. Four résumés, five requirements. Expected label in brackets.")
    base, hits = {}, 0
    for name, text in d.CANDIDATES.items():
        base[name] = _ask(text, contrastive)
        cells = []
        for k, s in zip(keys, short):
            ok = (base[name][k] >= 0.5) == bool(d.EXPECTED[name][k])
            hits += ok
            cells.append(f"{s}={base[name][k]:.2f}[{d.EXPECTED[name][k]}]{'' if ok else '!'}")
        print(f"  {name:12} " + "  ".join(cells))
    print(f"  agreement with labels at 0.5: {hits}/{len(d.CANDIDATES) * len(keys)}")

    print("\n2. The criteria are the algorithm: the keyword-stuffed résumé, three wordings.")
    wordings = {
        "naive recruiter phrasing": {k: d.requirement(q, None) for k, q in d.NAIVE_REQUIREMENTS.items()},
        "precise question, no criteria": {k: d.requirement(q.replace("personally ", ""), None) for k, q in d.REQUIREMENTS.items()},
        "precise question + contrastive criteria": contrastive,
    }
    wording_out = {}
    for label, questions in wordings.items():
        wording_out[label] = _ask(d.CANDIDATES["C_stuffed"], questions)
        print(f"  {label:42} " + "  ".join(f"{s}={wording_out[label][k]:.2f}" for k, s in zip(keys, short)))

    print("\n3. An appended instruction to the model (before -> after).")
    injected = {}
    for name in ("C_stuffed", "D_adjacent"):
        injected[name] = _ask(d.CANDIDATES[name] + d.INJECTION, contrastive)
        print(f"  {name:12} " + "  ".join(f"{s}={base[name][k]:.2f}->{injected[name][k]:.2f}" for k, s in zip(keys, short)))

    print("\n4. Borderline and adversarial bullets for container orchestration. Y >= 0.7, M 0.3-0.7, N <= 0.3.")
    question = {"k8s": contrastive["container_orchestration"]}
    borderline, in_band = [], 0
    for band, name, bullet in d.BORDERLINE:
        p = _ask("Software Engineer, 2020-2026, Northwind\n" + bullet, question)["k8s"]
        got = "Y" if p >= 0.7 else ("N" if p <= 0.3 else "M")
        in_band += got == band
        borderline.append({"case": name, "p": p, "expected": band, "got": got})
        print(f"  {name:22} {p:.2f} -> {got} [{band}]{'' if got == band else '  <- differs'}")
    print(f"  in the expected band: {in_band}/{len(d.BORDERLINE)}")

    print("\n5. Messy input: PDF-extraction noise and Hinglish, against the clean B_described résumé.")
    noisy = d.CANDIDATES["B_described"].replace(" ", "  ").replace("- ", "•\n").replace("containerised", "container-\nised").replace("language model", "lan-\nguage  model")
    noisy = "Page 1 of 2\nCurriculum Vitae\n" + noisy + "\nPage 2 of 2\nReferences available on request"
    messy = {"clean": base["B_described"], "pdf noise": _ask(noisy, contrastive), "hinglish": _ask(d.HINGLISH, contrastive)}
    for label, row in messy.items():
        print(f"  {label:10} " + "  ".join(f"{s}={row[k]:.2f}" for k, s in zip(keys, short)))
    return {"four_resumes": base, "wording": wording_out, "injection": injected, "borderline": borderline, "messy": messy}
