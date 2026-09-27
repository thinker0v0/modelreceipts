# 경쟁 지형: 오픈소스 "태스크별 최적 모델 지식베이스" (2026-09-27 기준)

> 조사 방법 메모: WebSearch 17회 + WebFetch 2회(OpenRouter 문서/블로그). WebSearch 결과는 검색 도구가 요약한 스니펫이라 1차 출처 원문을 모두 직접 열어 확인하지는 않았다. 원문으로 직접 확인한 항목은 [원문확인]으로 표시했다. 벤더 비교글(Morph, OrcaRouter, Bito, Requesty, Braintrust, Helicone 등)은 이해관계가 있는 출처라서 따로 표시했다.

## Q1. 공개 리더보드/아레나: 태스크 세분도와 데이터 개방성

### Takeaway
주요 리더보드는 두 계열로 나뉜다. (a) 벤치마크 계열(Artificial Analysis, HELM, SEAL, Epoch, Vellum)은 "능력 도메인" 몇 개 수준으로 쪼개고, (b) 선호/사용량 계열(Arena, OpenRouter)은 최대 수십 개 카테고리까지 쪼갠다. 그러나 **어느 쪽도 "실제 업무를 끝낸 뒤의 결과(outcome)"를 측정하지 않는다.** 전부 사람의 쌍대 선호 투표, 통제된 벤치마크 점수, 토큰/지출 점유율 중 하나다. 데이터 개방성도 제각각이다. Arena는 일부 투표 스냅샷을 공개하지만 전체와 실시간 데이터는 비공개이고(유료 사업의 핵심 자산), OpenRouter는 집계치만 CC BY 4.0으로 공개한다.

