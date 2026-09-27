# 태스크별 AI 모델 성과 기록 자동 수집: 통합 경로와 시드용 공개 데이터 (2026-09-27 기준)

작성일: 2026-09-27. 조사 범위: 표준·훅 지점, 초기 데이터(cold start)용 공개 데이터셋, 커뮤니티 제출형 평가 프로젝트의 스키마, 최소 레코드 스키마 권고. 도구 호출 약 21회로 조사를 끝냈기 때문에 일부 도구(Aider, Continue, Roo, Vercel AI SDK 세부, LangChain 콜백, MCP)는 1차 문서로 끝까지 확인하지 못했고, 해당 내용은 Gaps에 적었다.

## Q1. 표준: OTel GenAI semconv, OpenInference, OpenLLMetry. OTel exporter에 편승해 "endpoint만 추가"하는 방식이 가능한가?

### Takeaway
OTel GenAI 시맨틱 컨벤션은 2026년 9월에도 전부 **Development** 상태다(Stable 아님). 2026-06 v1.42.0에서 별도 저장소로 분리됐고, 그 저장소에는 아직 태그된 릴리스가 없다. 그래도 모델, 토큰, 평가(`gen_ai.evaluation.result`) 속성은 이미 정의돼 있다. Claude Code와 Codex CLI는 표준 `OTEL_EXPORTER_OTLP_*` 설정으로 OTLP를 내보내므로 "OTLP 수신 endpoint를 제공하고 사용자는 env/config만 추가"하는 방식은 기술적으로 가능하다. 다만 도구마다 속성 이름공간(`claude_code.*`, `codex.*`, `gen_ai.*`, OpenInference `llm.*`)이 달라 서버 쪽 정규화가 꼭 필요하다. **태스크 텍스트와 자체 품질 평가는 OTel만으로 얻기 어렵다.**

