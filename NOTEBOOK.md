## Entry 1 — baseline reproduction
command: uv run starter_kit/fertility.py --corpus eng=partA/corpus/eng.dev --corpus hin=partA/corpus/hin.dev --tokenizer gpt2
result:
tokenizer: gpt2
lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.39       0.230
hin                       7.63       1.505

hin is 5.50x the fertility of eng (worse tokenization)

Expectation: this roughly matches REPORT_v0's ~5.89x claim, confirming the
intern's number is reproducible — the bug isn't a fluke, it's structural.


## Entry 2 - baseline reproduction on tam and kan - extended to 4 languages
command: uv run flam-submission/starter_kit/fertility.py --corpus eng=flam-submission/partA/corpus/eng.dev --corpus hin=flam-submission/partA/corpus/hin.dev --corpus tam=flam-submission/partA/corpus/tam.dev --corpus kan=flam-submission/partA/corpus/kan.dev --tokenizer gpt2

result:
tokenizer: gpt2

lang      fertility (tok/word)    tok/char
------------------------------------------
eng                       1.39       0.230
hin                       7.63       1.505
tam                      23.66       2.677
kan                      19.24       2.584

hin is 5.50x the fertility of eng (worse tokenization)
tam is 17.05x the fertility of eng (worse tokenization)
kan is 13.87x the fertility of eng (worse tokenization)