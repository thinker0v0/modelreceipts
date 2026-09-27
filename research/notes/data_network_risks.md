# Give-to-get 데이터 네트워크: 인센티브·어뷰징·프라이버시·거버넌스 리스크 (2026-09-27 기준)

조사 범위: AI 에이전트/앱이 태스크별 기록(태스크 유형, 모델, 방법, 자기평가 품질, 비용)을 공유 DB에 자동 제출하고, 제출자만 "어떤 모델/방법이 최선인가"를 조회할 수 있게 하는 오픈소스 give-to-get 구조의 타당성. 모든 날짜는 출처 기준이며, 조사일은 2026-09-27.

---

## Q1. 선례: give-to-get·기여형 데이터 네트워크는 무엇으로 성공/실패했나 (콜드스타트, 접근 게이팅, 기여율)

### Takeaway
성공한 선례(Glassdoor, Levels.fyi, Waze, OSM, Common Voice)는 공통적으로 (1) 데이터가 0일 때도 쓸모 있는 "시드 가치"로 콜드스타트를 넘었고, (2) 기여 비용이 매우 낮거나 기여가 사용의 부산물(수동적 텔레메트리)이었으며, (3) 게이트는 "기간 한정·쉬운 1회 기여"처럼 느슨했다. 반대로 Stack Overflow는 대체재(LLM)가 등장하자 기여가 급감했다. 이 프로젝트는 "자동 제출"이므로 기여 비용은 낮지만, 조회 가치가 OpenRouter 순위·LMArena·Artificial Analysis 같은 무료 대체재와 경쟁해야 하며 이것이 give-to-get 루프의 최대 약점이다.

### Cited Findings