### Cited Findings
**LMArena → "Arena" (arena.ai)**
- 2026-01-06 Series A로 $150M를 유치했고 post-money 기업가치는 $1.7B다(리드: Felicis, UC Investments. a16z, Kleiner Perkins, Lightspeed 등 참여). 2025-05에 $100M 시드($600M 밸류)를 받았다. 2025-12 기준 ARR은 $30M, 월 사용자 500만 명 이상, 월 대화 6,000만 건 이상이다 — [TechCrunch](https://techcrunch.com/2026/01/06/lmarena-lands-1-7b-valuation-four-months-after-launching-its-product/); [Wikipedia](https://en.wikipedia.org/wiki/LMArena)
- 수익 모델은 무료 공개 사이트로 투표를 모으고, 기업과 AI 랩에 private evaluation, custom arena, API, analytics를 파는 구조다. OpenAI와 Anthropic도 고객이다 — [TechCrunch](https://techcrunch.com/2026/01/06/lmarena-lands-1-7b-valuation-four-months-after-launching-its-product/)
- 2026-01-28 "Arena"로 리브랜딩하고 arena.ai로 이전했다. 2026-01-13 투표 파이프라인 개편으로 일부 Elo가 30점 이상 이동했으므로 전후 비교에 주의해야 한다. 2025-12-18에는 랭킹 방법론을 담은 오픈소스 패키지 Arena-Rank를 공개했다 — [Wikipedia](https://en.wikipedia.org/wiki/LMArena); [productleadersdayindia (2차, 2026-05)](https://productleadersdayindia.org/blogs/lmarena-leaderboard/lmarena-leaderboard.html)
- 태스크 세분도: 2025-11 "Arena Expert"와 Occupational Categories를 도입했다. 모든 프롬프트를 23개 직무 분야로 분류하고, 그중 상위 8개(Software & IT Services, Writing/Literature/Language, Life/Physical/Social Science, Entertainment/Sports/Media, Business/Management/Financial Ops, Mathematical, Legal & Government, Medicine & Healthcare)에 별도 리더보드를 둔다. 전체 프롬프트의 약 5.5%가 "expert"로 태깅된다. 비중은 Software/IT 약 28%, Writing 약 25%, Science 약 17%다 — [Arena blog: Arena Expert](https://arena.ai/blog/arena-expert); [news.lmarena.ai](https://news.lmarena.ai/arena-expert/)
- 2026-06 기준 360개 이상 모델을 평가하며, 카테고리는 Overall, Expert, Coding, Math, Creative Writing, Instruction Following, Multi-Turn, Hard Prompts, Occupational이다. 모달리티별로 text, webdev, vision, text-to-image, video(2026-01)가 있다 — [toolcenter.ai (2차)](https://www.toolcenter.ai/en/articles/lmarena-review-2026); [Wikipedia](https://en.wikipedia.org/wiki/LMArena)
- 데이터 개방: Hugging Face `lmarena-ai` 조직에 스냅샷을 공개한다. arena-human-preference-55k(Apache-2.0), 100k(2024-06~08, 프롬프트 CC-BY-4.0), 140k(2025-04~07, text), search-arena-24k(2025-03~05)가 있다. 가장 최근 공개 스냅샷도 2025년 7월 데이터라서 실시간이나 전체 데이터는 아니다 — [HF 140k](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k); [HF 55k](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-55k); [HF search-arena-24k](https://huggingface.co/datasets/lmarena-ai/search-arena-24k)
- 비판 — "The Leaderboard Illusion"(arXiv 2504.20879, 2025-04, Cohere/Stanford/MIT/Ai2 등, NeurIPS 2025 포스터): 일부 대형 제공사가 비공개 변형을 여러 개 테스트한 뒤 가장 좋은 점수만 공개할 수 있었다(예: Meta가 2025-03에 27개 변형 테스트). 상위 2개 제공사가 Arena 데이터의 약 19.2%와 20.4%를 가져간 반면 오픈웨이트 83개 모델은 합쳐 약 29.7%였다. 공개 모델 243개 중 205개가 조용히 폐기됐다 — [arXiv](https://arxiv.org/abs/2504.20879); [Simon Willison](https://simonwillison.net/2025/Apr/30/criticism-of-the-chatbot-arena/)
- LMArena 반박: 사전 테스트 정책은 2024-03부터 공개돼 있었고, 사전 테스트의 실제 효과는 약 11 Elo이며, 오픈 모델 비중은 40.9%라고 주장했다 — [LMArena response](https://news.lmarena.ai/our-response/)
- Inclusion AI(Ant Group 계열)는 Arena의 한계로 일반 도메인 프롬프트 편중, 불균형 샘플링, 조작 가능성을 지적했다 — [arXiv 2508.11452](https://arxiv.org/abs/2508.11452)

**Artificial Analysis**
- Intelligence Index v4.3.2는 10개 평가(AA-Briefcase, GDPval-AA, AutomationBench-AA, Terminal-Bench 4.0, SciCode, AA-LCR, AA-Omniscience, HLE, GDP.pdf, CritPt)로 구성된다. pass@1을 쓰고, 영어 텍스트 중심이며, 비용은 토큰 단가로 산출한다 — [AA Index 페이지](https://artificialanalysis.ai/evaluations/artificial-analysis-intelligence-index); [AA methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking)
- v4.0(2026-01-06)에서 4개 카테고리를 각 25%로 두었고, v4.1(2026-06)에서 Agents 34%, Coding 24%, Scientific Reasoning 24%, General 18%로 바꿨다. 세분도는 "카테고리 4개 + 개별 벤치" 수준이다 — [AA methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking); [smartchunks (2차)](https://smartchunks.com/artificial-analysis-intelligence-index-april-2026-explained/)
- 공개된 펀딩은 $250K(AI Grant 등)이며, 이는 오래됐을 수 있는 DB 기준이다 — [PitchBook](https://pitchbook.com/profiles/company/680302-90); [Caplight](https://www.caplight.com/company/artificialanalysis)

**HELM (Stanford CRFM)**
- HELM Capabilities는 MMLU-Pro, GPQA, IFEval, WildBench, Omni-MATH 등 큐레이션된 시나리오로 구성되고, 모든 프롬프트를 공개하며 완전히 재현할 수 있다(오픈소스 프레임워크). 관련해 HELM Long Context, MedHELM 같은 도메인판도 있다. 공지는 2025년 자료다 — [HELM Capabilities (2025-03)](https://crfm.stanford.edu/2025/03/20/helm-capabilities.html); [GitHub](https://github.com/stanford-crfm/helm)

**Scale SEAL (현재 labs.scale.com)**
- 2024-05에 시작했다. Scale이 만든 비공개 데이터셋과 전문가 루브릭을 쓴다(오염 방지를 위해 비공개). SWE-Bench Pro는 1,865개 태스크, 250턴 제한이다. 같은 Opus 4.5가 SWE-bench Verified 80.9% 대 SEAL 45.9%로, 하네스에 따라 점수가 두 배 차이 날 수 있다 — [Scale blog](https://scale.com/blog/leaderboard); [Scale Labs](https://labs.scale.com/leaderboard); [Kili (2차, 2026)](https://kili-technology.com/blog/ai-benchmarks-guide-the-top-evaluations-in-2026-and-why-theyre-not-enough)

**Epoch AI Benchmarking Hub**
- 2026-09-26에 업데이트됐다. 자체 실행 결과와 외부 결과를 담은 DB이고, Epoch Capabilities Index(ECI)는 여러 벤치를 단일 능력 척도로 합친다. 오픈소스 Python 클라이언트(`pip install epochai`)가 있다 — [Epoch benchmarks](https://epoch.ai/benchmarks); [Epoch hub update](https://epoch.ai/blog/benchmarking-hub-update)

**Hugging Face Open LLM Leaderboard**
- v1은 2024-06에 아카이브됐고 v2(IFEval, MuSR, GPQA, MATH, BBH, MMLU-Pro)는 2025-03에 은퇴했다. 은퇴 이유는 "hill climb irrelevant directions"을 조장할 우려였다. 데이터는 OpenEvals 컬렉션에 아카이브돼 있고, 커뮤니티 리더보드 200개 이상이 이를 대체한다 — [HF 토론](https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/1135); [HF archived collection](https://huggingface.co/collections/OpenEvals/archived-open-llm-leaderboard-2024-2025); [burtenshaw post](https://huggingface.co/posts/burtenshaw/596060753193040)

**Vellum 등 집계형**
- Vellum LLM Leaderboard는 제공사 발표치, 자체 평가, 커뮤니티 평가를 모아 공개 벤치 결과를 보여 준다(툴 사용, 멀티스텝 워크플로, computer use 포함) — [Vellum](https://www.vellum.ai/llm-leaderboard)
- 서드파티 집계 사이트(BenchLM 등)는 데이터 품질 문제가 있다. BenchLM의 AA 페이지 209행 중 0행이 원출처 또는 독립 실행이고 205행이 2차 보고다 — [BenchLM](https://benchlm.ai/benchmarks/artificialanalysis)

**OpenRouter Rankings (사용량 계열)**
- 실제 API 토큰 처리량으로 순위를 매긴다. 뷰는 Top Models, 태스크별, market share, languages, programming, context length, tool calls, images, top apps 등이 있다. 랭킹 데이터는 CC BY 4.0이고 JSON Data API가 있다. private로 표시된 요청은 집계에서 뺀다 — [OpenRouter rankings](https://openrouter.ai/rankings); [OpenRouter Data](https://openrouter.ai/data)
- OpenRouter 스스로 "rankings measure adoption, not quality"라고 명시한다 — [digitalapplied (2차)](https://www.digitalapplied.com/blog/openrouter-usage-charts-what-they-measure); [datastudios (2차)](https://www.datastudios.org/post/openrouter-rankings-real-usage-data-model-popularity-and-how-to-choose-wisely)
- 앱 귀속은 `HTTP-Referer`와 `X-OpenRouter-Title`, 카테고리는 `X-OpenRouter-Categories` 헤더로 한다 — [App Attribution docs](https://openrouter.ai/docs/app-attribution)
- 서드파티에 따르면 현재 export에는 앱 단위 합계만 있고 앱×모델 행은 없다 — [codesota (2차)](https://www.codesota.com/agentic/openrouter-models)
- a16z와 함께 낸 "State of AI" 2025 보고서가 있다 — [OpenRouter Data](https://openrouter.ai/data)

### Inferences
- 벤치마크형은 "통제된 과제 × 모델" 매트릭스이고, Arena는 "익명 프롬프트에 대한 사람 선호"이고, OpenRouter는 "지출/토큰 점유율(=시장 선택)"이다. 제안 프로젝트의 핵심 신호인 **실제 작업 완료 후의 결과, 방법(워크플로/하네스), 비용과 지연을 한 레코드로 묶은 것**은 어느 리더보드에도 없다.
- SEAL과 SWE-bench Verified의 점수 차는 "모델"보다 "모델 + 하네스/방법" 조합이 성능 단위임을 보여 준다. 제안 프로젝트가 model 외에 method/workflow를 기록하려는 설계와 맞아떨어진다.
- Arena의 최대 세분도는 약 23개 직무 분야이고, OpenRouter는 약 30개 태스크 타입이다(Q2 참고). 제안 프로젝트가 "내 태스크"라는 세분도를 약속하려면 이보다 훨씬 미세한 분류 체계(예: 태스크 타입 × 도메인 × 입력 특성)가 필요하고, 그만큼 셀당 표본이 희소해진다.

### Gaps
- LiveBench와 SWE-bench 공식 리더보드의 2026년 현재 카테고리 구성은 직접 확인하지 못했다.
- Artificial Analysis의 2026년 추가 펀딩 여부는 알 수 없다. PitchBook/Caplight의 $250K는 오래된 값일 수 있다.
- Arena가 2025-07 이후 새 공개 데이터셋을 냈는지는 확인하지 못했다.
- HELM Capabilities의 2026년 최신 버전과 순위는 미확인이다(확인한 자료가 2025년 공지).

## Q2. 모델 라우터/추천기: 교차 사용자 결과 데이터로 학습하는가, 그 데이터를 공유하는가

### Takeaway
라우터들은 (1) 공개 선호 데이터나 벤치로 학습하는 오픈소스 연구형(RouteLLM), (2) **고객 자신의** 평가 데이터로 맞춤 라우터를 훈련하는 상용형(Not Diamond, Martian, Unify), (3) 휴리스틱 분류형(Requesty)으로 나뉜다. 가장 가까운 예외는 **OpenRouter Auto Router(현행)**다. 약 30개 태스크 타입별로 "커뮤니티의 7일간 지출 점유율"로 모델을 고르는데, 이는 교차 사용자 신호이지만 품질이 아니라 지출(시장 선택)이고, 원시 데이터도 공유하지 않는다. 품질·결과 신호를 교차 사용자로 모아 공개하는 라우터는 찾지 못했다.

### Cited Findings
- **OpenRouter Auto Router** [원문확인]: 경량 분류기가 프롬프트를 "~30 fine-grained task types"(예: `code:debugging`, `math`, `customer_support`) 중 하나로 분류하고, 해당 태스크에서 OpenRouter 사용자들의 "trailing 7-day window" 지출 점유율로 후보를 순위화한다. `cost_tier`(low~max)로 가격대를 고르고, 재학습 없이 "within days" 적응한다. `X-OpenRouter-Metadata: enabled` 헤더를 보내면 `task_type`이 반환된다. 근거는 "aggregate anonymized spend statistics"이고, 결과 집계는 rankings#task-spend에 노출되지만 원시 데이터 공개는 명시하지 않았다 — [OpenRouter Auto Router docs](https://openrouter.ai/docs/guides/routing/routers/auto-router); [OpenRouter blog 2026-06-12 "How OpenRouter Model Routing Works"](https://openrouter.ai/blog/insights/model-routing/)
- 과거 Auto Router는 Not Diamond 기반이었고, 서드파티 가이드는 2026-08-10에 커뮤니티 지출 신호 방식으로 교체됐다고 보고한다. 공식 문서에는 Not Diamond 언급이 없고 "previous version"만 언급된다. 정확한 전환일은 1차 출처로 확인하지 못했다 — [aireiter (2차)](https://aireiter.com/blog/openrouter-auto-router-guide); [OpenRouter docs](https://openrouter.ai/docs/guides/routing/routers/auto-router)
- **Not Diamond**: 60개 이상 모델에 걸친 학습형 메타 라우터다. 사용자가 prompts, candidate responses, eval scores를 제공하면 맞춤 라우터를 훈련한다. 공개 자료상 펀딩은 2025년 말 $2.3M pre-seed(Jeff Dean, Julien Chaumond 등)다. RouterArena 벤치에서 12개 중 12위("frequently selects expensive models")였다 — [Morph (경쟁사 비교글)](https://www.morphllm.com/notdiamond-alternative); [bestaiweb (2차)](https://www.bestaiweb.ai/openrouter-martian-and-not-diamond-the-2026-llm-router-race-and-where-agent-cost-optimization-is-heading/); [dreaming.press 2026-06](https://dreaming.press/posts/2026-06-21-routellm-vs-notdiamond-vs-martian.html)
- **Martian**: "Model Mapping"으로 쿼리별 최적 모델을 예측하고, 고객 eval 데이터로 맞춤 라우터를 훈련한다. 현재 초점을 두고 출처가 충돌한다. QVeris(2026-07)는 라우터 페이지가 사라지고 해석가능성 연구로 이동했다고 하고, Bito(2026-08)는 Gateway가 여전히 활성이라고 한다. $1.3B 밸류 보도는 미확인(Medium발)이다 — [QVeris](https://qveris.ai/guides/martian-llm-router-alternatives/); [OrcaRouter (경쟁사)](https://www.orcarouter.ai/blog/not-diamond-vs-martian); [Bito](https://bito.ai/blog/best-ai-model-routers-for-coding-agents-in-2026/); [bestaiweb](https://www.bestaiweb.ai/openrouter-martian-and-not-diamond-the-2026-llm-router-race-and-where-agent-cost-optimization-is-heading/)
- **RouteLLM** (LMSYS, ICLR 2025, 오픈소스): Chatbot Arena 공개 선호 데이터 약 80K와 GPT-4 judge 증강 데이터로 학습한 강/약 2-모델 라우터다. Arena 데이터에서 임의 두 모델 쌍의 라벨 비율이 0.1% 미만이라 희소성이 핵심 문제였다. 고용량 분류기는 Arena 데이터만으로는 "close to random"이었다. 증강 후 MT Bench에서 비용을 85% 넘게 줄이면서 GPT-4 품질의 95%를 유지했다 — [LMSYS blog 2024-07](https://www.lmsys.org/blog/2024-07-01-routellm/); [arXiv 2406.18665](https://arxiv.org/pdf/2406.18665); [GitHub](https://github.com/lm-sys/routellm)
- **Unify** (YC): 공개 벤치(10분마다 갱신한다고 주장)와 사용자 정의 품질 지표로 라우팅하며, 사용자 전용 라우터를 훈련할 수 있다. 확인한 자료가 대부분 2024~2026 초라서 현재 상태는 불확실하다 — [YC Launch](https://www.ycombinator.com/launches/L4t-unify-the-best-llm-on-every-prompt); [nolist.ai](https://nolist.ai/item/unify-ai)
- **Requesty**: 600개 이상 모델을 다루는 게이트웨이다. "Smart Routing"은 요청 유형을 탐지해 단순 질의는 저가 모델로, 복잡한 추론은 강한 모델로 보낸다. 제공사 선택은 PeakEWMA(1시간 롤링 지연)를 쓴다. 수수료는 5%(자사 주장)다 — [Requesty](https://www.requesty.ai/); [Requesty blog](https://www.requesty.ai/blog/introducing-smart-routing-smart-ai-model-selection)
- 기타 라우터로 vLLM Semantic Router(2026-01), LLMRouter(UIUC 오픈소스 라이브러리), Portkey, LiteLLM이 있다. RouterArena는 모든 지표에서 최고인 라우터가 없다고 보고했다 — [dreaming.press](https://dreaming.press/posts/2026-06-21-routellm-vs-notdiamond-vs-martian.html); [LLMRouter GitHub](https://github.com/ulab-uiuc/LLMRouter)

### Inferences
- OpenRouter Auto Router는 제안 아이디어의 **"질의" 측면을 이미 제품화**했다(태스크 타입 → 커뮤니티 신호 기반 최적 모델). 다만 신호가 지출이라서 인기·가격·기본값 편향이 섞이고 "잘 됐는가"는 담지 않는다. 가장 직접적인 경쟁·참조 대상이다.
- 상용 라우터는 고객 eval 데이터를 **해당 고객 전용**으로 쓰는 구조다. 교차 고객 풀링은 계약과 프라이버시 문제 때문에 공개되지 않는다. 이 공백이 곧 "open commons" 포지셔닝의 여지다.
- RouteLLM의 경험(모델 쌍당 라벨 0.1% 미만, 소량 데이터에서 고용량 모델 실패)은 제안 DB의 **콜드스타트와 희소성 리스크**에 대한 직접 증거다. 태스크 세분화가 심할수록 셀당 데이터가 부족해진다.

### Gaps
- Not Diamond의 2026년 추가 펀딩, Martian의 현재 제품 상태와 펀딩은 1차 출처로 확인하지 못했다.
- OpenRouter task-spend 랭킹을 API로 태스크 타입별로 받을 수 있는지(공개 범위)는 확인하지 못했다.

## Q3. 관측/평가 도구: 교차 고객 "태스크 X에서 이기는 모델" 집계를 공개하는가

### Takeaway
LangSmith, Langfuse, Helicone, Braintrust 등은 태스크 단위 트레이스와 점수를 이미 수집하지만, 집계는 **고객 계정 내부**에 한정된다. 교차 고객 품질 벤치마크를 공개한 사례는 찾지 못했다. 유일하게 교차 고객 공개 집계인 Helicone `/stats`도 **사용량**이지 품질이 아니며, Helicone은 Mintlify에 인수돼 유지보수 모드로 알려져 있다. 원격측정 표준(OpenTelemetry GenAI semconv)은 레코드 포맷의 기반으로 쓸 수 있다.

### Cited Findings
- Helicone `/stats`는 게이트웨이를 거친 트래픽 기준으로 실시간 모델 사용량 리더보드(토큰, 인기)를 보여 준다. 오픈소스 가격 DB는 300개 이상 모델을 다룬다 — [Helicone stats](https://www.helicone.ai/stats); [Helicone GitHub](https://github.com/helicone/helicone)
- PostHog에 따르면 Helicone은 Mintlify에 인수된 뒤 유지보수 모드로 운영된다 — [PostHog blog](https://posthog.com/blog/best-open-source-llm-observability-tools)
- Braintrust Monitor는 로그와 실험의 지연, 토큰, eval 점수를 집계하고 "Top lists"로 모델별 순위를 매길 수 있지만, 자기 데이터 안에서만 가능하다. 교차 고객 "state of evals" 보고서는 찾지 못했다 — [Braintrust](https://www.braintrust.dev/); [Braintrust how-to-eval](https://www.braintrust.dev/articles/how-to-eval)
- Langfuse는 데이터 소유권, self-hosting, API-first export를 강조한다. 교차 고객 벤치 공개는 찾지 못했다 — [Langfuse](https://langfuse.com/resources/engineering/best-braintrustdata-alternatives)
- OpenTelemetry GenAI semantic conventions(`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens` 등)로 agent run을 root span으로 기록하고 "run outcome"을 정의하는 관행이 있다 — [OpenTelemetry](https://opentelemetry.io/); [kunalganglani 2026-07 (2차)](https://www.kunalganglani.com/blog/opentelemetry-ai-agents-instrumentation)
- 코딩 에이전트 흔적(커밋 등)에는 어떤 모델을 썼는지가 대개 남지 않는다(Copilot 등). 예외적으로 Aider는 기록한다 — [arXiv 2601.18345](https://arxiv.org/pdf/2601.18345)

### Inferences
- 관측 도구 벤더는 "per-task trace + score"라는 원재료를 이미 쥐고 있지만, 고객 신뢰와 계약 때문에 풀링하지 않는다. 제안 프로젝트는 이들과 경쟁하기보다 **OTel GenAI 스팬에서 익명화한 요약 레코드를 opt-in으로 내보내는 exporter/플러그인**으로 붙는 편이 유통상 유리하다(Langfuse, Phoenix, OpenLLMetry 모두 OTel 호환).
- 모델 사용 흔적이 남지 않는다는 연구 결과는 "모델·방법 메타데이터를 표준화해 남기는 것" 자체에 가치가 있음을 보여 준다.

### Gaps
- LangSmith, Arize Phoenix, W&B Weave, OpenLLMetry(Traceloop)에 대해서는 교차 고객 집계 공개 여부를 개별 검색으로 확인하지 못했다. 위 3개 벤더 조사에 비춰 없을 것으로 추정하지만 검증되지 않았다.
- 이들 벤더 약관상 익명 집계 데이터를 쓸 권리를 보유하는지도 확인하지 못했다.

## Q4. 크라우드소싱된 "실사용 태스크별 모델 성능" 시도: 가장 가까운 사례와 성패

### Takeaway
가장 가까운 사례는 네 가지다. (1) **Inclusion Arena**(실제 앱 안에 쌍대 비교를 심어 넣음. 개념상 가장 근접하지만 2개 앱, 선호 투표 기반), (2) **Yupp.ai**(크레딧을 인센티브로 준 크라우드 선호 수집. $33M 조달 후 2026-03 폐업), (3) **OpenRouter** 사용량·지출 랭킹과 Auto Router, (4) **Anthropic Economic Index**(O*NET 태스크 단위 사용 데이터를 CC-BY로 공개. 단 단일 벤더·단일 모델군이고 모델 비교가 아님). "에이전트가 작업 후 결과 레코드를 자동 제출하는 공유 DB"는 찾지 못했다.

### Cited Findings
**Inclusion Arena** (Inclusion AI/Ant Group 계열, arXiv 2508.11452, 2025-08)
- 실제 앱의 사람-AI 다중턴 대화 중에 무작위로 모델 배틀을 발생시키고, Bradley-Terry에 Placement Matches와 Proximity Sampling을 더해 순위를 낸다 — [arXiv](https://arxiv.org/abs/2508.11452)
- 데이터 출처는 Joyland(롤플레이)와 T-Box(에이전트 플랫폼) 두 앱뿐이다. 비교 501,003건, 모델 49개, 사용자 46,611명이다. 코딩·교육 등 도메인별 서브 리더보드는 계획 단계다 — [arXiv](https://arxiv.org/abs/2508.11452); [VentureBeat](https://venturebeat.com/orchestration/stop-benchmarking-in-the-lab-inclusion-arena-shows-how-llms-perform-in-production)
- 2026-06 Neurocomputing 후속 논문(이론화)이 나왔다 — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S092523122601578X)

**Yupp.ai (실패 사례)**
- 사용자가 두 모델 답변 중 하나를 고르면 크레딧을 받고, Yupp은 그 선호 데이터를 AI 랩에 판매했다. VIBE Score 리더보드(Bradley-Terry + 지연·비용)를 운영했다. $33M 조달(a16z crypto의 Chris Dixon 리드) — [TechCrunch 2026-03-31](https://techcrunch.com/2026/03/31/yupp-ai-shuts-down-33m-a16z-crypto-chris-dixon/); [Yupp blog leaderboard](https://blog.yupp.ai/leaderboard/)
- 2026-03-31 폐업을 발표했고 2026-04-15 서비스를 종료했다. 창업자는 "didn't reach a strong enough product-market fit"라고 밝혔고, 모델 개선 속도와 "the future is not just models but agentic systems"를 이유로 들었다. 랩들은 Scale AI·Mercor처럼 전문가를 RL 루프에 투입하는 방식을 선호했다 — [TechCrunch](https://techcrunch.com/2026/03/31/yupp-ai-shuts-down-33m-a16z-crypto-chris-dixon/); [Prism News](https://www.prismnews.com/news/crowdsourced-ai-feedback-startup-yuppai-shuts-down-less)
- 최종 수치: 등록 사용자 100만 명 이상, 모델 900개 이상, 프롬프트 3,700만 건, 선호 데이터 3,000만 건 이상 — [Yupp.ai 작별 페이지](https://www.yupp.ai/)

**Anthropic Economic Index**
- 2026년 보고서: 01월 "Economic primitives"(과업 복잡도, 자율성, 성공 여부 등 5개 차원), 03월 "Learning curves"(Opus 4.5/4.6), 06-26 "Cadences"(chat, Cowork, Claude Code). 데이터는 CC-BY, 코드는 MIT이며 Hugging Face에 있다 — [HF dataset](https://huggingface.co/datasets/Anthropic/EconomicIndex); [Jan 2026](https://www.anthropic.com/research/anthropic-economic-index-january-2026-report); [Mar 2026](https://www.anthropic.com/research/economic-index-march-2026-report); [Jun 2026](https://www.anthropic.com/research/economic-index-june-2026-report)
- 대화를 O*NET 태스크에 매핑한다(2025-09 릴리스 기준 1,909,132개 질의, 17,659개 O*NET 태스크). Claude.ai에서 3,000개 이상의 고유 업무 태스크가 나타났다 — [arXiv 2607.15506](https://arxiv.org/pdf/2607.15506); [Jan 2026 report](https://www.anthropic.com/research/anthropic-economic-index-january-2026-report)
- "Open Source Economic Index"(arXiv 2606.26118)라는 독립 프로젝트도 있다 — [arXiv](https://arxiv.org/pdf/2606.26118)

**에이전트 대상 아레나와 벤치**
- BrowserArena: 사용자 태스크를 두 BrowserUse 에이전트(서로 다른 LLM)에 주고 투표를 받는다 — [arXiv 2510.02418](https://arxiv.org/html/2510.02418v2)
- TheAgentCompany: 부서별 실제 업무형 태스크로 구성되며 API 비용도 보고한다 — [NeurIPS 2025](https://papers.nips.cc/paper_files/paper/2025/file/0d744742f6fac4d1134c019b7cef3c8a-Paper-Datasets_and_Benchmarks_Track.pdf)
- HAL (Princeton Holistic Agent Leaderboard) — [GitHub](https://github.com/princeton-pli/hal-harness)
- SWE-Bench Mobile은 에이전트 도구 × 모델 22개 구성을 비교했다(최고 12%, Cursor + Opus/Sonnet 및 Codex + GLM) — [arXiv 2602.09540](https://arxiv.org/pdf/2602.09540)

### Inferences
- Yupp의 실패는 "사람 선호 데이터를 랩에 판매"하는 모델이 전문가 RL 데이터 시장에 밀렸고, 소비자 인센티브(크레딧)만으로는 지속되지 않았음을 보여 준다. 제안 프로젝트는 소비자 투표가 아니라 **에이전트/앱이 부산물로 자동 생성하는 레코드**라서 수집 비용 구조가 다르다. 대신 자기평가 품질의 신뢰성과 조작(스팸, 벤더의 자기 홍보)이 새로운 리스크가 된다.
- Inclusion Arena는 "실사용 앱 안에서 평가"라는 방향이 학술적으로 타당함을 보여 주지만, 참여 앱 2개(모회사 계열)에 머문다. 다수 독립 앱의 참여를 끌어낼 인센티브가 없다는 점이 제안 아이디어의 give-to-get이 메우려는 지점이다.
- Anthropic Economic Index는 "태스크 분류 체계(O*NET) + 성공 여부"를 대규모로 공개한 선례다. 분류 체계 설계(태스크 타입 스키마)의 참조 표준으로 쓸 수 있다.

### Gaps
- Anthropic Clio 자체, OpenAI의 "How people use ChatGPT"(2025) 사용 연구, Hugging Face 커뮤니티 evals에 대해서는 이번 세션에서 개별 검색으로 확인하지 못했다.
- "에이전트가 작업 완료 후 자동 제출하는 공유 결과 DB"는 검색으로 찾지 못했다. 존재하지 않는다는 증거가 아니라 발견하지 못했다는 의미다. GitHub, HN, Reddit을 추가로 탐색해야 한다.
- Inclusion Arena 라이브 리더보드의 2026년 운영 현황과 참여 앱 확대 여부는 미확인이다.

## Q5. 가장 방어 가능한 공백/차별점

### Takeaway
기존 생태계의 공백은 다음을 모두 만족하는 데이터셋이 없다는 것이다. (1) **실제 작업 결과(outcome) 신호**(선호 투표나 지출이 아닌 것), (2) **모델 + 방법/하네스 + 비용/지연의 결합 레코드**, (3) **미세한 태스크 스키마**, (4) **원시 수준의 개방 데이터(open commons)**, (5) **특정 벤더나 게이트웨이에 종속되지 않는 수집**. 가장 가까운 OpenRouter는 (1)과 (4)가 빠져 있고, Arena는 (1), (2), (4-실시간)이 빠져 있고, 관측 도구는 (4)가 빠져 있고, Inclusion Arena는 (2)와 (5)가 빠져 있다.

### Cited Findings (공백을 뒷받침하는 근거)
- OpenRouter 랭킹은 품질이 아니라 채택도를 측정한다 — [digitalapplied](https://www.digitalapplied.com/blog/openrouter-usage-charts-what-they-measure)
- Auto Router의 신호는 "aggregate spend"이고 원시 데이터 공개는 명시돼 있지 않다 — [OpenRouter docs](https://openrouter.ai/docs/guides/routing/routers/auto-router)
- 하네스 차이가 점수를 두 배 바꾼다(SWE-bench Verified 80.9% 대 SEAL 45.9%) — [Kili](https://kili-technology.com/blog/ai-benchmarks-guide-the-top-evaluations-in-2026-and-why-theyre-not-enough)
- 관측 도구의 집계는 계정 내부에 한정된다 — [Braintrust](https://www.braintrust.dev/)
- 에이전트 흔적에 모델 정보가 누락된다 — [arXiv 2601.18345](https://arxiv.org/pdf/2601.18345)
- 크라우드 선호 수집 사업의 실패 사례가 있다(Yupp) — [TechCrunch](https://techcrunch.com/2026/03/31/yupp-ai-shuts-down-33m-a16z-crypto-chris-dixon/)
- Arena 조작 가능성과 편향 비판이 있다 — [arXiv 2504.20879](https://arxiv.org/abs/2504.20879); [arXiv 2508.11452](https://arxiv.org/abs/2508.11452)

### Inferences
- **차별화 1 — 결과 신호**: 자기평가 품질만으로는 약하므로 검증 가능한 결과 신호(테스트 통과, 사용자 수락/수정 여부, 재시도 횟수, 롤백)를 우선 필드로 두고, 자기평가는 보조로 두어야 방어력이 생긴다.
- **차별화 2 — method/harness 1급 필드**: "모델 × 에이전트 하네스 × 프롬프트 전략" 조합 단위 랭킹은 현재 어느 공개 서비스도 제공하지 않는다.
- **차별화 3 — 개방성과 중립성**: CC-BY 계열 원시(익명화) 레코드 덤프, 오픈 스키마, 벤더 중립 거버넌스. Arena(유료 private eval)나 OpenRouter(게이트웨이 사업)와 이해상충 구조가 다르다.
- **차별화 4 — 유통**: OTel GenAI 스팬 → 익명 요약 레코드 exporter를 만들어 Langfuse, Phoenix, OpenLLMetry, LiteLLM 사용자가 한 줄로 기여하게 한다. 사용자 확보의 병목을 기존 도구에 올라타 해결하는 방식이다.
- **주요 리스크(방어 필요)**:
  - 콜드스타트와 희소성: RouteLLM에서 모델 쌍당 라벨이 0.1% 미만이었다. 해결책은 계층형 분류 체계와 백오프, 벤치 사전분포와의 결합이다.
  - 조작과 스팸: Arena 논란과 같은 구조. 서명된 제출, 기여자 평판, 이상치 탐지가 필요하다.
  - 자기평가 편향: LLM이 자기 결과를 과대평가할 수 있다.
  - 선택 편향: 기여자가 이미 좋은 모델을 쓰는 쪽으로 쏠린다.
  - 프라이버시: 태스크 설명의 유출 위험. 원문 대신 분류 라벨만 제출하게 한다.
  - OpenRouter가 task-spend 데이터를 확장하거나 품질 신호를 추가하면 격차가 빠르게 좁혀질 수 있다.
- give-to-get 자체는 Yupp의 크레딧 모델과 달리 "데이터로 데이터를 산다"는 구조라서 금전 인센티브가 필요 없다. 다만 질의 가치가 생기려면 임계 데이터량이 필요하다. 초기에는 공개 벤치(Epoch, AA, HELM의 오픈 데이터)와 OpenRouter CC BY 랭킹을 사전분포로 시드하는 방식이 현실적이다(추론이며 검증되지 않음).

### Gaps
- give-to-get 방식의 오픈 데이터 커먼즈가 AI 도메인에서 성공하거나 실패한 구체 사례(예: 오픈 텔레메트리 풀)는 이번 조사에서 찾지 못했다.
- 자기평가 품질 점수와 실제 결과의 상관에 관한 실증 자료는 조사하지 않았다.
