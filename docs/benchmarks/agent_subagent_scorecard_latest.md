# Agent Subagent Scorecard

- generated_at: 2026-03-27T13:32:59.167622+00:00
- source_fixture: tests/golden/chat_stream_golden_fixture.json
- expected_subagents: ['research', 'planning', 'budget', 'verification']
- observed_subagents: ['planning', 'research', 'verification']
- expected_eval_modes: ['plan', 'react']
- healthy_subagents: 0
- partial_subagents: 2
- mismatch_subagents: 1
- missing_subagents: 1

## Subagents

### research

- status: partial
- coverage_score: 0.5
- modes_seen: ['plan', 'react']
- expected_skills: ['AttractionResearchSkill', 'CityResearchSkill', 'TravelTipsSkill', 'WeatherLookupSkill']
- observed_skills: ['CityResearchSkill']
- expected_tools: ['query_attractions', 'search_cities', 'get_travel_tips', 'get_weather']
- observed_tools: ['search_cities']
- start_count: 2
- end_count: 2
- artifact_patch_count: 0
- tool_event_count: 4
- issues: ['missing skills: AttractionResearchSkill, TravelTipsSkill, WeatherLookupSkill', 'missing tools: get_travel_tips, get_weather, query_attractions', 'no artifact patch observed']

### planning

- status: partial
- coverage_score: 0.6667
- modes_seen: ['plan', 'react']
- expected_skills: ['HotelQuoteSkill', 'PlanSynthesisSkill', 'WeatherLookupSkill']
- observed_skills: ['PlanSynthesisSkill']
- expected_tools: ['query_hotels', 'plan_itinerary', 'get_weather']
- observed_tools: []
- start_count: 3
- end_count: 3
- artifact_patch_count: 3
- tool_event_count: 0
- issues: ['missing skills: HotelQuoteSkill, WeatherLookupSkill', 'missing tools: get_weather, plan_itinerary, query_hotels']

### budget

- status: missing
- coverage_score: 0.0
- modes_seen: []
- expected_skills: ['BudgetAggregationSkill', 'HotelQuoteSkill']
- observed_skills: []
- expected_tools: ['calculate_budget', 'query_hotels']
- observed_tools: []
- start_count: 0
- end_count: 0
- artifact_patch_count: 0
- tool_event_count: 0
- issues: ['fixture coverage missing', 'missing skills: BudgetAggregationSkill, HotelQuoteSkill', 'missing tools: calculate_budget, query_hotels', 'no artifact patch observed']

### verification

- status: mismatch
- coverage_score: 0.6
- modes_seen: ['plan', 'react']
- expected_skills: ['TravelTipsSkill', 'WeatherLookupSkill']
- observed_skills: ['BudgetAggregationSkill']
- expected_tools: ['get_travel_tips', 'get_weather']
- observed_tools: []
- start_count: 2
- end_count: 2
- artifact_patch_count: 2
- tool_event_count: 0
- issues: ['unexpected skills: BudgetAggregationSkill', 'missing skills: TravelTipsSkill, WeatherLookupSkill', 'missing tools: get_travel_tips, get_weather']

## Modes

- direct: subagents=[], starts=0, ends=0, artifact_patches=0, tool_events=0
- plan: subagents=['planning', 'research', 'verification'], starts=4, ends=4, artifact_patches=3, tool_events=2
- react: subagents=['planning', 'research', 'verification'], starts=3, ends=3, artifact_patches=2, tool_events=2
