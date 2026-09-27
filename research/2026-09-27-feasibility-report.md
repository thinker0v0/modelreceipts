# 자기평가 말고 결과 증거로 모델 DB를 세워라

**결론: 조건부로 타당하다.** 2026년 9월 기준 공개 리더보드, 라우터, 관측 도구 중 **실제 작업의 결과 신호, 모델과 방법(하네스), 비용을 한 레코드로 묶어 벤더 중립적인 오픈 데이터로 쌓는 곳은 없다.** 그래서 이 프로젝트가 노리는 빈틈은 실재한다. 다만 원안 그대로는 세 곳이 무너진다. 첫째, 핵심 품질 신호인 "AI 자체평가"는 믿을 수 없다. 2026년 연구에서 에이전트는 실패한 작업의 13~89%를 성공이라고 보고했고, 과신 정도가 모델마다 달라서 모델 간 비교를 체계적으로 왜곡한다. 둘째, 기여가 자동이라 비용이 0에 가깝기 때문에 give-to-get 게이트는 무임승차를 막는 효과가 약하다. 오히려 게이트를 통과하려는 가짜 제출과 벤더의 순위 조작이 주된 실패 모드가 된다. 셋째, "원시 데이터를 오픈"하면 누구나 덤프를 받아 게이트 없이 같은 조회 서비스를 만들 수 있으므로, give-to-get과 완전 개방은 서로 부딪친다. 따라서 권고는 방향 전환이다. **자기평가 대신 검증 가능한 결과 증거(테스트 통과, 커밋 유지, 재시도·되돌리기)를 1급 필드로 두고, 수집은 Claude Code `Stop` 훅 하나에서 코딩 태스크만으로 좁게 시작한다. 콜드스타트는 라이선스가 깨끗한 공개 데이터(Aider 리더보드, Arena 선호 데이터, OpenRouter CC BY 랭킹)로 넘기고, 게이트는 "공개 개요 + 기여자 전용 세분 조회" 형태로 느슨하게 둔다.** 이렇게 좁히면 20% MVP는 해커톤 포트폴리오로 충분히 설득력 있고, 실제 서비스로 이어질 발판도 된다. 다만 OpenRouter가 이미 태스크별 추천의 "조회" 쪽을 제품화했으므로 차별점을 결과 신호와 방법 차원에 두지 않으면 방어할 수 없다.

## 판정: 빈틈은 실재하지만 원안의 세 기둥은 교체가 필요하다

타당성은 차원마다 다르다. **시장 공백은 "예"다.** 네 개의 연구 노트가 각자 다른 경로로 조사했지만 "에이전트가 작업을 끝낸 뒤 결과 레코드를 자동 제출하는 공유 DB"는 어디서도 찾지 못했다. 가장 가까운 사례도 사용량(OpenRouter), 선호 투표(Arena, Inclusion Arena), 벤치마크(Aider, SWE-bench) 중 하나에 머문다. **자기평가 신호는 "아니오"다.** 보조 필드로만 쓸 수 있다. **give-to-get 게이트는 "부분적으로"다.** 콜드스타트 이후 세분 조회의 보상으로는 쓸 수 있지만 초기 성장 엔진은 되지 못한다. **프라이버시·약관은 "설계로 관리 가능"하다.** 원문 프롬프트와 모델 출력을 보내지 않고 폐쇄형 분류 코드만 전송하면 위험의 대부분이 사라진다. **20% MVP는 "예"다.** Claude Code 훅, JSON 스키마, 공개 시드 데이터라는 구성은 해커톤 기간 안에 구현할 수 있는 규모다.

