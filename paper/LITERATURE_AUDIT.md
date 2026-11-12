# Related work and novelty audit

## Which references and bibliographic details are verified?

### Takeaway
All five identifiers resolve to relevant primary papers. Two supplied titles need correction; cite verified titles below.

### Cited Findings
- **Jimenez et al. (2024), _SWE-bench: Can Language Models Resolve Real-World GitHub Issues?_** arXiv:2310.06770v3. Authors: Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, Karthik Narasimhan. The paper defines `base_commit` as the state preceding the reference patch, distinguishes solution/test patches and hints, and describes BM25 retrieval. This supports pre-fix indexing and exclusion of future patches/hints. — [Full text](https://arxiv.org/html/2310.06770v3)
- **Chen et al. (2025), _LocAgent: Graph-Guided LLM Agents for Code Localization_.** ACL 2025, pp. 8697–8727, DOI 10.18653/v1/2025.acl-long.426. Uses heterogeneous code graphs and LLM-guided search/traversal. — [ACL record](https://aclanthology.org/2025.acl-long.426/), [authoritative PDF](https://aclanthology.org/2025.acl-long.426.pdf)
- **Qin and Xie (2026), _Agent Retrieval Bench: Evaluating Repository Context Retrieval for Coding Agents_.** arXiv:2607.24882v1. Authors: Bowen Qin and Yi Xie. Evaluates frozen-commit workflow-context retrieval and counterfactual wrong-repository controls. — [Full text](https://arxiv.org/html/2607.24882v1)
- **Bellam (2026), _How Much Do Structural Tools Help Small Coding Agents? A Pre-Registered Scale Study of Code Localization_.** arXiv:2610.33958v2, revised November 9, 2026. Sole listed author: Saurav Bellam. This is the current verified title, replacing the prompt's “How Do Small Coding Agents Use Code Graphs and Embeddings?” — [Full text](https://arxiv.org/html/2610.33958v2)
- **Caumartin, Chen, and Costa (2026), _Retrieval-Oriented Code Representations in Agentic Bug Localization_.** arXiv:2607.11046v1. Authors: Genevieve Caumartin, Tse-Hsun (Peter) Chen, Diego Elias Costa. Compares code representations, retrieval, fusion, and LLM reranking. This replaces the supplied title “Code Retrieval Representations in Agentic Bug Localization.” — [Full text](https://arxiv.org/html/2607.11046v1)

### Inferences
- Use “Chen et al.” for LocAgent: the landing-page metadata lists Robert Tang, whereas the PDF lists Xiangru Tang. This discrepancy does not affect the technical positioning.

### Gaps
- This audit verifies sources and described protocols, not independent reproduction of their results.

## How much of the proposed evaluation already exists?

### Takeaway
Counterfactual controls, leakage checks, frozen snapshots, budget-aware evaluation, and masking already have adjacent precedents. The paper must describe a narrower resource contribution.

### Cited Findings
- LocAgent ablates graph traversal, relation types, one-hop traversal, entity retrieval, and BM25 indexing (Table 6). Its graph-localization contribution predates this project. — [Section 5.6](https://aclanthology.org/2025.acl-long.426.pdf)
- Agent Retrieval Bench checks exact gold paths, patches, fix hashes, and generated artifacts; preserves realistic distractors; and reports context-budget curves. Its counterfactual is a wrong-repository control, not a same-degree graph intervention. — [Sections 6 and 8](https://arxiv.org/html/2607.24882v1)
- Bellam's placebo replaces returned entities with random definitions from the same repository while retaining output lines, format, and headers. Its gold masking replaces gold-definition tool-output lines, rather than removing target names from issue queries. It also separates graph and embedding contributions. — [Appendix B, “Placebo and masking,” and Section 4.2](https://arxiv.org/html/2610.33958v2)
- Caumartin et al. study representations on Long Code Arena and SWE-bench Verified and rerank retrieved candidates. This supports keeping index representation identical across topology arms. — [Section 3](https://arxiv.org/html/2607.11046v1)

### Inferences
- Safe wording: “PatchScope-CF packages a lightweight, model-free audit combining a directed-degree-preserving import-graph intervention, identical lexical candidate pools, and an explicitly label-informed target-name query stress-test.”
- Do not claim the first graph-based localizer, first counterfactual localization evaluation, first masking analysis, or first leakage-audited frozen-commit retrieval benchmark.

### Gaps
- I did not identify the exact combined protocol in these five papers or targeted searches for degree-preserving code-graph localization. This is limited negative evidence, not proof of priority. A broader systematic review could find earlier equivalents.

## What scientific limits should accompany that positioning?

### Takeaway
A same-degree topology intervention answers a narrow ranking question. It cannot establish downstream agent repair gains or a universal conclusion about code graphs.

### Cited Findings
- SWE-bench's original task is patch generation evaluated against tests; a file-localization metric measures only an upstream component. — [Task formulation](https://arxiv.org/html/2310.06770v3)
- Bellam distinguishes exposure to gold code from conversion into successful localization; tool effectiveness depends on the model and harness. — [Sections 5–7](https://arxiv.org/html/2610.33958v2)

### Inferences
- Identical top-100 pools isolate reranking but prohibit graph discovery outside the lexical pool; state that tradeoff explicitly.
- Exact in/out degree preservation controls node popularity but not every structural property. Bounded edge swaps do not guarantee uniform null sampling or mixing; report successful swaps and retained-edge fractions.
- Gold-informed query masking changes the task and can remove useful ordinary language. Treat it as diagnostic information removal, never an ordinary deployment setting or a stand-alone causal claim.
- A small deterministic Lite subset supports pilot findings only. Report null and negative results and uncertainty without comparing its scores directly to published agent results.

### Gaps
- The current project has no LLM/Gemma arm, downstream repair evaluation, or graph-null mixing analysis. These are limitations, not implied completed experiments.