### Cited Findings
- 공식 사이트의 GenAI semconv 페이지는 이제 "Moved" 안내만 남아 있다. 내용은 `open-telemetry/semantic-conventions-genai` 저장소로 옮겨졌다(하위 섹션: Agent spans, Anthropic, AWS Bedrock, Azure AI Inference, Events, Exceptions, Metrics, MCP, OpenAI, Spans). — [opentelemetry.io GenAI semconv](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- 새 저장소는 Apache-2.0이고 Weaver로 core semconv에 의존한다. schema URL은 README에 아직 "TODO"로 적혀 있다. 조사 시점 기준 커밋 640, 스타 394, 열린 이슈 135. — [GitHub semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai)
- 2026-07-17 기준으로 `gen_ai.*`의 span, event, metric, attribute는 **전부 Development**이고, 같은 표에 나오는 `error.type`, `server.address` 같은 core 속성만 Stable이다. 메인 저장소 v1.42.0(2026-06-12)이 `gen_ai.*`를 deprecate하고 새 저장소로 옮겼으며, 새 저장소에는 릴리스/태그가 없다. 따라서 마지막으로 버전이 붙은 GenAI 스냅샷은 v1.42.0이다. — [John Hodge, "The state of the OpenTelemetry GenAI semantic conventions (July 2026)"](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/) (개인 블로그. 2차 출처지만 버전 번호와 날짜가 구체적이다)
- 속성 이력(같은 출처):
  - v1.37.0(2025-08): `gen_ai.provider.name`이 `gen_ai.system`을 대체했고, 메시지가 `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions` 속성으로 바뀌었다.
  - v1.27.0(2024-08): `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`로 이름이 바뀌었다.
  - v1.40.0(2026-02): 캐시 토큰 속성, retrieval span, `gen_ai.agent.version`이 추가됐다.
  - v1.41.0(2026-04): `invoke_agent`가 client/internal로 나뉘었고, reasoning 토큰과 스트리밍 지연 메트릭이 추가됐다.
  - 이 글에는 **비용(cost) 속성에 대한 언급이 없다.** — [John Hodge](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/)
- `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`을 설정하면 최신 실험 컨벤션을 쓴다. 설정하지 않으면 계측 라이브러리는 v1.36 시절 출력을 유지한다. 프레임워크마다 이 값을 따르는 정도가 다르므로 실제로 내보낸 span을 확인하라는 권고가 있다. — [John Hodge](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/)
- 평가 이벤트 `gen_ai.evaluation.result`의 속성:
  - `gen_ai.evaluation.name`(Required)
  - `gen_ai.evaluation.score.value`(숫자), `gen_ai.evaluation.score.label`(예: `pass`/`fail`/`correct`/`relevant`, 카디널리티를 낮게 유지해야 함)
  - `gen_ai.evaluation.explanation`
  - `gen_ai.response.id`(span으로 부모를 연결할 수 없을 때 상관관계용)
  - `error.type`
  - 이 이벤트는 평가 대상 GenAI span을 부모로 두는 것이 권장된다. 평가자 provenance 속성은 PR #359로 제안된 상태다. — [gen-ai-events.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md); [PR #359](https://github.com/open-telemetry/semantic-conventions-genai/pull/359); [OTel registry gen-ai attributes](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/)
- 평가 이벤트가 어느 버전에 들어갔는지는 출처마다 다르다. Hodge 블로그는 "v1.38.0(2025-10)"이라고 하고, 검색 요약에는 "semantic-conventions#2563, 2025-08 merge, v1.39.0"이라는 서술이 있다. 어느 쪽이든 2025년 하반기에 도입됐다. — [John Hodge](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/); [TrueFoundry 블로그](https://www.truefoundry.com/blog/opentelemetry-genai-semantic-conventions)
- 프레임워크별 채택 현황:
  - Vercel AI SDK 7은 OTel을 `@ai-sdk/otel`로 분리했다. 현재 provider/token 필드를 내보내면서 레거시 `ai.*`도 유지한다.
  - OpenAI Agents SDK는 자체 트레이싱을 쓰고 GenAI semconv를 네이티브로 내보내지 않는다.
  - Pydantic AI는 현재 형식을 기본으로 쓴다.
  - Strands는 v1.36 형식이 기본이다.
  - OpenLLMetry는 패키지와 버전마다 마이그레이션 상태가 다르다.
  - 실무 권고: 양쪽 세대의 속성을 COALESCE하고(합산하면 중복 집계됨), 자체 내부 스키마를 두고, 커스텀 속성은 `gen_ai.*` 밖에 둔다. — [John Hodge](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/)
- OpenInference(Arize)는 OTel 위에 얹는 별도 컨벤션이다.
  - 주요 속성: `openinference.span.kind`, `llm.model_name`, `llm.provider`, `llm.token_count.prompt|completion|total`, `llm.cost.*` 접두사, `llm.input_messages.<i>.message.role|content`.
  - Phoenix는 `gen_ai.*` span을 제대로 해석하지 못한다.
  - OTel Collector contrib의 `genainormalizerprocessor`가 `llm.token_count.prompt`를 `GenAIUsageInputTokens`로, `llm.model_name`을 `GenAIRequestModel`로 매핑한다. — [OpenInference spec](https://arize-ai.github.io/openinference/spec/semantic_conventions.html); [salaboy 2026-05-27](https://www.salaboy.com/2026/05/27/five-semantic-conventions-one-config-property-observing-spring-ai-with-arconia/); [openinference issue #3097](https://github.com/Arize-ai/openinference/issues/3097)
- Claude Code의 OTel 설정과 신호:
  - 설정: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER`, `OTEL_LOGS_EXPORTER`, `OTEL_TRACES_EXPORTER`(beta), `OTEL_EXPORTER_OTLP_PROTOCOL`(기본값 없음), `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`.
  - 메트릭 `claude_code.cost.usage`(USD)와 `claude_code.token.usage`(type=input/output/cacheRead/cacheCreation)에는 `model`, `query_source`, `effort`, `agent.name`, `skill.name`, `mcp_tool.name` 등이 붙는다.
  - 트레이스 `claude_code.llm_request` span에는 `gen_ai.request.model`, `input_tokens`, `output_tokens`, `cache_*_tokens`, `duration_ms`, `ttft_ms`, `success`, `stop_reason`이 들어간다.
  - 프롬프트 텍스트는 기본적으로 redact된다(`OTEL_LOG_USER_PROMPTS=1`로 opt-in).
  - **레포의 `.claude/settings.json`에 넣은 OTEL 변수는 무시된다.** 사용자 설정(`~/.claude/settings.json`), 셸, managed settings에 넣어야 한다. — [Claude Code monitoring docs](https://code.claude.com/docs/en/monitoring-usage)
- Codex CLI의 OTel:
  - `~/.codex/config.toml`의 `[otel]`에서 설정한다(`exporter = { otlp-http = {...} }` 또는 `otlp-grpc`). 기본은 꺼져 있다.
  - 메트릭 `codex.turn.token_usage`(input/cached_input/output/reasoning_output/total), `codex.turn.e2e_duration_ms` 등을 낸다.
  - **프롬프트 텍스트와 비용은 내보내지 않는다.** `codex exec`는 메트릭이 없고 `codex mcp-server`는 아무것도 내보내지 않는다.
  - 프로젝트 로컬 config의 `otel`과 `notify`는 무시된다.
  - 출처는 서드파티 KB와 블로그를 검색 요약으로 본 것이고, 공식 config reference는 직접 열람하지 못했다. — [LangWatch Codex docs](https://langwatch.ai/docs/coding-agents/openai-codex); [Codex KB OTel](https://codex.danielvaughan.com/2026/04/16/codex-cli-opentelemetry-observability-tracing-agent-sessions/); [OpenAI Codex config reference](https://developers.openai.com/codex/config-reference)

### Inferences
- "사용자가 endpoint만 추가"하는 방식은 Claude Code와 Codex에서 가능하다. 다만 수집 서버가 OTLP/HTTP(4318, `/v1/logs`, `/v1/metrics`, `/v1/traces`)를 받아 도구별 이름공간을 공통 스키마로 정규화해야 한다. 가장 싼 구현은 OTel Collector에 `genainormalizerprocessor`와 transform processor를 붙이고, 커스텀 HTTP exporter로 DB에 적재하는 것이다.
- OTel 데이터에는 "태스크 유형"과 "품질"이 없다. 품질은 표준 슬롯인 `gen_ai.evaluation.result`에 실을 수 있지만, 그 값을 만드는 주체(훅, 자체 평가 프롬프트, 사용자 피드백)는 따로 있어야 한다. OTel은 **비용·토큰·지연·모델 수집 채널**로, 훅이나 MCP는 **태스크 요약·품질 채널**로 역할을 나누는 게 현실적이다.
- 공개 공유 DB에 원시 OTel 로그를 그대로 받으면 개인정보(`user.email`, `user.account_uuid`, `vcs.repository.url.full`, `workspace.host_paths` 등 Claude Code 표준 속성)가 섞여 들어올 위험이 크다. 클라이언트 쪽 로컬 Collector에서 화이트리스트 필터를 거친 뒤 업로드하는 구조가 필요하다.
- GenAI semconv가 Development 상태이고 두 세대 속성이 공존하므로, 공유 DB 스키마는 OTel 이름을 참조하되 자체 버전(`schema_version`)을 갖는 독립 스키마로 두는 것이 안전하다.

### Gaps
- `gen_ai.usage.cache_*` 속성의 정확한 이름, 공식 비용 속성이 있는지 여부, `gen_ai.operation.name` 전체 enum은 새 저장소의 `docs/registry/attributes/gen-ai.md`를 직접 열어 확인하지 못했다.
- OpenLLMetry(Traceloop)의 2026년 현황(OTel 기부/병합 여부 등)은 이번 조사에서 1차 출처를 확보하지 못했다.

## Q2. 인기 에이전트 도구의 훅 지점: 각각 모델 id, 토큰, 비용, 태스크 텍스트에 접근할 수 있는가?

### Takeaway
"태스크 종료" 훅이 있는 곳은 Claude Code(`Stop`/`SessionEnd`, http 훅 타입까지 지원), Cursor(`stop`, `afterAgentResponse`), Cline(`TaskComplete`), Codex(`notify` agent-turn-complete, 신규 hooks.json)다. 다만 **훅 입력에 토큰과 비용이 들어 있는 도구는 없었다.** 토큰과 비용은 OTel 또는 transcript 파싱으로 얻어야 한다. Cursor만 모든 훅 입력에 `model`을 넣어 준다. 게이트웨이 계층(LiteLLM, OpenRouter)과 SDK 계층(OpenAI Agents SDK)은 모델, 토큰, 비용을 가장 확실하게 준다.

### Cited Findings
- **Claude Code hooks**
  - 이벤트는 33종이다. 이 프로젝트와 관련된 것은 `Stop`, `StopFailure`, `SubagentStop`, `SessionEnd`(matcher: `clear`/`resume`/`logout`/`prompt_input_exit`/`other`), `TaskCompleted`, `UserPromptSubmit`, `PostToolUse`다.
  - 공통 입력 필드: `session_id`, `prompt_id`(v2.1.196+), `transcript_path`, `cwd`, `permission_mode`, `effort`, `hook_event_name`.
  - `Stop`/`SubagentStop`에는 `last_assistant_message`가 있다.
  - **model 필드는 `SessionStart`에서만, 그것도 항상은 아니게 제공된다.** 토큰과 사용량 필드는 없다. 사용량은 transcript를 파싱하거나 `prompt_id`로 OTel과 상관관계를 맺어 얻어야 한다.
  - 훅 타입은 5가지다: `command`, `http`(url로 POST), `mcp_tool`(연결된 MCP 서버의 tool 호출), `prompt`(단일 턴 LLM 평가), `agent`(실험적).
  - `SessionEnd` 훅들은 합계 1.5초 타임아웃을 공유한다(최대 60초까지 늘릴 수 있음). — [Claude Code hooks docs](https://code.claude.com/docs/en/hooks)
- **Claude Code OTel**: 트레이스 span `claude_code.interaction`이 사용자 프롬프트 1회 처리 단위이고, 하위에 `llm_request`와 `tool` span이 있다. 이벤트 `claude_code.user_prompt`와 `assistant_response`가 있다. 이벤트 로그와 훅은 `prompt.id`로 연결할 수 있다. — [Claude Code monitoring docs](https://code.claude.com/docs/en/monitoring-usage)
- **Codex CLI**
  - `notify`는 `agent-turn-complete` 이벤트 1종만 있다. JSON이 stdin이 아니라 **마지막 명령줄 인자**로 전달된다.
  - payload에는 `session_id`, `cwd`, `turn_id`, `input_messages`, `last_assistant_message`가 있고 토큰 수는 없다.
  - `notify`는 레거시로 유지되는 기능이고, 새 통합에는 hooks.json을 쓰라고 권장된다.
  - LangWatch는 notify와 transcript, OTel을 조합해 수집한다. — [backgrind 블로그](https://backgrind.com/blog/codex-cli-notifications/); [LangWatch](https://langwatch.ai/docs/coding-agents/openai-codex); [Codex hooks KB](https://codex.danielvaughan.com/2026/04/15/codex-cli-hooks-complete-guide-events-policy-patterns/)
- **Cursor hooks**
  - `.cursor/hooks.json`에서 설정한다. 모든 훅의 기본 입력에 `conversation_id`, `generation_id`, `model`, `model_id`, `model_params`, `hook_event_name`, `cursor_version`, `workspace_roots`, `user_email`, `transcript_path`가 있다.
  - `stop` 입력은 `{"status":"completed"|"aborted"|"error","loop_count":N}`이다. `afterAgentResponse`는 응답 `text`를 준다.
  - Cloud Agent에서는 `stop`과 `afterAgentResponse`가 실행되지 않는다(2026-05 포럼 버그 리포트). 토큰과 비용 필드에 대한 언급은 찾지 못했다. — [Cursor hooks docs](https://cursor.com/docs/hooks); [Cursor forum bug](https://forum.cursor.com/t/cursor-cloud-agents-do-not-run-afteragentresponse-or-stop-hooks/159929); [ntorres 가이드](https://ntorres.dev/blog/cursor-hooks-json-guide)
- **Cline hooks**(v3.36+)
  - 실행 파일을 `~/Documents/Cline/Rules/Hooks/` 또는 `.clinerules/hooks/`에 두는 방식이다.
  - 이벤트는 `TaskStart`, `TaskResume`, `TaskCancel`, `TaskComplete`, `TaskError`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `PreCompact`, `SessionShutdown`이다.
  - 기본 입력은 `clineVersion`, `hookName`, `timestamp`, `taskId`, `workspaceRoots`, `userId`다. **model 필드는 문서에 없고 transcript도 제공되지 않는다.**
  - 버그 #7672: TaskStart/TaskComplete 값이 null로 나온다(2025-11). — [Cline hooks docs](https://docs.cline.bot/customization/hooks); [Cline v3.36 blog](https://cline.bot/blog/cline-v3-36-hooks); [cline issue #7672](https://github.com/cline/cline/issues/7672)
- **LiteLLM**
  - 콜백 `kwargs`에 `model`, `messages`, `response_cost`, `cache_hit`, `litellm_params.metadata`가 있다.
  - 모든 응답에 대해 `kwargs["standard_logging_object"]`(StandardLoggingPayload)가 기록된다(스트리밍 중간 이벤트는 예외).
  - `CustomLogger.async_log_success_event`로 구현하고 `litellm.callbacks`에 등록한다. Proxy도 같은 방식을 지원한다. — [LiteLLM custom callbacks](https://docs.litellm.ai/docs/observability/custom_callback); [StandardLoggingPayload spec](https://docs.litellm.ai/docs/proxy/logging_spec)
- **OpenRouter**: `HTTP-Referer` 헤더로 앱 attribution을 하면 공개 랭킹과 모델 페이지에 앱별 사용량이 노출된다. hidden 앱 옵션도 있다. — [OpenRouter App Attribution](https://openrouter.ai/docs/app-attribution)
- **OpenAI Agents SDK**
  - `add_trace_processor()`로 커스텀 `TracingProcessor`(`on_trace_start/end`, `on_span_start/end`)를 추가할 수 있다. `set_trace_processors()`는 OpenAI로 보내는 기본 exporter를 대체한다.
  - Generation span에는 model과 usage가 있다.
  - JS SDK의 turn span에는 input, output, cached-input, cache-write 토큰이 있다. — [openai-agents-python tracing.md](https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md); [Agents SDK JS tracing](https://openai.github.io/openai-agents-js/guides/tracing/); [Processor interface](https://openai.github.io/openai-agents-python/ref/tracing/processor_interface/)
- **Vercel AI SDK 7**: OTel 기능은 `@ai-sdk/otel` 패키지로 옮겨졌고, 현재 GenAI provider/token 필드를 내보낸다. — [John Hodge](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/)

### Inferences
- MVP에 가장 적합한 수집 지점은 **Claude Code `Stop` 훅(http 또는 command)**이다.
  1. http 훅이 `session_id`, `prompt_id`, `last_assistant_message`를 서버로 바로 POST한다.
  2. command 훅이라면 `transcript_path`의 JSONL에서 모델과 usage를 파싱해 합산한다.
  3. 선택적으로 `prompt` 타입 훅으로 LLM 자체 평가 점수를 만든다.

  이 흐름은 설정 파일 한 줄 수준이라 사용자 부담이 가장 작다. 단, 레포 로컬 설정이 아니라 사용자 설정에 설치하게 하는 편이 OTel 조합까지 고려하면 일관적이다.
- 멀티툴 지원 우선순위는 이렇게 정리된다. Cursor(model 제공, 토큰 없음), Codex(OTel 토큰과 notify 텍스트 조합), LiteLLM(비용과 모델이 확실한 게이트웨이 계층, 태스크 텍스트는 metadata 태깅이 필요), Cline(모델 정보 없음, 후순위).
- **MCP `report_task_outcome` tool 방식**은 어떤 MCP 클라이언트에서도 동작한다는 장점이 있다. 하지만 에이전트가 스스로 tool을 호출해야 하므로 "자동" 수집률이 낮고, 모델이 자기 모델 id와 토큰을 정확히 알지 못하는 경우가 많아 자기 보고값의 신뢰도가 낮다(추론). Claude Code의 `mcp_tool` 훅 타입을 쓰면 `Stop` 시점에 MCP tool을 결정적으로 호출할 수 있다. 즉 "MCP 서버와 훅의 조합"이 이식성과 자동성의 절충안이다.
- 토큰과 비용은 훅 payload에 없으므로, 클라이언트는 도구별 transcript 파서(Claude Code JSONL, Codex rollout 파일)나 로컬 OTel 수신기를 갖춰야 한다. 비용은 대부분 도구가 주지 않으므로(Claude Code 메트릭과 LiteLLM만 제공) 서버 쪽 가격표(LiteLLM `model_prices` 등)로 재계산하는 것이 일관성 면에서 낫다(추론).

### Gaps
- Aider(analytics와 `--analytics-log`), Continue, Roo Code, LangChain/LangGraph callback(`on_llm_end`의 `llm_output.token_usage`), OpenRouter `usage` 응답의 cost 필드는 이번 조사에서 1차 문서를 열람하지 못했다.
- MCP 프로토콜이 서버에 호출 모델 id를 전달하는지는 확인하지 못했다. 필자 지식으로는 `initialize`의 `clientInfo`(name/version)만 전달되지만, 출처로 검증하지는 않았다.
- Codex 신규 hooks.json의 이벤트 목록과 필드는 1차 문서로 확인하지 못했다.
- Claude Code `Stop` 훅의 `stop_hook_active` 필드와 `SessionEnd`의 `reason` 필드 이름은 페이지가 잘려 확인하지 못했다.

## Q3. Cold start용 공개 데이터셋: 라이선스와 태스크 유형별 결과 포함 여부

### Takeaway
라이선스가 가장 깨끗한 시드 소스는 다음과 같다.
- LMArena `arena-human-preference-*`: 프롬프트는 CC-BY-4.0, 모델 출력은 각 제공사 약관, 55k는 Apache-2.0.
- WildChat-4.8M: ODC-BY.
- OpenRouter 랭킹 데이터: CC BY 4.0.
- EEE datastore: 저장소 MIT, 데이터 라이선스는 미확인.
- Aider 리더보드 YAML.

LMSYS-Chat-1M은 해지 가능한 커스텀 약관이고, Artificial Analysis는 무료 API라도 재배포와 "모델 선택 가이드 경쟁 제품"을 금지하므로 **피해야 한다.** 태스크 유형별 결과를 직접 담은 곳은 Arena의 카테고리/투표 데이터와 벤치마크별 점수 정도이고, "실제 작업 + 모델 + 워크플로 + 비용 + 성공"을 한 행에 담은 공개 데이터는 찾지 못했다.

### Cited Findings
- **LMArena HF 데이터셋**
  - `arena-human-preference-140k`, `-100k`, `search-arena-24k`, `PPE-Human-Preference-V1`: 사용자 프롬프트는 CC-BY-4.0, 모델 출력은 각 제공사 이용약관을 따른다. PPE는 학습용이 아니라 벤치마킹과 평가용이다.
  - `arena-human-preference-55k`는 Apache-2.0이다(Kaggle 대회용, 70개 이상 모델).
  - `VisionArena-Battle`은 해지 가능한 커스텀 약관이다.
  - `search-arena-24k`는 대화 24,069건과 투표 12,652건으로 구성되고, 2025-03-18부터 05-08까지 수집됐으며 DLP로 PII를 제거했다.
  - 2026년에 새로 나온 LMArena 투표 데이터셋은 검색되지 않았다. — [arena-human-preference-140k](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k); [arena-human-preference-55k README](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-55k/blob/main/README.md); [search-arena-24k](https://huggingface.co/datasets/lmarena-ai/search-arena-24k); [VisionArena-Battle](https://huggingface.co/datasets/lmarena-ai/VisionArena-Battle)
- **WildChat-4.8M**
  - ODC-BY이고, 2024-06에 AI2 ImpACT에서 ODC-BY로 소급 변경됐다.
  - 표준판은 ChatGPT 대화 3,199,860건이다. Full판(4,743,336건)은 게이트가 있고 구체적인 사유를 적어야 접근할 수 있다.
  - 모델 간 성과 비교나 투표 데이터는 없고 대화 로그뿐이다. — [WildChat-4.8M](https://huggingface.co/datasets/allenai/WildChat-4.8M); [WildChat LICENSE](https://huggingface.co/datasets/allenai/WildChat-4.8M-Full/blob/main/LICENSE.md)
- **LMSYS-Chat-1M**: 게이트가 있는 커스텀 License Agreement를 따른다. 비양도, 재라이선스 불가이며 라이선스 제공자가 언제든 해지하고 삭제를 요구할 수 있다. — [lmsys-chat-1m](https://huggingface.co/datasets/lmsys/lmsys-chat-1m); [파생 데이터셋의 약관 사본](https://huggingface.co/datasets/tokyotech-llm/lmsys-chat-1m-synth/blame/d54f2562d29aaed4842ffecb0b809b9d87237e5c/LMSYS-CHAT-1M_DATASET_LICENSE_AGREEMENT)
- **OpenRouter 랭킹 데이터**
  - 공개 랭킹과 같은 데이터를 JSON API로 받을 수 있다(OpenRouter API 키 필요). 일별 상위 50개 모델의 토큰 사용량과 나머지를 합친 "other" 행 1개로 구성된다.
  - 기간, 모달리티, tool-calling, 컨텍스트 길이로 필터링할 수 있다. private 요청은 집계에서 빠진다.
  - **CC BY 4.0**으로 재사용과 재게시가 가능하다(출처 표기 필요).
  - 앱별 랭킹도 있지만(예: Claude Code 22.5T 토큰), 서드파티 분석에 따르면 현재 export에는 앱×모델 행이 없다.
  - **품질이나 성공 정보는 없고 사용량(인기도)뿐이다.** — [OpenRouter Data](https://openrouter.ai/data); [OpenRouter rankings](https://openrouter.ai/rankings); [OpenRouter apps](https://openrouter.ai/apps); [codesota](https://www.codesota.com/agentic/openrouter-models); [일별 스냅샷 미러](https://github.com/mekos2772/usage-rankings-data)
- **Artificial Analysis**
  - 무료 API는 "Internal use only; no redistribution"이다. 모든 등급에서 출처 표기가 필요하다.
  - 무료 필드는 헤드라인 지수, 중앙값 성능, 입출력 가격이다. 전체 eval, 토큰 수 등은 Pro 필드다.
  - Data Platform Terms v1.1이 무료 API에도 적용된다.
  - 서드파티(modelspec PR) 해석에 따르면 기계 판독 가능한 재배포, 고객용 API 제공, **모델 선택 가이드를 주는 "Competitive Product"가 금지**되고, 위반 시 책임 한도가 없다.
  - 재배포하려면 Commercial 라이선스가 필요하다. — [AA Data API docs](https://artificialanalysis.ai/data-api/docs); [AA API reference](https://artificialanalysis.ai/api-reference); [AA Data Platform Terms v1.1 PDF](https://artificialanalysiscdn.com/legal/ProDataPlatformTerms.pdf); [modelspec PR #173](https://github.com/turbobeest/modelspec/pull/173)
- **Aider 리더보드**
  - `aider/website/_data/polyglot_leaderboard.yml`(225 테스트, 다언어)과 레거시 `edit_leaderboard.yml`(Python Exercism 133)이 있다.
  - 필드: `dirname`, `test_cases`, `model`, `edit_format`, `commit_hash`, `pass_rate_1`, `pass_rate_2`, `pass_num_1/2`, `percent_cases_well_formed`, `error_outputs`, `num_malformed_responses`, `user_asks`, `lazy_comments`, `syntax_errors`, `exhausted_context_windows`, `test_timeouts`, `command`, `date`, `versions`, `seconds_per_case`, `total_cost`.
  - 모델, 방법(edit_format), 비용, 지연, 성공률이 한 행에 들어 있어 **이 프로젝트의 스키마와 가장 비슷한 선례**다. 제출은 PR로 한다. — [polyglot_leaderboard.yml](https://github.com/Aider-AI/aider/blob/main/aider/website/_data/polyglot_leaderboard.yml); [aider benchmark README](https://github.com/Aider-AI/aider/blob/main/benchmark/README.md); [Aider leaderboards](https://aider.chat/docs/leaderboards/)
- **SWE-bench/experiments**
  - 제출별 predictions, 실행 로그, trajectories, 결과를 공개한다. 현재 레이아웃은 `all_preds.jsonl`, `logs/`, `trajs/`다.
  - 2025-11-18부터 Verified와 Multilingual 제출은 학술 기관으로 제한된다. Multimodal은 누구나 제출할 수 있다.
  - trajectory 형식은 비정형이다. 저장소 라이선스는 확인하지 못했다. — [SWE-bench experiments issue #482](https://github.com/SWE-bench/experiments/issues/482); [포크 README](https://github.com/ZhangShenao/experiments)
- **Open LLM Leaderboard**: v2(2024-06~2025, IFEval/BBH/MATH/GPQA/MuSR/MMLU-Pro)와 v1(2023-04~2024-06, 7K 모델)이 읽기 전용 아카이브로 남아 있다. 결과는 `open-llm-leaderboard/results`와 `open-llm-leaderboard-old/results` 데이터셋에 있다. **오픈 가중치 모델 중심이라 상용 API 모델 비교에는 쓸모가 적다.** — [HF archive docs](https://huggingface.co/docs/leaderboards/en/open_llm_leaderboard/archive); [Archived collection](https://huggingface.co/collections/OpenEvals/archived-open-llm-leaderboard-2024-2025)
- **HELM**: 원시 결과가 공개 GCS 버킷 `crfm-helm-public`에 있다(인증 불필요, 프로젝트당 수백 GB, Classic은 1TB 이상). 경로 형식은 `runs/v1.0.0/<RUN_ID>/run_spec.json|stats.json`이다. 데이터 라이선스는 문서에 명시돼 있지 않다. — [HELM Downloading Raw Results](https://crfm-helm.readthedocs.io/en/latest/downloading_raw_results/)
- **EEE datastore**: HF `evaleval/EEE_datastore`에 모델 22,235개, 고유 벤치마크 2,273개, 평가 포맷 31종이 있다(논문 2606.14516 기준). — [arXiv 2606.14516](https://arxiv.org/abs/2606.14516); [GitHub evaleval/every_eval_ever](https://github.com/evaleval/every_eval_ever)

### Inferences
- 시드 데이터는 세 층으로 나누는 것이 합리적이다.
  1. **벤치마크 선험치(prior)**: EEE datastore, Aider polyglot YAML, HF Community Evals. 태스크 유형에 대응하는 벤치마크를 매핑한다(예: coding은 Aider/SWE-bench, 수학은 MATH/HLE).
  2. **선호 기반 태스크별 승률**: arena-human-preference-140k, 55k를 프롬프트 카테고리로 분류해 모델별 승률로 집계한다. 이렇게 만든 집계 통계는 원시 출력 재배포보다 라이선스 위험이 작다(추론).
  3. **인기도와 사용 비중**: OpenRouter CC BY 4.0 데이터.

  이 셋 모두 "실제 작업 기록"은 아니므로, DB에서 `source_type = benchmark | preference | usage | field_report`처럼 출처를 구분해 사용자 제출 기록과 섞이지 않게 해야 한다.
- 제품이 성장할 경우를 생각하면 Artificial Analysis와 LMSYS-Chat-1M은 시드에서 빼는 것이 안전하다.

### Gaps
- LMArena 리더보드의 카테고리별 Elo(코딩, 수학, 창작 등) 원시 데이터가 2026년에 공개 export로 제공되는지는 확인하지 못했다.
- Arena-Hard-Auto 결과 파일의 라이선스, HELM 데이터 라이선스, SWE-bench/experiments 저장소 라이선스, EEE datastore 데이터 라이선스는 확인하지 못했다.
- OpenRouter Data API의 정확한 엔드포인트 경로와 인용 형식은 페이지를 직접 열람하지 못했다.

## Q4. "커뮤니티가 평가 결과를 제출"하는 기존 오픈소스 프로젝트와 스키마

### Takeaway
2026년에는 **Every Eval Ever(EEE)**가 사실상의 교차 프레임워크 결과 스키마로 떠오르고 있다. EvalEval Coalition이 만들었고, 2026-02에 출시됐으며 2026-06에 논문이 나왔다. HF Community Evals(2026-02-04 베타)의 `.eval_results/*.yaml`와 호환 컨버터가 있다. 둘 다 "Git/HF PR 기반 제출, 스키마 검증 봇, 출처 배지"라는 구조다. 이 프로젝트는 벤치마크가 아니라 **현장 작업 기록**을 다루므로 EEE의 aggregate/instance 분리와 `source_metadata.evaluator_relationship` 개념을 빌리고, 필드는 더 가볍게 가져가는 것이 적합하다.

### Cited Findings
- **EEE**
  - 단일 JSON 문서로 "누가 평가했는지, 어떤 모델인지, 어떤 생성 설정인지, 메트릭을 어떻게 계산했는지, 인스턴스 출력(선택)"을 표현한다.
  - Inspect AI, HELM, lm-eval-harness 컨버터가 있다.
  - HF에서 모델 22,235개, 벤치마크 2,273개, 포맷 31종을 호스팅한다.
  - Pith 리뷰는 고정 스키마 하나로 모든 프레임워크를 손실 없이 표현할 수 있다는 가정에 의문을 제기한다. — [arXiv 2606.14516](https://arxiv.org/abs/2606.14516); [EEE 프로젝트 페이지](https://evalevalai.com/projects/every-eval-ever/); [Pith 리뷰](https://pith.science/paper/2606.14516)
- **EEE 스키마 구조**
  - aggregate `eval.schema.json`: `source_metadata`(`source_name`, `source_type`, `source_organization_name`, `evaluator_relationship`), `generation_config`(`generation_args`, agentic의 경우 `agentic_eval_config.available_tools`, `eval_limits`, `sandbox`), `evaluation_results[]`(`evaluation_name`, `metric_config`{`evaluation_description`, `lower_is_better`, `score_type`, `min_score`, `max_score`}, `score_details`, CI/SE 지원), `detailed_evaluation_results.file_path`.
  - instance `{uuid}_samples.jsonl`: `schema_version`(예: "0.3.0"), `evaluation_id`, `model_id`, `evaluation_name`, `sample_id`, `interaction_type`(`single_turn`/`multi_turn`/`agentic`), `input`, `output`/`messages`(+`tool_calls`), `answer_attribution`, `evaluation`{`score`, `is_correct`}, 선택 필드 `token_usage`, `performance`.
  - 저장 경로는 `data/{benchmark}/{developer}/{model}/{uuid}.json`이다.
  - 제출 절차: CLI `every_eval_ever validate`로 로컬 검증한 뒤 PR을 올리면 봇이 다시 검증한다. 경고만 있어도 merge가 막힌다.
  - 저장소는 MIT다. — [GitHub evaleval/every_eval_ever](https://github.com/evaleval/every_eval_ever)
- **HF Community Evals**(2026-02-04 베타)
  - 벤치마크 dataset repo가 `eval.yaml`(Inspect AI 기반)로 등록한다. 모델 repo에는 `.eval_results/*.yaml`을 둔다.
  - 필드: `dataset.id`(필수), `task_id`, `value`(필수), `revision`, `verifyToken`(검증 가능한 평가 증명), `date`, `source`.
  - 작성자, 커뮤니티(PR), 검증 여부를 배지로 구분한다. 모델 작성자는 PR을 닫거나 결과를 숨길 수 있다.
  - 첫 벤치마크는 MMLU-Pro, GPQA, HLE였다.
  - 2026-06에 EEE와 호환되는 컨버터가 나왔다. — [HF blog: Community Evals](https://huggingface.co/blog/community-evals); [HF Hub docs: Evaluation Results](https://huggingface.co/docs/hub/main/en/eval-results); [HF blog: EEE on model pages](https://huggingface.co/blog/eee-community-evals); [huggingface/community-evals](https://github.com/huggingface/community-evals); [InfoQ 2026-02](https://www.infoq.com/news/2026/02/hugging-face-evals)
- **Aider**: 벤치마크 러너가 YAML 한 블록을 만들고, 이를 PR로 `_data/*.yml`에 추가하는 구조다(필드는 Q3 참고). — [aider benchmark README](https://github.com/Aider-AI/aider/blob/main/benchmark/README.md)
- **SWE-bench**: 제출 형식은 `all_preds.jsonl`, `logs/`, `trajs/`와 system description(논문, 기술 보고서, 블로그)이다. `swebench submit verify`, `package`, `publish`, `register` CLI가 있다. — [SWE-bench experiments issue #482](https://github.com/SWE-bench/experiments/issues/482)

### Inferences
- **권장 최소 레코드 스키마**(초안). EEE instance 레코드와 OTel GenAI 이름을 매핑해서 만든다. 각 필드 옆 괄호가 매핑 대상이다.

```json
{
  "schema_version": "0.1.0",
  "record_id": "uuid",
  "submitted_at": "2026-09-27T12:00:00Z",
  "source": {
    "client": "claude-code",        // 수집 클라이언트 (EEE source_metadata.source_name 유사)
    "client_version": "2.1.x",
    "collector": "stop-hook|otel|litellm|mcp|manual",
    "evaluator_relationship": "self|user|third_party"   // EEE 개념 차용
  },
  "task": {
    "type": "code.bugfix",          // 고정 taxonomy (계층형 enum)
    "summary": "짧은 요약(선택, 기본 off, 로컬 LLM/규칙으로 비식별화)",
    "language": "ko",
    "interaction_type": "agentic"   // EEE: single_turn|multi_turn|agentic
  },
  "model": {
    "provider": "anthropic",        // gen_ai.provider.name
    "id": "claude-opus-5-5",        // gen_ai.response.model (없으면 request.model)
    "effort": "high"                // Claude Code effort / reasoning 설정
  },
  "method": {
    "harness": "claude-code",       // 에이전트/앱
    "workflow_tags": ["plan-mode","subagents","tdd"],
    "tools_used": ["Bash","Edit"]   // 이름만, 인자 제외
  },
  "usage": {
    "input_tokens": 0,              // gen_ai.usage.input_tokens
    "output_tokens": 0,             // gen_ai.usage.output_tokens
    "cache_read_tokens": 0,
    "reasoning_tokens": 0,
    "cost_usd": 0.0,                // 클라이언트 보고 + 서버 재계산값 별도 저장 권장
    "cost_source": "client|server_pricing",
    "latency_ms": 0,
    "turns": 0
  },
  "outcome": {
    "status": "completed|aborted|error",       // Cursor stop status와 동일한 enum
    "quality": {                                // OTel gen_ai.evaluation.* 대응
      "name": "self_assessment_v1",             // gen_ai.evaluation.name
      "score": 0.8,                             // score.value (0~1 정규화)
      "label": "pass",                          // score.label
      "rater": "self_llm|user|test_suite"
    },
    "verifiable_signal": {"tests_passed": true} // 가능할 때만(테스트 통과, 커밋 여부 등)
  },
  "privacy": {"content_included": false}
}
```

- **최소 수집 클라이언트 설계**(추론):
  1. 로컬 CLI/데몬 `taskdb-agent` 하나를 둔다.
  2. Claude Code 어댑터: `~/.claude/settings.json`에 `Stop` 훅(command)을 설치한다. 훅이 `transcript_path`를 파싱해 model과 usage를 합산하고, `last_assistant_message`와 최근 사용자 프롬프트로 태스크 유형을 분류한다(로컬 규칙이나 `prompt` 훅).
  3. 전송 전 미리보기와 비식별화를 거친 뒤 HTTPS POST로 보낸다.
  4. 선택 옵션으로 로컬 OTLP 수신기(4318)를 켜 토큰, 비용, 지연을 보강한다.
  5. 20% MVP에서는 Claude Code 하나만 지원하고, 다음 단계로 Cursor(`stop`, model 제공)와 Codex(`notify`, OTel)를 추가하며, 그다음 LiteLLM `CustomLogger`를 붙인다.
  6. 서버는 JSON Schema 검증, append-only 저장, 공개 덤프(HF dataset, EEE 호환 export)로 구성한다.
- 기존 표준과 연결해 두면 신뢰도에 도움이 된다(추론). EEE 컨버터를 제공하면 HF Community Evals와 EEE 생태계에 합류할 수 있고, OTel `gen_ai.evaluation.result`를 받아들이면 DeepEval 같은 평가기의 출력을 그대로 흡수할 수 있다.
- 자기 평가 품질은 편향이 크므로 `rater` 필드로 자기 평가, 사용자 평가, 테스트 기반 평가를 구분해 저장하고, 집계할 때 가중치를 달리하는 것이 필수다(추론). HF의 author/community/verified 배지와 EEE의 `evaluator_relationship`이 선례다.

### Gaps
- EEE aggregate 스키마의 required 필드 목록과 `model_info` 필드 이름은 `eval.schema.json` 원문을 열람하지 못해 확인하지 못했다.
- OpenCompass의 결과 제출 스키마와 "Evaluation cards" 표준은 이번 조사 범위 안에서 출처를 확보하지 못했다.
- "실제 작업 로그를 에이전트가 자동 제출하는 공개 DB"라는 직접적인 선례는 찾지 못했다. 가장 가까운 것은 OpenRouter 앱 attribution(사용량만)과 Aider 벤치 YAML(벤치마크만)이다. 이것이 부재를 증명하지는 않으며, 선례 탐색은 별도 조사로 보완해야 한다.