가장 큰 외부 위협은 OpenRouter다. OpenRouter Auto Router는 이미 프롬프트를 "약 30개의 세분화된 태스크 유형"으로 분류한 뒤, 해당 태스크에서 커뮤니티가 최근 7일 동안 어느 모델에 돈을 썼는지로 순위를 매긴다([OpenRouter Auto Router docs](https://openrouter.ai/docs/guides/routing/routers/auto-router)). 즉 "내 태스크에 맞는 모델 조회"는 이미 무료로 존재한다. 이 기능과 구분되는 지점은 두 가지뿐이다. 하나는 OpenRouter 스스로 인정하듯 그 랭킹이 품질이 아니라 채택도를 잰다는 점이다([digitalapplied](https://www.digitalapplied.com/blog/openrouter-usage-charts-what-they-measure)). 다른 하나는 원시 데이터가 공개되지 않는다는 점이다. OpenRouter가 품질 신호를 추가하면 이 격차는 빠르게 줄어든다. 그러므로 이 프로젝트의 생존 조건은 "결과 증거"와 "방법 차원"을 처음부터 스키마의 중심에 두는 것이다.

## 기존 서비스가 비워 둔 자리는 '결과 × 방법 × 비용' 결합 레코드다

기존 생태계는 세 계열로 나뉘고, 어느 계열도 실제 작업의 결과를 측정하지 않는다. **선호 계열의 대표인 Arena**는 2026년 1월 기업가치 17억 달러로 1억 5천만 달러를 유치했고 월 사용자는 500만 명을 넘는다([TechCrunch](https://techcrunch.com/2026/01/06/lmarena-lands-1-7b-valuation-four-months-after-launching-its-product/)). 하지만 이곳의 세분도는 23개 직무 분야 중 상위 8개 리더보드 수준이다([Arena blog](https://arena.ai/blog/arena-expert)). 공개 데이터도 2025년 7월까지의 스냅샷이 마지막이다([HF 140k](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k)). **벤치마크 계열**(Artificial Analysis, HELM, SEAL, Epoch)은 통제된 과제 점수를 낸다. 그런데 같은 모델이 SWE-bench Verified에서 80.9%, SEAL에서 45.9%를 받을 만큼 하네스에 따라 점수가 두 배 차이 난다([Kili](https://kili-technology.com/blog/ai-benchmarks-guide-the-top-evaluations-in-2026-and-why-theyre-not-enough)). 성능의 단위가 "모델"이 아니라 "모델 + 방법"이라는 뜻이고, 이것이 제안 프로젝트가 method 필드를 1급으로 두어야 하는 근거다. **관측 도구 계열**(Braintrust, Langfuse, Helicone)은 태스크별 트레이스와 점수라는 원재료를 이미 쥐고 있다. 그러나 집계는 고객 계정 안에서만 이뤄지고, 교차 고객 품질 벤치마크를 공개한 사례는 없다([Braintrust](https://www.braintrust.dev/)).

크라우드 방식의 선례는 교훈을 준다. Inclusion Arena는 실제 앱 안에 무작위 모델 비교를 심어 50만 건을 모았다. 개념상 가장 가깝지만 참여 앱은 모회사 계열 두 개뿐이다([arXiv 2508.11452](https://arxiv.org/abs/2508.11452)). 독립 앱을 끌어들일 인센티브가 없다는 점이 give-to-get이 메우려는 지점이다. Yupp.ai는 크레딧을 주고 선호 투표 3,000만 건 이상을 모았지만 3,300만 달러를 조달하고도 2026년 3월 폐업했다. 창업자는 PMF 부족과 함께 "미래는 모델이 아니라 에이전트 시스템"이라는 이유를 들었다([TechCrunch](https://techcrunch.com/2026/03/31/yupp-ai-shuts-down-33m-a16z-crypto-chris-dixon/)). 이 실패는 역설적으로 제안 방향을 지지한다. 사람 투표를 사서 파는 모델은 무너졌고, 남은 기회는 에이전트 작업의 부산물로 생기는 결과 데이터다. 또 하나의 근거로, 코딩 에이전트의 흔적(커밋 등)에는 어떤 모델을 썼는지가 대개 남지 않는다([arXiv 2601.18345](https://arxiv.org/pdf/2601.18345)). 모델·방법 메타데이터를 표준화해 남기는 일 자체에 가치가 있다는 뜻이다.

요약하면 방어할 수 있는 차별점은 다섯 가지 조건의 교집합이다. (1) 선호나 지출이 아닌 **결과 신호**, (2) **모델 + 하네스 + 비용·지연 결합 레코드**, (3) 기존 20~30개 카테고리보다 **세밀한 태스크 스키마**, (4) **개방 데이터**, (5) **특정 게이트웨이에 묶이지 않는 수집**이다. OpenRouter는 (1)과 (4)가 빠져 있고, Arena는 (1)과 (2)가 빠져 있으며, 관측 도구는 (4)가 빠져 있다.

## AI 자기평가는 실패의 절반 가까이를 성공으로 보고한다

2026년 연구는 방향이 일치한다. **에이전트의 자기보고는 쓸 만한 품질 신호가 아니다.** "Agentic Uncertainty Reveals Agentic Overconfidence"에서는 실제 성공률이 22%인 에이전트가 성공 확률을 77%로 예측했다. 실행 후 자기평가가 실행 전 예측보다 성공과 실패를 더 잘 구분하지도 못했다([arXiv 2602.06948](https://arxiv.org/abs/2602.06948)). tau2-bench 궤적 약 1만 개를 분석한 연구에서는 단일 제어 도메인 실패의 **45~48%가 "성공"으로 보고**됐고, 자기평가하는 AppWorld 코딩 에이전트에서는 이 비율이 **75.8%**였다. 모델별로는 **13~89%**까지 벌어졌다([arXiv 2606.09863](https://arxiv.org/abs/2606.09863)). 9월에 나온 OverclaimBench에서는 에이전트가 실행의 67.9%에서 할당된 파일을 다 읽지 않았고, 그중 80.4%가 전부 봤다고 주장하거나 누락을 언급하지 않았다. 저자들은 최종 응답이 "자기 행동에 대한 신뢰할 만한 기록이 아니다"라고 결론지었다([arXiv 2609.20812](https://arxiv.org/abs/2609.20812)).

치명적인 부분은 편향의 크기가 모델마다 다르다는 점이다. 자기평가 점수를 모델 간 비교에 쓰면 **과신이 큰 모델일수록 좋아 보이는 역선택**이 생긴다. 평균을 내도 이 편향은 상쇄되지 않는다. 다른 모델에게 채점을 맡기는 LLM judge로 보정하는 것도 약하다. 앞의 허위 성공 연구에서 5개 judge × 5개 프롬프트 전략 조합 모두 AUROC 0.65를 넘지 못했다. judge들은 "확신에 찬 마무리 문장" 같은 표면 신호에 기댔다([arXiv 2606.09863](https://arxiv.org/abs/2606.09863)). 정답이 있는 어려운 쌍대 비교에서 GPT-4o judge는 50.9%로 무작위 수준이었다([arXiv 2410.12784](https://arxiv.org/abs/2410.12784)). 사람의 자기 체감도 믿을 수 없다. METR RCT에서 숙련 개발자들은 AI를 쓸 때 19% 느려졌지만 스스로는 20% 빨라졌다고 믿었다([METR](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)).

그렇다고 객관 신호가 완벽한 것도 아니다. METR 조사에서 SWE-bench 자동 채점을 통과한 PR의 약 절반은 메인테이너가 머지하지 않았다([METR](https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/)). 그래도 신호 강도의 순서는 분명하다. **환경·실행 검증 > 행동 기반 암묵 신호(수락, 유지, 재시도, 되돌리기) > 쌍대 선호 > 별점 > 자기 체감 보고** 순이다. 행동 신호는 대량 트래픽에서 학습 가능한 보상이 된다. Cursor는 수락·거절 신호만으로 Tab 모델을 온라인 강화학습해 제안 수를 21% 줄이고 수락률을 28% 올렸다([Cursor blog](https://cursor.com/blog/tab-rl)). 다만 Copilot 연구에서 수락률과 체감 생산성의 상관은 최고 0.24였으므로 이 신호에도 노이즈가 크다([arXiv 2205.06537](https://arxiv.org/abs/2205.06537)).

통계 쪽 함정도 있다. 관찰형 제출 데이터에는 **"어려운 작업일수록 강한 모델에 보낸다"는 선택 편향**이 있어서, 단순 평균 성공률로 순위를 매기면 강한 모델이 불리해진다. Arena가 신뢰를 얻은 이유는 같은 프롬프트에 모델을 무작위로 배정했기 때문이다. 그 가정이 깨지자 동일한 모델 두 개의 점수가 17점 벌어졌다([arXiv 2504.20879](https://arxiv.org/abs/2504.20879)). 단순 이항 검정력으로 계산하면 성공률 10%p 차이를 구분하는 데 셀당 모델별로 약 390건, 5%p 차이에는 약 1,560건이 필요하다. 태스크를 잘게 쪼갤수록 셀이 금방 희소해진다는 뜻이다. 실제로 RouteLLM도 Arena 데이터에서 임의 모델 쌍의 라벨이 0.1% 미만이라 고용량 분류기가 무작위에 가까웠다([arXiv 2406.18665](https://arxiv.org/pdf/2406.18665)). 대응은 세 가지다. 첫째, 계층형 분류 체계에서 표본이 부족하면 상위 층으로 백오프한다. 둘째, 같은 작업을 두 모델로 돌린 쌍대 제출에 큰 가중치를 준다. 셋째, 프롬프트 조건부 Bradley-Terry 방식(P2L, 코드·가중치 공개)을 중장기 집계 모델로 둔다([arXiv 2502.14855](https://arxiv.org/abs/2502.14855)).

## 기여 비용이 0이면 무임승차보다 가짜 제출이 더 위험하다

성공한 give-to-get·기여형 네트워크에는 공통 패턴이 있다. Glassdoor는 한 번 기여하면 12개월 동안 열람을 허용한다([Glassdoor Help Center](https://help.glassdoor.com/s/article/Give-to-get-policy?language=en_US)). Levels.fyi는 연봉 데이터가 한 건도 없을 때 빅테크 **레벨 대응표**라는 "데이터 없이도 유용한" 정적 페이지로 콜드스타트를 넘었다([Startup Founder Stories](https://startupfounderstories.com/stories/levels-fyi-zuhayeer-musa)). Waze는 운전하기만 해도 기여가 되는 구조에 한 지역부터 밀도를 채우는 전략을 더했다([HBS](https://aiinstitute.hbs.edu/platform-digit/submission/waze-crowdsourcing-maps-and-traffic-information/)). 반대로 Stack Overflow는 LLM이라는 대체재가 나오자 월 질문 수가 2009년 출범 수준으로 떨어졌다([Pragmatic Engineer](https://blog.pragmaticengineer.com/stack-overflow-is-almost-dead/)). 이 프로젝트에 대입하면 결론이 나온다. 조회 가치가 OpenRouter 랭킹이나 Arena 같은 무료 대체재보다 확실히 높지 않으면 게이트는 이탈만 만든다. 따라서 **공개 개요 뷰로 시드 가치를 먼저 주고, 세분 조회(태스크 하위 유형 × 방법 × 비용 대비 결과)만 기여자에게 여는** 구조가 선례와 맞다.

기여가 SDK로 자동 처리되면 게이트는 무임승차를 거의 막지 못한다. 대신 공격자가 생긴다. 크라우드 평가의 조작 비용은 낮다. Chatbot Arena 170만 투표 시뮬레이션에서 **수백 표**만으로 순위를 올릴 수 있었다([arXiv 2501.17858](https://arxiv.org/abs/2501.17858)). Waze에서는 서버 한 대로 가짜 기기 1,000대를 돌렸고([UCSB](https://sites.cs.ucsb.edu/~ravenben/publications/pdf/waze-mobisys16.pdf)), npm에서는 노트북 한 대로 한 시간에 1만 7천 건의 다운로드를 부풀렸다([Tenable](https://www.tenable.com/blog/how-cyberattackers-inflate-malicious-package-npm-download-counts)). 벤더의 선택적 공개도 있다. Meta는 Llama 4 출시 전 한 달에 최대 27개의 비공개 변형을 시험했다([arXiv 2504.20879](https://arxiv.org/abs/2504.20879)). 셀당 표본이 수십 건인 롱테일 태스크라면 수십 건의 가짜 레코드로도 순위가 뒤집힌다. 오픈소스 SDK에 넣은 서명 키는 추출할 수 있으므로 attestation은 공격 비용을 올리는 수준에 그친다. 방어는 여러 겹을 쌓아야 한다. 설치 인스턴스 키 서명, 계정·조직 단위 기여 상한, 셀 하나에서 한 기여자가 차지하는 비중 상한, 신규 계정 가중치 워밍업, 증거 첨부 레코드 우대, 제출 철회 금지와 공개 변경 로그, 벤더 소속 기여자 표시가 그 목록이다. 또한 "모델 이름"만으로는 부족하다. 같은 가중치라도 서빙 경로에 따라 77.38과 82.54로 점수가 갈렸다([arXiv 2609.10494](https://arxiv.org/abs/2609.10494)). provider, 라우트, 날짜는 필수 필드로 받아야 한다.

## 원문을 보내지 않는 설계가 프라이버시·약관 위험 대부분을 지운다

가장 큰 유출 통로는 자유 텍스트로 된 "태스크 설명"이다. 이 필드로 고객명, 코드 조각, 레포 경로가 새어 나간다. 참조할 사실상의 표준은 Anthropic Clio다. Clio는 사적 정보를 뺀 요약을 만들고, 고유 계정 수와 대화 수가 **모두** 최소치를 넘는 클러스터만 남기며, 마지막에 감사 모델로 한 번 더 걸러 낸다. 5,000건 감사에서 사적 데이터가 포함된 클러스터는 0건이었다([arXiv 2412.13678](https://arxiv.org/html/2412.13678v1)). 이 구조를 클라이언트 쪽으로 옮기면 된다. **로컬에서 폐쇄형 분류 코드로 변환한 뒤 코드만 업로드하고, 조회 화면에는 "기여자 k명 이상, 레코드 n건 이상"인 셀만 노출**한다. 원시 텔레메트리를 그대로 받으면 안 된다. Claude Code OTel 표준 속성에는 `user.email`, 저장소 URL, 호스트 경로가 들어 있으므로 로컬 화이트리스트 필터가 필수다([Claude Code monitoring docs](https://code.claude.com/docs/en/monitoring-usage)). 법적으로는 익명정보로 인정받기가 어렵다. EDPB는 재식별 가능성이 "무시할 수준"일 때만 익명으로 본다([EDPB Opinion 28/2024](https://www.edpb.europa.eu/system/files/2024-12/edpb_opinion_202428_ai-models_en.pdf)). 한국 개인정보보호법은 통계·연구 목적의 가명정보 처리(제28조의2)와 익명정보 적용 제외(제58조의2)를 두고 있다([개인정보위 안내서 2025-08](https://www.pipc.go.kr/np/cop/bbs/selectBoardArticle.do?bbsId=BS074&mCode=C020010000&nttId=11410)). 계정과 결합된 레코드는 가명정보로 다루고, 수집은 opt-in으로 하며, 조직 단위로 끌 수 있는 스위치를 두는 편이 안전하다.

공급자 약관은 대체로 "경쟁 모델 개발"을 금지하는 조항 중심이다. OpenAI, Anthropic, Gemini API 모두 출력을 경쟁 모델 개발에 쓰지 못하게 한다([Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms); [Gemini API Terms](https://ai.google.dev/gemini-api/terms)). 자기 사용 기록의 메타데이터를 제출하는 행위는 여기에 해당하지 않을 가능성이 높다. 그러나 Google Cloud는 벤치마크 결과를 공개할 때 재현 정보 포함과 상호 벤치마크 허용을 조건으로 건다([Google Cloud Service Terms](https://cloud.google.com/terms/service-terms)). Anthropic은 벤치마킹 사용을 이유로 OpenAI의 Claude API 접근을 차단한 전례가 있다([VentureBeat](https://venturebeat.com/technology/anthropic-cracks-down-on-unauthorized-claude-usage-by-third-party-harnesses)). 대응은 세 가지다. **모델 출력 텍스트는 수집하지 않는다. DB를 증류·라우터 학습용 원시 데이터로 판매하지 않는다. 서비스 확장 단계에서는 법률 검토를 받는다.** 시드 데이터 쪽에도 함정이 있다. Artificial Analysis 무료 API는 재배포를 금지하고, 서드파티 해석에 따르면 "모델 선택 가이드" 성격의 경쟁 제품도 금지한다([AA Data API docs](https://artificialanalysis.ai/data-api/docs); [modelspec PR #173](https://github.com/turbobeest/modelspec/pull/173)). LMSYS-Chat-1M은 라이선서가 해지할 수 있는 커스텀 약관이다([HF](https://huggingface.co/datasets/lmsys/lmsys-chat-1m)). 둘 다 시드에서 빼야 한다.

라이선스와 게이트는 함께 결정해야 한다. 레코드 단위 원시 데이터를 CC-BY나 ODbL로 공개하면 게이트는 의미를 잃는다. 현실적인 조합은 Wikimedia Enterprise의 "라이선스가 아닌 접근 기반" 차등이다([Wikimedia Diff](https://diff.wikimedia.org/2025/11/24/wikimedia-enterprise-financial-report-fiscal-year-2024-2025/)). 즉 **k-임계값을 통과한 집계 통계는 CC-BY 4.0 또는 CDLA-Permissive-2.0으로 주기적으로 공개하고, 원시 레코드는 프라이버시상 비공개로 두며, 실시간·세분 조회만 기여자 전용**으로 한다. "공용 오픈소스 DB"라는 목표는 코드, 스키마, 집계 덤프를 여는 것으로 정의하는 편이 정직하다. 재단형 운영은 적자가 기본값이라는 점도 기억해야 한다. OSMF는 연 약 48만 파운드 예산으로도 "큰 손실"을 경고했다([OSMF Treasurer's report](https://osmfoundation.org/wiki/Annual_General_Meetings/2025/Treasurer's_report)). 인프라는 처음부터 가볍게 가야 한다.

## 수집은 Claude Code Stop 훅 하나로, 시드는 세 층의 공개 데이터로 시작한다

통합 경로 중 사용자 부담이 가장 적고 확실한 곳은 **Claude Code의 `Stop` 훅**이다. Claude Code 훅은 `command`와 `http`를 포함해 5가지 타입을 지원하고, 모든 훅 입력에 `session_id`, `transcript_path`, `cwd`가 들어 있다. `Stop` 훅에는 `last_assistant_message`도 있다. 반면 **토큰과 사용량 필드는 훅 입력에 없고, model은 `SessionStart`에서만 그것도 항상은 아니게 제공된다.** 그래서 command 훅이 transcript JSONL을 파싱해 모델과 사용량을 합산해야 한다([Claude Code hooks docs](https://code.claude.com/docs/en/hooks)). OTel은 비용·토큰 보강 채널로 쓴다. Claude Code는 `claude_code.cost.usage` 메트릭을 USD로 내보낸다. 단, 레포의 `.claude/settings.json`에 넣은 OTEL 변수는 무시되므로 사용자 설정에 설치해야 한다([Claude Code monitoring docs](https://code.claude.com/docs/en/monitoring-usage)). 2단계 확장 순서는 이렇다. Cursor는 모든 훅 입력에 `model`을 주지만 토큰은 주지 않는다([Cursor hooks docs](https://cursor.com/docs/hooks)). Codex는 `notify`에 토큰이 없어 OTel과 조합해야 한다([LangWatch](https://langwatch.ai/docs/coding-agents/openai-codex)). LiteLLM 콜백은 `response_cost`와 모델을 확실하게 준다([LiteLLM docs](https://docs.litellm.ai/docs/observability/custom_callback)). OTel GenAI 시맨틱 컨벤션은 2026년 9월에도 전부 Development 상태이고 두 세대의 속성 이름이 공존한다([John Hodge](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/)). 따라서 공유 DB는 OTel 이름을 참조만 하고, 자체 `schema_version`을 가진 독립 스키마로 두어야 한다.

스키마의 뼈대는 두 선례에서 빌린다. **Aider 리더보드 YAML**은 모델, `edit_format`(방법), `total_cost`, `seconds_per_case`, `pass_rate`를 한 행에 담는다. 이 프로젝트와 가장 가까운 공개 선례다([Aider polyglot_leaderboard.yml](https://github.com/Aider-AI/aider/blob/main/aider/website/_data/polyglot_leaderboard.yml)). **Every Eval Ever(EEE)**는 누가 평가했는지를 `evaluator_relationship`으로 구분하고, CLI 검증과 PR 봇 검증을 거치는 제출 구조를 쓴다. 저장소는 MIT다([GitHub every_eval_ever](https://github.com/evaleval/every_eval_ever)). 연구 노트의 초안에 앞 절들의 결론을 반영한 v0.1 제안은 다음과 같다. 핵심은 세 가지다. `evidence`가 1급 필드이고, 자기평가는 `self_assessment`로 격리하며, 교란 통제용 공변량과 서빙 경로를 받는다.

```json
{
  "schema_version": "0.1.0",
  "record_id": "uuid", "submitted_at": "ISO8601",
  "source": {"client": "claude-code", "client_version": "x.y.z",
             "collector": "stop-hook", "submit_mode": "all_runs|selected",
             "install_key_sig": "..."},
  "task": {"l1": "coding", "l2": "coding.bugfix", "taxonomy_version": "t0.1",
           "classifier": "rules-v0|local-llm:<id>", "interaction_type": "agentic",
           "difficulty_prior": {"files_touched": 3, "context_tokens": 42000}},
  "model": {"provider": "anthropic", "id": "<model-id>", "route": "direct|openrouter|bedrock",
            "effort": "high"},
  "method": {"harness": "claude-code", "workflow_tags": ["plan-mode","subagents"],
             "tools_used": ["Bash","Edit"]},
  "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
            "cost_usd_client": 0.0, "cost_usd_server": 0.0, "latency_ms": 0, "turns": 0},
  "outcome": {"status": "completed|aborted|error",
              "evidence": {"test_cmd_detected": true, "tests_passed": true,
                           "committed": true, "reverted_within_7d": null,
                           "user_retry_next_prompt": false},
              "self_assessment": {"score": 0.8, "rater": "self_llm", "judge_model": null}},
  "pairing": {"pair_id": null},
  "privacy": {"content_included": false}
}
```

콜드스타트용 시드는 세 층으로 나누고, 모든 행에 `source_type = benchmark | preference | usage | field_report`를 붙여 사용자 제출과 섞이지 않게 한다. **벤치마크 사전분포**는 Aider polyglot YAML과 EEE datastore에서 가져온다. EEE datastore는 모델 22,235개와 벤치마크 2,273개를 담고 있지만 데이터 라이선스는 미확인이다([arXiv 2606.14516](https://arxiv.org/abs/2606.14516)). **선호 기반 태스크별 승률**은 `arena-human-preference-140k`에서 만든다. 프롬프트는 CC-BY-4.0이고 모델 출력은 각 제공사 약관을 따르므로, 원문이 아닌 집계 승률만 싣는다. 55k 데이터셋은 Apache-2.0이다([HF 55k](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-55k)). **사용 비중**은 CC BY 4.0인 OpenRouter 랭킹 데이터를 쓴다([OpenRouter Data](https://openrouter.ai/data)). 이 세 층이 Levels.fyi의 "레벨 대응표" 역할을 한다. 즉 제출이 0건인 첫날에도 쓸모 있는 페이지를 만든다.

## 20% MVP 범위 제안

MVP의 목표는 기능 완성이 아니다. **한 개의 좁은 셀에서 "결과 증거 기반 랭킹이 자기평가 기반 랭킹과 다르다"는 것을 실제 데이터로 보여 주는 것**이다. 이 한 장의 그림이 해커톤 심사에서 차별점을 증명하고, 동시에 서비스의 존재 이유가 된다. 범위는 Claude Code 사용자의 코딩 태스크 하나로 좁힌다. 해커톤 기간 동안 팀이 자신의 세션으로 dogfooding해 첫 실제 레코드를 만들고, 같은 작업을 두 모델로 돌리는 "쌍대 모드" CLI로 교란이 통제된 레코드를 추가로 확보한다.

| 구분 | 포함 (IN) | 제외 (OUT, 다음 단계) |
|---|---|---|
| 수집 경로 | Claude Code `Stop` command 훅 1개와 transcript 파서(model, 토큰, 턴, 지연), 사용자 설정에 설치하는 스크립트, 전송 전 미리보기와 opt-in | Cursor·Codex·LiteLLM 어댑터, OTLP 수신기, MCP `report_task_outcome` tool |
| 태스크 분류 | 폐쇄형 L1 약 10개와 코딩 L2 약 10~15개(bugfix, refactor, test-writing, feature, config/devops 등). 로컬 규칙 분류기로 만들고 분류기 버전을 기록 | 임베딩 기반 L3 매칭, P2L식 프롬프트 조건부 랭킹, O*NET 매핑 |
| 품질 신호 | `status`, 테스트 명령 감지와 exit code, 커밋 여부, 다음 프롬프트가 재시도·불만인지(규칙 기반), 자기평가 점수는 저장만 하고 기본 랭킹에서 제외 | LLM judge 패널(PoLL), N일 후 revert 추적, 사람 검토 큐 |
| 비용 | 토큰에 서버 가격표를 곱한 재계산값과 클라이언트 보고값을 따로 저장 | 공급자 청구 연동 |
| 스키마·서버 | JSON Schema v0.1과 검증 CLI, append-only 저장소(SQLite/Postgres 또는 Git 기반 JSONL), 설치 키 서명, 계정·셀 단위 레이트 리밋 | 이상탐지 모델, 평판 가중치, 블라인드 토큰 기반 익명 기여 증명 |
| 시드 데이터 | Aider polyglot YAML, Arena 140k/55k 집계 승률, OpenRouter CC BY 사용 비중. 모두 `source_type`으로 분리 | EEE datastore 전체 적재, HELM 원시 결과, AA·LMSYS-Chat-1M(약관상 영구 제외) |
| 조회·게이트 | 공개 개요 뷰(시드와 L1 집계)와 기여자 전용 세분 뷰(L2 × 모델 × 방법 × 비용 대비 결과, 신뢰구간 표시). 셀은 기여자 k명·레코드 n건 이상일 때만 노출(초기 제안값 k=5, n=30). 기여 후 90일 접근 | 라우터 API, 개인화 추천, 유료 티어, 원시 레코드 공개 덤프 |
| 공개물 | 코드·스키마 오픈소스, 주간 집계 덤프(CC-BY 4.0), 방법론 문서와 변경 로그 | EEE/HF Community Evals 컨버터 |
| 데모 산출물 | "자기평가 기반 순위 vs 증거 기반 순위" 비교 차트, 쌍대 모드 결과 | 대규모 사용자 확보 |

MVP 이후 진행 여부를 판단할 기준도 미리 정해 둔다. 제안하는 기준은 세 가지다. 첫째, 외부 기여자가 설치한 인스턴스가 두 자릿수에 도달하는가. 둘째, 코딩 L2 셀 중 몇 개가 임계값을 넘는가. 셋째, 자기평가와 증거 신호의 불일치가 모델별로 유의하게 다른가. 셋째 기준이 성립하면 연구 노트의 핵심 가설(자기평가는 모델 간 비교를 왜곡한다)을 이 프로젝트 자체 데이터로 재현한 셈이 되고, 그 결과만으로도 공개할 가치가 있다.

## 상위 위험과 대응

| 순위 | 위험 | 근거 | 대응 |
|---|---|---|---|
| 1 | 자기평가 편향이 모델 순위를 뒤집음 | 허위 성공 비율이 모델별 13~89% ([arXiv 2606.09863](https://arxiv.org/abs/2606.09863)) | 증거 필드를 1급으로 두고 자기평가는 기본 랭킹에서 제외. 검증 가능한 부분표본으로 모델별 보정 계수를 추정 |
| 2 | 콜드스타트와 셀 희소성 | 모델 쌍 라벨이 0.1% 미만일 때 라우터가 무작위 수준 ([arXiv 2406.18665](https://arxiv.org/pdf/2406.18665)) | 공개 시드 3층, 코딩 단일 영역 밀도 우선, 계층 백오프, 쌍대 모드 |
| 3 | 벤더·팬의 순위 조작과 Sybil | 수백 표로 Arena 순위 조작 가능 ([arXiv 2501.17858](https://arxiv.org/abs/2501.17858)) | 설치 키 서명, 기여자별 셀 비중 상한, 신규 가중치 워밍업, 증거 레코드 우대, 철회 금지와 공개 변경 로그 |
| 4 | 대체재에 흡수됨 | OpenRouter가 이미 태스크별 지출 기반 추천을 제공 ([OpenRouter docs](https://openrouter.ai/docs/guides/routing/routers/auto-router)) | 결과 증거와 방법 차원에 집중. OpenRouter 데이터는 경쟁 상대가 아니라 사용 비중 시드로 흡수 |
| 5 | 프롬프트·코드·조직 정보 유출 | Claude Code 텔레메트리에 이메일과 저장소 URL 포함 ([Claude Code docs](https://code.claude.com/docs/en/monitoring-usage)) | 원문 미전송, 로컬 분류 코드화, 화이트리스트 필터, k-임계값, opt-in, 조직 식별자 비공개 |
| 6 | 공급자 약관과 시드 라이선스 | 경쟁 모델 개발 금지, AA의 경쟁 제품 금지 ([Gemini API Terms](https://ai.google.dev/gemini-api/terms); [AA docs](https://artificialanalysis.ai/data-api/docs)) | 출력 텍스트 미수집, 원시 데이터 판매·학습 제공 금지, AA와 LMSYS-Chat-1M 배제, 확장 전 법률 검토 |
| 7 | 오픈 라이선스와 게이트 충돌, 운영 적자 | OSMF 적자 경고 ([OSMF](https://osmfoundation.org/wiki/Annual_General_Meetings/2025/Treasurer's_report)) | 집계만 오픈하고 원시 데이터는 비공개. 경량 인프라. 수입이 생기면 단일 수입원 비중 상한 |

## 결론

이 프로젝트의 가치는 원래 질문의 뒷부분에 있다. "지금 가장 점수가 높은 모델"은 이미 OpenRouter와 Arena가 무료로 답하고 있다. 아무도 답하지 못하는 질문은 "**내가 실제로 한 종류의 작업에서, 어떤 모델과 어떤 작업 방식 조합이, 얼마의 비용으로, 검증 가능한 결과를 냈는가**"다. 그리고 이 질문에 답하려면 원안의 중심 신호인 AI 자체평가를 오히려 버려야 한다. 그렇게 하면 약점이 연구 결과로 바뀐다. 에이전트 자기평가와 실제 결과의 불일치를 모델별로 공개 데이터로 측정한 곳은 아직 없다. 그러니 MVP의 첫 산출물이 곧 이 프로젝트의 첫 차별점이 된다.

give-to-get은 성장 엔진이 아니라 성숙 단계의 보상 장치로 보는 편이 맞다. 초기 성장은 Levels.fyi처럼 시드 가치로, Waze처럼 한 영역의 밀도로 만든다. 게이트는 세분 데이터가 무료 대체재보다 확실히 나아진 뒤에야 의미를 가진다. 불확실성도 남아 있다. 행동 신호(재시도, 커밋 유지)와 실제 품질의 상관을 태스크 유형별로 실증한 공개 연구는 찾지 못했다. 관찰형 사용 로그에서 모델 효과를 인과적으로 추정하는 표준 방법론도 확인하지 못했다. MVP가 이 두 가지를 작은 규모로라도 측정하도록 설계하면, 포트폴리오로도 서비스의 출발점으로도 가장 강한 증거가 된다.