**Glassdoor (명시적 give-to-get의 원형)**
- 회사 리뷰·연봉·면접·복리후생 중 하나를 기여하면 12개월 무제한 열람 권한을 주고, 기간 만료 시 재기여를 요구한다. 접근은 기여가 "게시된 후" 시작된다. 학생·장기 무직자는 잡 알림 설정이나 앱 로그인으로 예외 접근 가능 — [Glassdoor Help Center "Give-to-Get Policy"](https://help.glassdoor.com/s/article/Give-to-get-policy?language=en_US)
- Glassdoor 자체 연구(2017, 2013~2016년 리뷰 116,000건 이상): give-to-get이 극단적 1점 리뷰 확률을 3.6%p, 5점 리뷰 확률을 2.1%p 낮춰 평점 분포를 더 균형 있게 만들었다고 주장. 단, Glassdoor 자체 연구로 독립 검증 아님 — [Glassdoor blog](https://www.glassdoor.com/blog/give-to-get/); [PR Newswire](https://www.prnewswire.com/news-releases/new-study-reveals-glassdoor-give-to-get-policy-leads-to-more-balanced-company-ratings-300534547.html)
- 2025-11-18부터 신규 계정은 단일 로그인 필수·Indeed 계정 자동 생성. 2024년 정책 변경(실명 확인 관련)으로 익명성 우려가 제기됐고, 약관상 익명성은 보장 불가로 명시 — [Wikipedia: Glassdoor](https://en.wikipedia.org/wiki/Glassdoor)

**Levels.fyi (콜드스타트를 데이터 없는 유용성으로 해결)**
- 첫 버전은 연봉 데이터가 아니라 Google·Facebook·Amazon·Apple·Microsoft 엔지니어 레벨 대응표(정적 HTML)였고, 사용자 데이터 없이도 유용해 콜드스타트를 피했다. 이후 Google Forms/Sheets로 연봉 수집을 붙였다 — [Startup Founder Stories](https://startupfounderstories.com/stories/levels-fyi-zuhayeer-musa); [Levels.fyi 엔지니어링 블로그(Google Sheets 백엔드)](https://www.levels.fyi/blog/scaling-to-millions-with-google-sheets.html)
- 현재도 회사 페이지에서 "연봉을 추가해 페이지를 unlock"하도록 요구(소프트 give-to-get) — [Levels.fyi Google Salaries](https://www.levels.fyi/companies/google/salaries)
- 2021년 10만+ 연봉·1,500+ 도시, 월 100만+ 방문. 오퍼레터·급여명세서 등 증빙을 제출하는 "verified" 데이터 트랙 운영. 수익은 협상 코칭·이력서 리뷰(개인)와 보상 데이터 판매(기업) — [Levels.fyi 2021](https://levels.fyi/2021); [Levels.fyi Data offerings](https://www.levels.fyi/offerings/data/)
- 2026년 월 300만+ 사용자, 100만+ 개별 보상 데이터 포인트(제3자 요약, 공식 수치 원문 미확인) — [Levels.fyi End of Year Pay Report 2025](https://www.levels.fyi/2025/)

**Waze (기여 = 사용의 부산물, 지역 밀도 우선)**
- 2006 Freemap Israel 커뮤니티 프로젝트에서 출발, 지도 라이선스를 살 돈이 없어 크라우드소싱. 초기 사용자가 앱을 켜고 운전만 해도 도로가 "포장"되는 게이미피케이션(포인트)으로 닭-달걀 문제를 넘었고, 이스라엘 한 지역에 밀도를 먼저 채운 뒤 해외로 확장 — [HBS Digital Innovation: Waze](https://aiinstitute.hbs.edu/platform-digit/submission/waze-crowdsourcing-maps-and-traffic-information/); [Medium: Waze history](https://medium.com/@aviva.martin/waze-the-wild-ride-of-the-revolutionary-crowdsourcing-navigation-app-a4ce54f676a5)
- Google 인수(2013) 당시 5,000만 사용자. 인수가는 출처별로 약 11.5억~13억 달러로 상이 — [HBS Digital Innovation](https://d3.harvard.edu/platform-digit/?p=2906)

**Stack Overflow (대체재 등장 시 기여 붕괴)**
- 월 질문 수는 2014년 약 20만 건 정점 후 감소, ChatGPT(2022-11) 이후 가속. 2025년 5월 Pragmatic Engineer는 월 질문 수가 2009년 출범 수준이라고 보도 — [Pragmatic Engineer](https://blog.pragmaticengineer.com/stack-overflow-is-almost-dead/)
- 2025년 말~2026년 초 월 질문 수 수치는 출처마다 크게 다름(약 5만 미만 / 3,862 / 약 300 등). 쿼리 방식 차이로 보이며 정확한 값은 불확실. 방향성(급감)은 일치 — [Slashdot 2026-01-05](https://developers.slashdot.org/story/26/01/05/1431212/stack-overflow-went-from-200000-monthly-questions-to-nearly-zero); [Eric Holscher](https://www.ericholscher.com/blog/2025/jan/21/stack-overflows-decline/)
- AI 이전부터 공격적 모더레이션·질문 폐쇄가 신규 기여자를 쫓아냈다는 내부 논의도 존재. 반면 Graz 공대 연구는 ChatGPT 이후 남은 질문의 길이·난이도가 올라갔다고 보고 — [arXiv 2509.05879 "Stack Overflow Is Not Dead Yet"](https://arxiv.org/html/2509.05879v1)

**OpenStreetMap / Common Voice / Wikipedia (오픈 커먼즈)**
- Common Voice 23.0(2025-09-17): 총 35,921시간(검증 24,600시간), 286개 언어. CC0로 배포. 2022년 CV8 기준 기여 자원봉사자 20만+ — [Mozilla Foundation 블로그](https://www.mozillafoundation.org/en/blog/topic/common-voice/); [Wikipedia: Common Voice](https://en.wikipedia.org/wiki/Common_Voice)
- 일부 언어 커뮤니티가 CC0(무귀속·무조건)는 커뮤니티 통제가 없어 부적합하다고 문제 제기 → Mozilla가 데이터 소유자가 자기 조건을 정하는 "Mozilla Data Collective"를 만들고 신규 릴리스를 그쪽으로 배포 — [Mozilla Foundation](https://www.mozillafoundation.org/en/blog/topic/common-voice/); [Mozilla Data Collective CV 23.0](https://community.mozilladatacollective.com/common-voice-23-0-live-on-mozilla-data-collective/)

**텔레메트리 기반 집계 통계(수동적 기여)**
- OpenRouter + a16z "State of AI"(2025-12, arXiv 2601.10088): 100조 토큰 이상의 실사용 로그 메타데이터(프롬프트 내용이 아닌 익명화된 요청 수준 메타데이터)로 모델·용도 분석. OpenRouter는 개발자 500만+, 60+ 공급자의 300+ 모델을 라우팅하며 보고서 직전 주 1일 1조+ 토큰 처리 — [arXiv 2601.10088](https://arxiv.org/abs/2601.10088); [OpenRouter State of AI](https://openrouter.ai/state-of-ai); [a16z](https://a16z.com/state-of-ai/)
- 즉 "어떤 모델이 어떤 용도에 얼마나 쓰이는가"의 공개 순위는 이미 무료로 존재(단, 품질이 아니라 사용량 지표) — 위 동일 출처
- npm 다운로드 수는 IP·UA 무관하게 카운트되며, 미러·스캐너·봇 다운로드가 포함되어 인기 지표로 부정확 → 연구자들은 의존 패키지 수 등 대체 지표를 사용 — [arXiv 2204.04562](https://arxiv.org/pdf/2204.04562); [SpellBound arXiv 2003.03471](https://arxiv.org/pdf/2003.03471)

**크라우드소싱 벤치마크(LMArena)**
- 2023 UC Berkeley 연구 프로젝트 → 2025-04 독립 법인 → 2025-05 시드 1억 달러(밸류 6억) → 2026-01-06 시리즈A 1.5억 달러(밸류 17억). 2025-09 유료 "AI Evaluations" 출시 후 2025-12 연환산 소비 3,000만 달러. 월 500만+ 사용자, 월 6,000만 대화 주장 — [TechCrunch 2026-01-06](https://techcrunch.com/2026/01/06/lmarena-lands-1-7b-valuation-four-months-after-launching-its-product/); [SiliconANGLE](https://siliconangle.com/2026/01/06/ai-evaluation-startup-lmarena-raises-150m-1-7b-valuation/); [PR Newswire](https://www.prnewswire.com/news-releases/lmarena-raises-150-million-to-build-the-worlds-most-trusted-ai-evaluation-platform-302653012.html)
- LMArena는 투표 데이터를 무료 서비스(여러 모델 무료 사용)와 교환 — 사용자 입장에서 "쓰면서 기여"하는 구조(위 출처들의 서비스 설명에 기반)

### Inferences
- 이 프로젝트의 "기여"는 SDK 자동 제출이라 비용이 거의 0(Waze·Homebrew형)인데 "조회 권한"은 Glassdoor형 게이트다. 기여 비용이 0이면 게이트가 행동을 바꾸는 효과는 약하고, 대신 **무임승차보다 허위 제출(게이트 통과용 가짜 기록)이 주된 실패 모드**가 된다(Q2 참조).
- 콜드스타트: Levels.fyi처럼 데이터 0에서도 유용한 시드(예: 공개 벤치마크·가격표·OpenRouter 사용량·공개 리더보드를 태스크 분류 체계로 재정리한 큐레이션 뷰)를 먼저 제공하고, Waze처럼 좁은 태스크 영역(예: 코딩 에이전트의 특정 태스크군)에 밀도를 먼저 채우는 전략이 선례와 일치.
- 조회 가치가 무료 대체재(LMArena, OpenRouter rankings, 벤더 벤치마크)보다 확실히 높지 않으면 게이트는 사용자 이탈만 만든다. 차별점은 "태스크 세분도 + 비용 대비 품질 + 방법(프롬프트/에이전트 구성) 차원"이어야 한다.
- Stack Overflow 사례는 "기여 동기가 외부 대체재에 의해 소멸될 수 있음"을 보여준다. 에이전트 라우터 벤더(OpenRouter 등)가 유사 기능을 무료 제공하면 루프가 무너질 위험.
- Glassdoor의 12개월 갱신형 게이트는 "지속 기여"를 강제하는 간단한 메커니즘으로 참고 가치가 있으나, Glassdoor 자체 효과 연구는 이해상충이 있다.

### Gaps
- Glassdoor·Levels.fyi의 give-to-get 전환율(방문자 중 기여 비율) 공개 수치는 찾지 못함.
- "90-9-1 참여 불평등 규칙"이나 Wikipedia/OSM의 활성 기여자 비율에 대한 1차 출처는 이번 조사에서 확인하지 못함.
- Folding@home 크레딧 시스템, Hugging Face datasets, PyPI 통계의 구체적 인센티브/게이팅 데이터는 조사 시간 제약으로 확보하지 못함.
- Waze 현재 사용자·에디터 수(1.5억/50만)는 비공식 블로그 수치라 제외.

---

## Q2. 어뷰징: 리더보드 게이밍, Sybil, 가짜 제출과 방어책

### Takeaway
크라우드 평가 시스템은 **저비용으로 조작 가능**하다는 증거가 풍부하다: 수백 표로 Chatbot Arena 순위 조작 가능(시뮬레이션), 비공개 다변형 테스트 후 최고치만 공개하는 selective reporting, 벤더 맞춤 "실험" 모델 제출(Llama 4), 단일 서버 1,000개 가짜 Waze 기기, 노트북 한 대로 npm 다운로드 1시간 1.7만 건 부풀리기. 이 프로젝트는 자기평가 품질을 쓰므로 LLM 자기선호/과신 편향이 "악의 없는 오염"까지 더한다. 방어는 단일 기법이 아니라 계층형(서명된 SDK 텔레메트리 + 신원/평판 가중 + 이상탐지 + 교차 검증 가능한 객관 신호 + 투명한 제출/철회 로그)이어야 한다.

### Cited Findings

**벤더의 리더보드 게이밍**
- "The Leaderboard Illusion"(Singh 외, arXiv 2504.20879, NeurIPS 2025 포스터): 200만 배틀, 42개 공급자·243개 모델(2024-01~2025-04) 감사. 소수 선호 공급자(Meta, Google, OpenAI, Amazon)가 비공개로 여러 변형을 테스트하고 최고치만 공개하는 미공개 정책의 혜택을 받았고, Llama 4 출시 전 한 달에 최대 27개 Meta 비공개 변형 관측. best-of-N 선택 공개는 Bradley-Terry 가정을 깨 점수를 체계적으로 부풀림. 상위 2개 공급자가 전체 Arena 데이터의 19.2%, 20.4%를 받은 반면 83개 오픈웨이트 모델 합계 29.7%. Arena 데이터를 조금만 더 받아도 ArenaHard 상대 성능이 최대 112% 향상 → 과적합 유인 — [arXiv 2504.20879](https://arxiv.org/abs/2504.20879); [OpenReview](https://openreview.net/forum?id=4Ae8edNqm0)
- 권고: 점수 철회 금지, 비공개 변형 수 상한, 공급자 간 공정 샘플링, 삭제된 모델 전체 로그 공개 — [arXiv 2504.20879](https://arxiv.org/abs/2504.20879)
- LMArena 반박: 공식 통계상 오픈 모델 비중 40.9%이며 논문이 Llama·Gemma 등을 누락; "사전 테스트로 100점+ 상승" 그림은 가우시안 시뮬레이션일 뿐이며 신규 데이터가 계속 들어와 선택 편향은 빠르게 0으로 수렴한다고 주장 — [LMArena "Our Response"](https://lmarena.ai/blog/our-response/). (공급자 식별이 모델 자기소개에 의존한다는 점은 논문도 인정하는 약점 — [Pith Review](https://pith.science/paper/2504.20879))
- Llama 4 Maverick(2025-04): "Llama-4-Maverick-03-26-Experimental"가 Elo 1417로 2위, 공개 HF 버전은 추가 후 32위. LMArena는 "Meta의 정책 해석이 우리 기대와 달랐다"며 정책 강화 및 배틀 2,000+건 공개 — [The Register](https://www.theregister.com/2025/04/08/meta_llama4_cheating/); [Simon Willison 인용](https://simonwillison.net/2025/Apr/8/lmaren/); [Digital Watch](https://dig.watch/updates/lmarena-tightens-rules-after-llama-4-incident)
- 2026-01 Yann LeCun이 FT 인터뷰에서 "결과가 약간 조작(fudged)됐다"고 발언(2차 보도) — [IRONHACKERS 정리](https://ironhackers.es/en/llama-4-controversia-lmarena/)

**투표 조작 연구**
- "Improving Your Model Ranking on Chatbot Arena by Vote Rigging"(Min 외, Sea AI Lab, ICML 2025): 대상 모델만 노리는 방식은 비효율(새 배틀 중 약 1%만 대상 포함)이지만, 모든 새 투표를 조작하는 "omnipresent" 전략은 과거 170만 투표 데이터 시뮬레이션에서 **수백 표**만으로 순위를 올릴 수 있었음. 라이브 사이트에서는 실험하지 않음 — [arXiv 2501.17858](https://arxiv.org/abs/2501.17858); [Fast Company](https://www.fastcompany.com/91273226/rigged-votes-ai-model-rankings-chatbot-arena)
- Huang 외(arXiv 2501.07493): 응답 비익명화 후 표적 투표 공격을 보이고 방어책을 Arena 팀과 공동 개발 — [arXiv 2501.07493](https://arxiv.org/pdf/2501.07493)
- Arena 기존 방어: 악성 사용자 탐지, reCAPTCHA v3, IP당 투표 제한, 프롬프트 중복 제거 — [arXiv 2504.20879](https://arxiv.org/pdf/2504.20879)

**Sybil / 가짜 기기·가짜 통계**
- UCSB "Ghost Riders"(MobiSys 2016 / ToN 2018): 위치 검증이 약한 Waze에서 소프트웨어 가짜 기기 1,000대를 Linux 서버 1대(메모리 11%, CPU 2%, 420Kbps)로 운용해 가짜 정체·사고 신고, 실사용자 추적 가능. 제안 방어는 "co-location edge"(물리적 동시 위치 인증 기록) 그래프에서 커뮤니티 탐지 — [UCSB MobiSys16 PDF](https://sites.cs.ucsb.edu/~ravenben/publications/pdf/waze-mobisys16.pdf); [ToN 2018 PDF](https://people.cs.uchicago.edu/~ravenben/publications/pdf/waze-ton18.pdf). Waze는 보도에 "심각한 오해"가 있다고 반박 — [Engadget](https://www.engadget.com/2016-04-26-waze-tracking-exploit.html)
- 2014 Technion: 평판 높은 봇 드라이버로 가짜 정체 생성 — [Daily Nexus](https://dailynexus.com/2016-04-28/ways-into-waze-researchers-find-method-to-hack-app/)
- npm "download pumping"(Tenable, 2026-05): 악성 패키지 'ambar-src'가 700+ 버전 업로드로 미러·스캐너 자동 다운로드를 유발해 3일 만에 5만+ 다운로드. 타볼 URL 직접 요청만으로 노트북 1대로 1시간에 1.7만 다운로드 — [Tenable](https://www.tenable.com/blog/how-cyberattackers-inflate-malicious-package-npm-download-counts); [ReversingLabs](https://www.reversinglabs.com/blog/download-pumping-trust-abuse). 2021년 개인 개발자가 1주일에 약 100만 가짜 다운로드 시연 — [DEV Community](https://dev.to/andyrichardsonn/how-i-exploited-npm-downloads-and-why-you-shouldn-t-trust-them-4bme)

**데이터 포이즈닝 규모**
- Anthropic·UK AISI·Alan Turing Institute(2025-10-09): 600M~13B 모델 모두 약 250개 악성 문서로 백도어 가능 — 공격에 필요한 양이 비율이 아니라 거의 상수. 단, 무의미한 출력을 유도하는 좁은 백도어만 시험 — [Anthropic](https://www.anthropic.com/research/small-samples-poison); [arXiv 2510.07192](https://arxiv.org/pdf/2510.07192)

**자기평가 품질 신호의 구조적 편향(비악의적 오염)**
- LLM 평가자는 자기 출력을 인식하고 선호(Panickssery 외, NeurIPS 2024); 자기선호는 낮은 perplexity(친숙한 텍스트) 선호로 설명되기도 함(Wataoka 외 2024) — [MATS](https://www.matsprogram.org/research/llm-evaluators-recognize-and-favor-their-own-generations); [arXiv 2410.21819](https://arxiv.org/abs/2410.21819)
- LLM 판정자 과신: DeepSeek-R1-0528, GPT-4o 등이 90~100% 신뢰도에 몰리지만 실제 정확도는 훨씬 낮음 — [arXiv 2508.06225](https://arxiv.org/html/2508.06225v2)
- 에이전트가 작업 후 자기 결과를 평가할 때가 사전 예측보다 보정이 더 나쁨 — [arXiv 2602.06948 "Agentic Uncertainty Reveals Agentic Overconfidence"](https://arxiv.org/pdf/2602.06948)

**"모델 ID" 자체의 불확실성**
- IB2/IBIB 프로토콜(arXiv 2609.10494, 2026-09-09): 감사한 벤치마크 18개 모두 "광고된 모델 식별자"를 채점하지만 실제 능력은 서빙 경로·정밀도·하니스에 좌우. 동일 가중치의 서로 다른 서빙 arm이 77.38→82.54로 차이 — [arXiv 2609.10494](https://arxiv.org/abs/2609.10494)

### Inferences
- 이 설계에서 가장 위험한 공격자는 (a) 자사 모델을 "최적"으로 보이게 하려는 벤더/팬, (b) 조회 권한만 얻으려는 무임승차자의 저품질 자동 제출, (c) 특정 방법/도구를 홍보하려는 에이전트 프레임워크 제작자. Arena 사례에서 수백 건 수준의 조작이 순위를 바꿀 수 있었으므로, 희소한 태스크 셀(롱테일)은 수십 건으로도 뒤집힐 수 있다.
- 자기평가 품질은 편향이 체계적(자기선호·과신)이므로 평균으로 상쇄되지 않는다. 가중치는 객관 신호(테스트 통과, 사용자 수락/되돌리기, 재시도 횟수, 비용·지연 같은 계측값)에 두고 자기평가는 보조로만 써야 한다. 평가 모델과 수행 모델을 다른 계열로 분리하는 것이 문헌 권고와 일치.
- 방어 계층 제안(선례 기반): SDK 서명 + 설치 인스턴스 키(단, 오픈소스 SDK는 키 추출 가능하므로 attestation은 "비용 올리기" 수준), 계정/조직 단위 기여 상한과 per-cell 기여 비율 상한, 신규 계정의 가중치 워밍업, 공급자 API 응답 헤더(요청 ID·모델 버전·토큰 사용량) 같은 제3자 검증 가능 필드, 분포 이상탐지(동일 조직이 특정 모델에 편향된 점수), Leaderboard Illusion 권고처럼 제출 철회 금지 및 공개 변경 로그, 벤더 소속 기여자 자기신고와 별도 표시.
- 서빙 경로(공급자/양자화/라우터)를 기록하지 않으면 "같은 모델명"의 기록이 섞여 결론이 오염된다 → 스키마에 provider/route/버전/날짜 필수.

### Gaps
- 텔레메트리 기반 AI 성능 DB에 대한 실제 Sybil 공격 사례는 찾지 못함(대부분 Arena 시뮬레이션·Waze·npm 유추).
- LMArena가 Llama 4 이후 구체적으로 어떤 정책 문구를 바꿨는지 원문 확인 못함.
- SDK attestation(예: 앱 무결성 API, TPM)이 오픈소스 클라이언트에서 얼마나 효과적인지에 대한 정량 연구는 미확보.

---

## Q3. 프라이버시·법적 리스크: 프롬프트/PII/사내 코드 유출, 기법, GDPR·PIPA, 공급자 ToS

### Takeaway
"태스크 유형" 필드는 자유 텍스트로 두면 프롬프트·고객명·코드 조각이 새어 나오는 통로가 된다. Anthropic Clio식 "로컬 요약 → 폐쇄형 분류 → 최소 계정/대화 수 임계값 → 감사" 계층 설계와 Homebrew/VS Code식 명확한 opt-out(가능하면 opt-in) 텔레메트리가 사실상의 표준이다. 법적으로는 GDPR/PIPA상 "익명정보"로 인정받기 어려우므로(가명정보로 취급될 가능성) 식별자·조직 정보 최소화가 필요하다. 공급자 ToS는 대체로 "경쟁 모델 개발" 금지 중심이며 공개 벤치마크 자체를 명시 금지하진 않지만, Google Cloud는 벤치마크 공개에 재현 정보·상호 벤치마크 허용 조건을 붙이고, Anthropic은 경쟁사 벤치마킹을 이유로 접근을 차단한 전례가 있다.

### Cited Findings

**Clio(프라이버시 보존 사용 분석)의 설계**
- 4개 계층: (1) 모델이 사적 정보 제외하고 대화 요약, (2) 클러스터는 고유 계정 수와 대화 수 **양쪽 모두** 최소 크기를 넘을 때만 유지, (3) 클러스터 요약 생성 시 사적 정보 배제, (4) 감사 모델이 사적 정보 포함 클러스터 제거. 5,000개 대화 감사에서 사적 데이터 포함 클러스터 0건 — [arXiv 2412.13678](https://arxiv.org/html/2412.13678v1); [Anthropic Clio](https://www.anthropic.com/research/clio)
- 구체적 임계값 수치는 공개 논문 본문 발췌에서 확인되지 않음. "약 1,000명 미만을 식별할 수 있는 정보"를 제거한다는 기준은 2차 출처(ZenML)에만 있음 — [ZenML](https://www.zenml.io/llmops-database/building-a-privacy-preserving-llm-usage-analytics-system-clio). 논문은 "100명 마을, 15명 회사" 같은 소집단 식별도 사적 정보로 간주 — [arXiv 2412.13678](https://arxiv.org/html/2412.13678v1)
- 한계: 차등프라이버시 같은 형식적 보장을 적용하기 어렵다고 명시; 단계 간 실패가 상관될 수 있음; 개인이 아닌 **집단 프라이버시** 침해 가능성; 지리 기반 분석은 지원하지 않음 — [arXiv 2412.13678](https://arxiv.org/html/2412.13678v1); [Provectus](https://provectus.com/blog/differential-privacy-for-llm-pipelines-lessons-from-anthropics-clio/)

**오픈소스 텔레메트리 규범**
- Homebrew: 기본 활성(opt-out), 최초 이벤트 전 고지, `brew analytics off` 또는 `HOMEBREW_NO_ANALYTICS=1`. 명령·옵션 이름만 기록하고 옵션 값은 제거. InfluxDB에 365일 보관, 공개 집계(JSON)만 대부분 메인테이너에게 노출 — [Homebrew Docs: Anonymous Analytics](https://docs.brew.sh/Analytics). 기본 활성에 대한 비판 존재 — [OS X Daily](https://osxdaily.com/2023/06/25/how-to-opt-out-disable-homebrew-analytics/)
- VS Code: `telemetry.telemetryLevel` = all(기본)/error/crash/off 단일 설정, 기업 정책(GPO) 지원, 일부 서드파티 확장은 설정을 무시할 수 있음. 2026-07 워크스페이스 단위 오버라이드 요청 이슈(#323825) — [VS Code Telemetry](https://code.visualstudio.com/docs/configure/telemetry); [Enterprise telemetry](https://code.visualstudio.com/docs/enterprise/telemetry); [GitHub #323825](https://github.com/microsoft/vscode/issues/323825)
- OpenRouter 연구 데이터는 프롬프트 내용이 아닌 익명화된 요청 메타데이터 기반 — [arXiv 2601.10088](https://arxiv.org/html/2601.10088v1)

**GDPR (EU)**
- EDPB Opinion 28/2024(2024-12-17): AI 모델 익명성은 사례별 판단; 직접(확률적 포함) 추출 가능성과 질의를 통한 획득 가능성 모두 "무시할 수준"이어야 익명으로 인정. 높은 기준 — [EDPB Opinion 28/2024 PDF](https://www.edpb.europa.eu/system/files/2024-12/edpb_opinion_202428_ai-models_en.pdf); [IAPP](https://iapp.org/news/a/edpb-weighs-in-on-key-questions-on-personal-data-in-ai-models)
- GDPR은 익명정보에는 적용되지 않고 개인정보에만 적용 — [Securiti 요약](https://securiti.ai/summary-of-edpb-opinion-282024-concerning-ai-models-processing-of-personal-data/)

**한국 PIPA**
- 개인정보보호법 제28조의2: 통계작성·과학적 연구·공익적 기록보존 목적이면 동의 없이 가명정보 처리 가능. 제58조의2: 시간·비용·기술을 합리적으로 고려해 다른 정보를 사용해도 개인을 알아볼 수 없는 정보(익명정보)엔 법 적용 제외 — [개인정보위 「생성형 AI 개발·활용을 위한 개인정보 처리 안내서」 2025-08](https://www.pipc.go.kr/np/cop/bbs/selectBoardArticle.do?bbsId=BS074&mCode=C020010000&nttId=11410); [PDF](https://smartcity.go.kr/wp-content/uploads/2025/09/%EB%B3%84%EC%B2%A82-%EC%83%9D%EC%84%B1%ED%98%95-%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5AI-%EA%B0%9C%EB%B0%9C%C2%B7%ED%99%9C%EC%9A%A9%EC%9D%84-%EC%9C%84%ED%95%9C-%EA%B0%9C%EC%9D%B8%EC%A0%95%EB%B3%B4-%EC%B2%98%EB%A6%AC-%EC%95%88%EB%82%B4%EC%84%9C.pdf)
- 안내서(2025-08-06 공개, 11-24 책자판)는 AI 수명주기 4단계(목적 설정/전략 수립/학습·개발/시스템 적용·관리)별 고려사항과 AI 프라이버시 거버넌스를 제시. 비정형데이터(챗봇 등) 가명처리 가이드라인도 개정되어 가명처리 적정성 근거 작성·보관 및 자체 검수를 요구 — [대한민국 정책브리핑](https://www.korea.kr/news/policyNewsView.do?newsId=148946215); [개인정보 포털](https://www.privacy.go.kr/front/bbs/bbsView.do?bbsNo=BBSMSTR_000000000049&bbscttNo=20836)

**AI 공급자 ToS: 경쟁 모델 개발·벤치마크 공개**
- OpenAI 소비자 약관: "Output을 OpenAI와 경쟁하는 모델 개발에 사용" 금지. 비즈니스 Services Agreement는 "Permitted Exception"을 제외하고 경쟁 AI 모델 개발에 Output 사용 금지. 벤치마크 결과 공개에 대한 명시 조항은 조사한 약관에서 확인되지 않음 — [OpenAI Terms of Use](https://openai.com/policies/row-terms-of-use/); [OpenAI Services Agreement](https://openai.com/policies/services-agreement/)
- Anthropic Commercial Terms D.4: 경쟁 제품/서비스 구축(경쟁 AI 모델 학습 포함)을 위한 접근, 리버스엔지니어링·복제, 승인 없는 재판매 금지. 벤치마킹 명시 조항은 없음 — [Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms)
- 그러나 집행 사례: 2025-08 Anthropic이 OpenAI의 Claude API 접근을 차단(Wired 보도: 자사 모델 벤치마킹·안전성 비교에 사용), 2025-06 Windsurf, 2026-01 Cursor 경유 xAI 차단 — [VentureBeat](https://venturebeat.com/technology/anthropic-cracks-down-on-unauthorized-claude-usage-by-third-party-harnesses); [AlternativeTo](https://alternativeto.net/news/2025/8/anthropic-abruptly-revokes-openai-s-access-to-claude-api-over-terms-of-service-violation)
- Gemini API Additional Terms(2026-03-23 시행): "Services로 Services와 경쟁하는 모델 개발 금지", 리버스엔지니어링·가중치 추출 금지 — [Gemini API Terms](https://ai.google.dev/gemini-api/terms)
- Google Cloud General Service Terms §7 Benchmarking(원문): 고객은 스스로(제3자 허용 불가) 벤치마크 테스트 가능, 결과 공개는 (i) 재현에 필요한 모든 정보 포함, (ii) Google이 고객의 공개 제품을 벤치마크·공개하는 것을 허용할 때만. 하이퍼스케일 퍼블릭 클라우드 사업자를 위한 테스트/공개는 사전 서면 동의 필요 — [Google Cloud Service Terms](https://cloud.google.com/terms/service-terms)
- 2026-09 Gemini API 오프라인 벤치마크 결과를 공개 사이트에 게시해도 되는지 묻는 개발자 포럼 질문에 공식 답변 확인 안 됨 — [Google AI Developers Forum](https://discuss.ai.google.dev/t/terms-clarification-offline-gemini-api-benchmarking-for-a-public-consumer-website/183994)

### Inferences
- 제출 스키마는 자유 텍스트 태스크 설명을 금지하고, 로컬(클라이언트)에서 사전 정의된 폐쇄형 분류 체계 코드로 변환한 뒤 업로드해야 한다(Clio의 "요약 후 집계"를 클라이언트 측으로 당긴 형태). 원문 프롬프트·파일 경로·레포명·고객명은 절대 전송하지 않음.
- 조회 결과는 Clio처럼 "고유 기여자 수 k 이상 & 기록 수 n 이상"인 셀만 노출(k-anonymity형 임계값). 롱테일 태스크 셀은 비노출 또는 상위 카테고리로 롤업. 조직 단위 집단 프라이버시(특정 회사의 모델 선택이 드러나는 것)도 영업비밀 리스크이므로 조직 식별자는 가중치 계산에만 쓰고 공개하지 않는 설계가 필요.
- 기여 인센티브(조회 권한)는 계정 식별을 요구하므로 완전 익명과 give-to-get 게이팅은 긴장 관계. 기여 증명은 익명 토큰(예: 기여 시 발급되는 블라인드 토큰)으로 분리하는 방안을 검토할 수 있으나 이는 설계 제안이지 검증된 선례는 아님.
- ToS 측면: 개별 사용자가 자기 사용 기록(비용·자기평가 품질)을 집계 DB에 제출하는 것은 "경쟁 모델 개발"에 해당하지 않을 가능성이 높지만, (a) DB를 라우터/증류 학습 데이터로 쓰는 경우, (b) 경쟁 AI 기업이 기여자인 경우, (c) Google Cloud 경유 호출 결과를 공개하는 경우 조건 충족(재현정보·상호 벤치마크 허용) 문제가 생길 수 있음. 출력 텍스트 자체는 수집하지 않는 것이 리스크를 크게 줄인다. 법률 자문 필요.
- 기본값: VS Code/Homebrew는 opt-out 기본이지만 비판이 있고 EU/한국 법제 및 기업 사용자 신뢰를 고려하면 이 프로젝트는 opt-in(명시적 활성화)이 안전. 기업용 정책 스위치(조직 단위 전체 끄기) 제공.

### Gaps
- Clio의 실제 최소 계정/대화 임계값 숫자는 공개 자료에서 확인 불가.
- OpenAI "Permitted Exception" 정의, Anthropic Consumer Terms의 벤치마크 관련 문구 전문은 확인하지 못함.
- 한 2026-09 arXiv 논문이 "여러 공급자 약관이 벤치마킹을 제한"하며 한 공급자("Provider P")는 명시 금지한다고 했다는 검색 요약이 있었으나, 해당 arXiv 초록 페이지(2609.10494)에서는 이 내용을 확인하지 못함 → 미검증으로 제외.
- 태스크 메타데이터(분류 코드+비용+모델명)가 GDPR/PIPA상 개인정보에 해당하는지에 대한 직접적 규제 해석은 찾지 못함(계정 ID와 결합 시 가명정보로 볼 가능성이 높다는 것은 추론).
- 차등프라이버시를 실제 텔레메트리 집계에 적용한 오픈소스 사례(예: Apple/Google의 로컬 DP)는 이번 조사에서 확보하지 못함.

---

## Q4. 거버넌스·지속가능성: 데이터 라이선스, 재단 vs 회사, 자금 조달, 벤더 포획

### Takeaway
오픈 데이터 커먼즈는 대개 소규모·적자 경향(OSMF 연 약 48만 파운드 예산, 2025 "큰 손실" 경고)이며, 기업 회원제·유료 고성능 API(Wikimedia Enterprise)·데이터 판매(Levels.fyi)·평가 서비스(LMArena)로 자금을 댄다. 반면 LMArena처럼 VC 자본으로 상업화하면 성장은 빠르지만 "평가 대상 벤더가 곧 고객"이 되는 중립성 문제가 생긴다. 라이선스는 ODbL(share-alike로 개선분 개방 강제) vs CDLA-Permissive-2.0/CC-BY 4.0(결합 용이, 계산 결과 무제한) 사이의 선택이며, give-to-get 게이팅은 사실 "완전 공개 라이선스"와 충돌하므로 원시 데이터 공개 정책을 먼저 정해야 한다.

### Cited Findings

**라이선스**
- ODbL: 데이터베이스 전용 copyleft. 수정 DB를 공개 사용하면 ODbL로 제공해야 함; "Produced Works"(예: 지도)는 출처 표시만 요구; DRM 배포 시 비제한 버전도 제공해야 함. 단 share-alike 리스크 때문에 타 조직이 사용을 꺼릴 수 있음 — [CASRAI](https://casrai.org/dictionary/term/open-database-license-odbl); [data.world](https://docs.data.world/en/214274-common-license-types-for-datasets.html)
- CDLA-Permissive-2.0: MIT 유사, 유일한 의무는 라이선스 문구 동봉. 데이터 계산적 사용 결과(ML 모델 출력 등)에 의무·제한 없음을 명시 — [data.world](https://data.world/license-help); [openmod wiki](https://wiki.openmod-initiative.org/wiki/Choosing_a_license)
- CC-BY 4.0: 데이터용으로는 4.0 버전만 권장, CC-BY-SA는 데이터에 비권장 — [openmod wiki](https://wiki.openmod-initiative.org/wiki/Choosing_a_license)
- OSMF 검토: CDLA Permissive(1.0)는 대체로 ODbL과 호환, CDLA Sharing은 비호환 — [OSMF CDLA permissive compatibility](https://osmfoundation.org/wiki/CDLA_permissive_compatibility)
- 미국에서는 사실 자체는 저작권 보호 대상이 아니며 DB는 편집물로서 선택·배열만 제한적으로 보호 — [ODI licence compatibility guide](https://github.com/theodi/open-data-licensing/blob/master/guides/licence-compatibility.md)
- Common Voice는 CC0로 시작했으나 커뮤니티 통제 요구로 Mozilla Data Collective(소유자가 조건 설정)로 이동 — [Mozilla Foundation](https://www.mozillafoundation.org/en/blog/topic/common-voice/)

**재단형 자금 조달**
- OSMF: 2025년 예산 수입 약 48.2만 파운드, 지출이 소폭 초과 예상(적립금으로 감당); 재무 보고서는 "올해 큰 손실, 경계해야 한다"고 경고. 개발 지출이 약 4만→9만 파운드로 증가(벡터 타일 등, 기업 회원의 일회성 대규모 기금으로 충당). 수입원: 개인·기업 회원비, State of the Map 수익, 기부 — [OSMF Board Minutes 2025-05](https://osmfoundation.org/wiki/Board/Minutes/2025-05); [OSMF 2025 Treasurer's report](https://osmfoundation.org/wiki/Annual_General_Meetings/2025/Treasurer's_report)
- OSMF 기업 회원은 연 750유로부터, 2023년 요금 50% 인상 및 Bronze 이상 자문위원회 참여권; Microsoft 2023-10 15만 달러 기부로 Platinum — [OSMF Corporate Members](https://osmfoundation.org/wiki/Corporate_Members); [OSM blog](https://blog.openstreetmap.org/2023/10/25/microsoft-pledges-150k-to-support-openstreetmap/)
- Wikimedia Enterprise: FY2024-25 수익 830만 달러(전년 340만 대비 +148%), WMF 총수입의 4.0%, 상업 고객 13곳. 전략은 "라이선스 기반이 아닌 접근(access) 기반"; Enterprise 수입은 총수입의 30%를 넘지 못하도록 상한(독립성 유지) — [Wikimedia Diff 2025-11-24](https://diff.wikimedia.org/2025/11/24/wikimedia-enterprise-financial-report-fiscal-year-2024-2025/); [WMF 2026-07-16](https://wikimediafoundation.org/news/2026/07/16/wikimedia-enterprise-protecting-wikipedia-ai/)
- WMF는 2025-11 AI 기업에 스크래핑 대신 유료 API 사용을 촉구; 신원 위장·주거용 프록시로 스크래핑하는 행위자가 여전히 인프라를 압박(2026-07) — [TechCrunch 2025-11-10](https://techcrunch.com/2025/11/10/wikipedia-urges-ai-companies-to-use-its-paid-api-and-stop-scraping/); [WMF 2026-07](https://wikimediafoundation.org/news/2026/07/16/wikimedia-enterprise-protecting-wikipedia-ai/)
- Common Voice 후원(2022 기준): Gates Foundation, GIZ, NVIDIA, 영국 FCDO — [Wikipedia: Common Voice](https://en.wikipedia.org/wiki/Common_Voice)

**회사형(상업화) 모델과 벤더 포획**
- LMArena: 학술 프로젝트 → VC 투자 회사(총 2.5억 달러 조달, 밸류 17억). 주요 수익은 기업·AI 랩·개발자가 비용을 내는 평가 서비스 — [TechCrunch](https://techcrunch.com/2026/01/06/lmarena-lands-1-7b-valuation-four-months-after-launching-its-product/)
- 평가 대상인 벤더가 곧 유료 고객이 되는 구조에서 LMArena가 중립성과 독립성을 계속 입증해야 한다는 논평; Leaderboard Illusion은 대형 벤더 우대(비공개 테스트, 샘플링 비중)를 지적 — [SiliconANGLE](https://siliconangle.com/2026/01/06/ai-evaluation-startup-lmarena-raises-150m-1-7b-valuation/); [arXiv 2504.20879](https://arxiv.org/abs/2504.20879)
- OpenRouter 사용 데이터 연구는 a16z(투자사)와 공동 발표 — 데이터 보유자가 상업적 이해관계자인 사례 — [a16z](https://a16z.com/state-of-ai/)
- Levels.fyi: 데이터는 무료 조회(기여 유도)하되 기업에 보상 데이터 판매, 개인에 협상 서비스 판매 — [Levels.fyi Data](https://www.levels.fyi/offerings/data/)

### Inferences
- 라이선스 선택은 게이팅 모델과 함께 결정해야 한다. give-to-get은 "원시 데이터 비공개 + 집계 조회만 게이트"를 전제로 하는데, 원시 데이터를 ODbL/CC-BY로 공개하면 누구나 덤프를 받아 게이트 없이 조회 서비스를 재구축할 수 있다. 현실적 조합: 집계 통계(k-임계값 통과분)는 CC-BY 4.0 또는 CDLA-Permissive-2.0로 주기적 공개, 레코드 단위 원시 데이터는 프라이버시상 비공개, 실시간/세분 조회만 기여자 전용(Wikimedia Enterprise식 "라이선스가 아닌 접근 기반" 차등).
- ODbL은 경쟁 라우터·벤더가 개선분을 닫아두는 것을 막는 장점이 있으나 기업 채택을 억제한다(data.world 지적). 벤더 포획을 막는 목적이라면 라이선스보다 거버넌스(수입원 상한, 벤더 기여자 표시, 방법론·정책 공개)가 더 직접적이다.
- 벤더 포획 방지 장치 후보(선례 기반): Wikimedia식 단일 수입원 비중 상한, OSMF식 기업 회원 자문위(의결권 없는), LMArena 논란에서 도출된 "벤더 사전 테스트/철회 금지·전체 제출 로그 공개", 벤더 소속 기여 데이터의 분리 표시 또는 가중치 제한.
- 자금: 재단형은 운영비 수십만 달러 규모에서도 적자 위험(OSMF). 초기에는 경량 인프라(Levels.fyi가 Google Sheets로 수백만 사용자까지 버틴 사례)로 비용을 낮추고, 이후 기업용 대량 API/SLA 판매가 가장 검증된 경로.

### Gaps
- Common Crawl의 재정·후원 구조에 대한 최신(2025~2026) 1차 자료는 이번 조사에서 확보하지 못함.
- Hugging Face datasets의 기여 인센티브·거버넌스 구체 데이터는 조사하지 못함.
- LMArena의 2026년 이후 재단/회사 거버넌스 변화(Wikipedia가 "Arena (AI platform)"으로 표기 — 리브랜딩 여부)는 확인되지 않음 — [Wikipedia: Arena (AI platform)](https://en.wikipedia.org/wiki/Arena_(AI_platform))
- 오픈소스 AI 평가 커먼즈가 재단 형태(Linux Foundation/LF AI & Data 산하 등)로 운영되는 구체 선례는 찾지 못함.
