
# ContextGuard

**Repository-Context-Aware Verification Filtering for Reliable LLM-Based Code Review**

ContextGuard is a code review verification system designed to reduce false positives in LLM-generated code review findings. It retrieves relevant repository context, grounds findings in tests and requirements, generates targeted tests, and compares test results against original and patched code before deciding whether a finding should be kept, filtered, or marked uncertain.

## Planned Pipeline

Pull Request Ingestion → Repository Chunking → Hybrid Retrieval → LLM Review → Context Assembly → Test Generation → Sandboxed Execution → Verification Filter

## Status

- [x] Repository initialized
- [x] Python virtual environment created
- [x] Git ignore rules added
- [ ] Project skeleton and schemas
- [ ] Pull request ingestion
- [ ] Retrieval and ranking
- [ ] Review and verification pipeline
- [ ] Evaluation and dashboard
- [ ] CI and release
