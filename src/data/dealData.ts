export type RolePlayTurn = {
  speaker: 'buyer' | 'seller'
  line: string
  rating?: 'STRONG' | 'ACCEPTABLE' | 'WEAK'
  coachNote?: string
}

export type RolePlayScenario = {
  id: string
  title: string
  prompt: string
  description: string
  tags: string[]
  turns: RolePlayTurn[]
}

export type LiveEvent = {
  time: string
  stage: string
  signal: string
  whisper: string
  context: string
  sentiment: string
  dealTemp: number
  tempDirection: string
  badges: string[]
  activeSignals: Array<{
    channel: string
    title: string
    detail: string
  }>
  bant: Array<{
    label: string
    score: number
    value: string
  }>
  talkRatio: {
    you: number
    them: number
    note: string
  }
}

export const dealData = {
  buyer: {
    name: 'Maya Chen',
    title: 'VP Revenue Operations',
    company: 'Northstar Health Systems',
  },
  callMeta: {
    countdown: 'T-18 minutes',
    nextCall: 'Today / 5:30 PM IST',
    headline: 'Your pre-call intelligence, real-time signals, and post-call playbook — ready.',
    summary:
      'DealWhisper prepares a full buyer brief before every meeting, delivers real-time coaching prompts during the conversation, and instantly generates structured debriefs, CRM updates, and next-step actions when the call ends.',
  },
  topMetrics: [
    { label: 'Deal size', value: '$84k ARR', context: 'Mid-market expansion across 3 sales pods.' },
    { label: 'Stage', value: 'Late discovery', context: 'Economic buyer joining for the first time.' },
    { label: 'Temp', value: '78 deg', context: 'Trending up after implementation concerns were resolved.' },
    { label: 'Risk', value: 'Budget scrutiny', context: 'Ops headcount freeze creates timing pressure.' },
  ],
  strategyCard: {
    goal: 'Get Maya to confirm budget owner and agree to a CFO-inclusive follow-up this week.',
    anchor: '$84k ARR with onboarding included.',
    floor: '$71k ARR only if Northstar expands to 2-year term.',
    watchFor: 'Friendly interest without real authority access.',
    edge: 'Northstar is hiring RevOps analysts but their stack is still fragmented.',
  },
  preCall: {
    oneThing:
      'Northstar just opened six RevOps and enablement roles after a platform migration. Maya is under pressure to standardize forecasting before Q2 board reporting, which means implementation certainty matters more than a headline discount.',
    whoTheyAre:
      'Maya has been in seat for 14 months after five years at MedMetric, one of your strongest customers. Her posting behavior and conference talks point to an analytical operator who values disciplined rollouts, clean attribution, and executive-ready reporting over feature novelty.',
    whyNow:
      'Northstar announced a new ambulatory expansion in January and quietly posted finance systems roles last week. That combination usually means board visibility is rising, internal audit pressure is increasing, and tooling decisions are getting pulled into near-term planning.',
    realSituation:
      'Job descriptions reference Salesforce hygiene, forecasting accuracy, and lead routing breakdowns. Employee review comments mention reporting debt and tooling overlap. The real pain is not productivity theater; it is executive trust in pipeline numbers.',
    lastTime:
      'The previous call ended with Maya interested but unconvinced the rollout would be low lift. The rep promised a cleaner implementation story, a healthcare-specific proof point, and a clearer map of who needs to approve budget.',
    decisionTeam:
      'Maya is likely the operational driver, but the economic sign-off sits with CFO partner Liam Ortiz. IT security will review only if the deal advances. Their frontline sales director is a likely internal champion because enablement pain surfaced repeatedly in prior notes.',
    competitiveLandscape:
      'Clari is the named benchmark for forecasting maturity, but its implementation burden worries Maya. Spreadsheets are the real incumbent. Your edge is faster time to operational trust with less admin lift.',
    strategy:
      'Win the call by quantifying the cost of delayed forecasting accuracy, proving implementation stays inside current bandwidth, and trading any concession for stakeholder access.',
    firstTen:
      'Establish whether today is a qualification gate or an internal selling rehearsal. If it is a rehearsal, load Maya with the language she needs to win the CFO.',
    likelyObjections: [
      {
        rank: 1,
        name: 'Budget pressure',
        concern: 'She will frame spend as difficult under the current hiring freeze.',
        response: 'Diagnose whether the issue is hard ceiling or ROI confidence. Then tie cost to missed board visibility and manual forecast hours.',
      },
      {
        rank: 2,
        name: 'Implementation risk',
        concern: 'She wants proof this does not become another multi-quarter systems project.',
        response: 'Lead with phased rollout, similar healthcare references, and the exact onboarding timeline before pricing.',
      },
      {
        rank: 3,
        name: 'Authority deflection',
        concern: 'She may say the CFO needs to review before exposing whether she is bought in.',
        response: 'Ask what the CFO will care about most and secure the joint meeting while momentum is high.',
      },
    ],
  },
  researchSources: [
    {
      title: 'LinkedIn and speaker footprint',
      detail: 'Title history, prior employer overlap, posting cadence, and decision-style clues from public talks.',
    },
    {
      title: 'Company intelligence',
      detail: 'Funding, hiring, leadership movement, product bets, and signals of budget expansion or contraction.',
    },
    {
      title: 'CRM and transcript history',
      detail: 'Every note, every promise, previous objections, and the exact phrases that resonated or stalled.',
    },
    {
      title: 'Tech stack confirmation',
      detail: 'BuiltWith patterns, job requirements, partner pages, and integration signals that lower adoption friction.',
    },
    {
      title: 'Review and community analysis',
      detail: 'Glassdoor, G2, Reddit, and customer-review themes that reveal internal pain buyers rarely state directly.',
    },
  ],
  buyerSnapshot: [
    { label: 'Decision style', value: 'Analytical, low-ego, prefers proof before enthusiasm.' },
    { label: 'Likely value frame', value: 'Forecast accuracy, executive trust, and implementation discipline.' },
    { label: 'Positive tell', value: 'Leans in and asks about rollout when mentally buying.' },
    { label: 'Resistance tell', value: 'Voice softens and gaze breaks when risk feels under-addressed.' },
  ],
  rolePlayScenarios: [
    {
      id: 'price-blocker',
      title: 'The Price Blocker',
      prompt: 'Buyer leads with budget pressure in the first 2 minutes.',
      description:
        'Maya is interested, but she wants to see if the rep will panic and discount before value is fully established.',
      tags: ['Budget', 'ROI', 'Hold line'],
      turns: [
        {
          speaker: 'buyer',
          line: 'Before we get too far, I need to be direct. We are under a freeze and the number may kill this.',
        },
        {
          speaker: 'seller',
          line: 'I hear you. Is the friction the absolute spend, or confidence that the return shows up quickly enough?',
          rating: 'STRONG',
          coachNote: 'Diagnoses before discounting and keeps the conversation in ROI, not panic.',
        },
        {
          speaker: 'buyer',
          line: 'Honestly, both. If I take this upstairs, I need to prove it pays back fast.',
        },
        {
          speaker: 'seller',
          line: 'Then let us pressure-test payback together. How many hours does manual forecast cleanup cost your team each month today?',
          rating: 'STRONG',
          coachNote: 'Moves into quantified pain. Good bridge to business case.',
        },
      ],
    },
    {
      id: 'committee-hider',
      title: 'The Committee Hider',
      prompt: 'Buyer sounds decisive but keeps unnamed approvers in the background.',
      description:
        'The rep needs to determine whether Maya truly owns the decision or is softening the no behind process language.',
      tags: ['Authority', 'Stakeholders', 'Process'],
      turns: [
        {
          speaker: 'buyer',
          line: 'This all makes sense. I just need to run it by a few people internally.',
        },
        {
          speaker: 'seller',
          line: 'Of course. When you take it to them, what question is most likely to slow it down?',
          rating: 'STRONG',
          coachNote: 'Surfaces the hidden objection instead of accepting vague process language.',
        },
        {
          speaker: 'buyer',
          line: 'The CFO will want to know why this cannot wait until next quarter.',
        },
        {
          speaker: 'seller',
          line: 'Then the next meeting should include them. I can walk through the cost of waiting with both of you together.',
          rating: 'ACCEPTABLE',
          coachNote: 'Solid move, but it would be stronger if the rep first confirms Maya agrees with the urgency case.',
        },
      ],
    },
    {
      id: 'technical-skeptic',
      title: 'The Technical Skeptic',
      prompt: 'Implementation questions become a shield against commitment.',
      description:
        'The buyer is less worried about integration detail than about being blamed for a failed rollout. The rep needs to reduce perceived risk without turning the call into a product dump.',
      tags: ['Implementation', 'Risk', 'Proof'],
      turns: [
        {
          speaker: 'buyer',
          line: 'Walk me through every system touchpoint. I cannot introduce another messy rollout.',
        },
        {
          speaker: 'seller',
          line: 'Absolutely. Before I get tactical, what rollout failure are you most trying not to repeat?',
          rating: 'STRONG',
          coachNote: 'Gets beneath the implementation question to the real emotional risk.',
        },
        {
          speaker: 'buyer',
          line: 'Last year we bought something that took four months and created more admin work.',
        },
        {
          speaker: 'seller',
          line: 'Then the right benchmark is not feature depth. It is time to trust. Our phased launch is live in 21 days with RevOps owning less than two hours a week.',
          rating: 'STRONG',
          coachNote: 'Reframes around the buyer\'s real fear and answers with a proof-based operating metric.',
        },
      ],
    },
  ] as RolePlayScenario[],
  liveCall: {
    whisperCadence: '4.6 per hour',
    goal: 'Only interrupt when the move changes the deal.',
    stakeholders: [
      {
        name: 'Maya Chen',
        role: 'Operational lead',
        read: 'High engagement. Asking process questions and testing rollout confidence.',
      },
      {
        name: 'Liam Ortiz',
        role: 'Economic buyer',
        read: 'Quiet but decisive. Others glance toward him before discussing budget.',
      },
      {
        name: 'Sara Bell',
        role: 'Champion',
        read: 'Sales director. Nods quickly when frontline pain is named in concrete terms.',
      },
    ],
    stageRules: [
      {
        stage: 'Opening',
        mission: 'Establish control without overselling and confirm whether the full hour still exists.',
        coaching: 'Set the agenda, then let the buyer speak first. Match their energy, not your excitement.',
      },
      {
        stage: 'Discovery',
        mission: 'Get beneath the surface problem and quantify what waiting costs.',
        coaching: 'If pain is stated but not priced, you are still in shallow discovery.',
      },
      {
        stage: 'Presentation',
        mission: 'Tie every proof point to a pain the buyer already admitted.',
        coaching: 'If engagement drops, ask a question or skip ahead. No feature tours.',
      },
      {
        stage: 'Objection handling',
        mission: 'Resolve concerns instead of rephrasing them.',
        coaching: 'When the same objection returns, treat it as unresolved and ask what full resolution looks like.',
      },
      {
        stage: 'Negotiation',
        mission: 'Trade every concession for movement and keep the anchor intact.',
        coaching: 'Fast discounts invite pressure. Small, slow, reciprocal moves only.',
      },
      {
        stage: 'Close',
        mission: 'Convert interest into next-step commitment without adding new information.',
        coaching: 'Three strong buying signals in five minutes means the close window is open.',
      },
    ],
    events: [
      {
        time: '03:12',
        stage: 'Opening',
        signal: 'Trust building',
        whisper: 'Trust is high. Ask the direct agenda question.',
        context:
          'Maya is leaning in, nodding lightly, and mirrored the rep posture after the opening framing. This is the right moment to confirm what a win for the meeting looks like.',
        sentiment: 'Warm and engaged',
        dealTemp: 71,
        tempDirection: 'UP 4 after rapport set',
        badges: ['open posture', 'nodding', 'steady tone'],
        activeSignals: [
          {
            channel: 'Video',
            title: 'Leaning forward',
            detail: 'High-confidence engagement cue. Buyer wants more detail, not less.',
          },
          {
            channel: 'Audio',
            title: 'Pace matches seller',
            detail: 'Rapport established. The conversation rhythm is aligned instead of defensive.',
          },
          {
            channel: 'Language',
            title: 'Uses "we need"',
            detail: 'Problem ownership is already framed as real, not hypothetical.',
          },
        ],
        bant: [
          { label: 'Budget', score: 28, value: 'Not discussed yet' },
          { label: 'Authority', score: 42, value: 'Maya leading' },
          { label: 'Need', score: 81, value: 'Urgent reporting pain' },
          { label: 'Timeline', score: 39, value: 'Likely before Q2' },
        ],
        talkRatio: {
          you: 46,
          them: 54,
          note: 'Healthy opening balance. Keep discovery buyer-heavy.',
        },
      },
      {
        time: '14:48',
        stage: 'Discovery',
        signal: 'Hidden pain surfaced',
        whisper: 'Do not pitch yet. Ask what waiting costs monthly.',
        context:
          'Liam has not spoken much, but he looked up from notes the moment forecast misses were tied to board pressure. The stated problem just became financially real.',
        sentiment: 'Focused',
        dealTemp: 79,
        tempDirection: 'UP 8 after quantified urgency',
        badges: ['future consequence', 'voice drop', 'executive attention'],
        activeSignals: [
          {
            channel: 'Audio',
            title: 'Pause before answering',
            detail: 'The buyer took 3 seconds before discussing board reporting, which usually means the issue is politically loaded.',
          },
          {
            channel: 'Language',
            title: 'Shifted from "nice to have" to "need before hiring push"',
            detail: 'Need is moving from general interest to a time-bound business requirement.',
          },
          {
            channel: 'Video',
            title: 'Stillness and downward gaze',
            detail: 'Processing signal. Silence is helping. Do not interrupt with more product.',
          },
        ],
        bant: [
          { label: 'Budget', score: 51, value: 'Pressure acknowledged' },
          { label: 'Authority', score: 58, value: 'CFO influence implied' },
          { label: 'Need', score: 92, value: 'Pain quantified' },
          { label: 'Timeline', score: 73, value: 'Before Q2 planning' },
        ],
        talkRatio: {
          you: 41,
          them: 59,
          note: 'Correct ratio for discovery. Keep it here until cost of waiting is clear.',
        },
      },
      {
        time: '28:06',
        stage: 'Presentation',
        signal: 'Implementation interest',
        whisper: 'They are evaluating. Slow down and let the proof land.',
        context:
          'Maya is asking setup questions in future tense and Sara is taking notes. This is not curiosity theater; it is early implementation visualization.',
        sentiment: 'Constructive',
        dealTemp: 83,
        tempDirection: 'UP 4 after healthcare proof point',
        badges: ['future tense', 'visible notes', 'implementation detail'],
        activeSignals: [
          {
            channel: 'Language',
            title: 'Unprompted future-tense language',
            detail: 'Buyer said "when this is live for our team" which is a strong buying signal.',
          },
          {
            channel: 'Video',
            title: 'Chin-touch contemplation',
            detail: 'Evaluation signal. Hold the floor for a beat before answering the next question.',
          },
          {
            channel: 'Audio',
            title: 'Interruptions are additive, not hostile',
            detail: 'The buyer is cutting in to refine fit, not to escape the conversation.',
          },
        ],
        bant: [
          { label: 'Budget', score: 57, value: 'Value case forming' },
          { label: 'Authority', score: 67, value: 'Economic buyer engaged' },
          { label: 'Need', score: 94, value: 'Clear operational consequence' },
          { label: 'Timeline', score: 79, value: 'Implementation window matters' },
        ],
        talkRatio: {
          you: 53,
          them: 47,
          note: 'Presentation can climb, but ask a checkpoint question before the next proof point.',
        },
      },
      {
        time: '36:44',
        stage: 'Objection handling',
        signal: 'Price objection',
        whisper: 'Do not discount. Ask if it is number or return.',
        context:
          'Liam mentioned the hiring freeze while looking slightly up-right and then back to Maya. That usually means the budget line is partly real and partly negotiable if the business case is sharp enough.',
        sentiment: 'Cautious',
        dealTemp: 76,
        tempDirection: 'DOWN 7 after price tension',
        badges: ['budget pressure', 'constructed number', 'CFO attention'],
        activeSignals: [
          {
            channel: 'Audio',
            title: 'Volume dropped on budget ceiling',
            detail: 'Signals uncertainty. The number may be an opening frame, not a hard stop.',
          },
          {
            channel: 'Video',
            title: 'Lip compression after price stated',
            detail: 'Disagreement is present but not yet verbalized. Surface the real concern.',
          },
          {
            channel: 'Language',
            title: 'Asked "what is the best you can do"',
            detail: 'Negotiation has started. Hold position until value and constraints are clear.',
          },
        ],
        bant: [
          { label: 'Budget', score: 82, value: 'Range emerging' },
          { label: 'Authority', score: 74, value: 'Liam now active' },
          { label: 'Need', score: 94, value: 'Still urgent' },
          { label: 'Timeline', score: 81, value: 'Need before board cycle' },
        ],
        talkRatio: {
          you: 61,
          them: 39,
          note: 'Too high for objection handling. Ask, then let them justify their frame.',
        },
      },
      {
        time: '47:31',
        stage: 'Negotiation',
        signal: 'Close window opening',
        whisper: 'Close window open. Trade concession for joint follow-up.',
        context:
          'Maya asked whether a phased launch could start with one region while Liam asked about term options. Multiple Tier 1 buying signals are present within the same five-minute window.',
        sentiment: 'Intentional',
        dealTemp: 88,
        tempDirection: 'UP 12 after phased rollout framed',
        badges: ['term options', 'pilot framing', 'future rollout'],
        activeSignals: [
          {
            channel: 'Language',
            title: 'Term options question',
            detail: 'They are modeling a path to yes rather than evaluating abstractly.',
          },
          {
            channel: 'Video',
            title: 'Warm eye contact',
            detail: 'Trust recovered after objection handling. Good moment for a summary close.',
          },
          {
            channel: 'Audio',
            title: 'Overlap from both buyers',
            detail: 'High engagement. They are both trying to shape the deal instead of exit it.',
          },
        ],
        bant: [
          { label: 'Budget', score: 84, value: 'Trade-off path identified' },
          { label: 'Authority', score: 86, value: 'Decision group visible' },
          { label: 'Need', score: 95, value: 'Problem remains urgent' },
          { label: 'Timeline', score: 88, value: 'This week follow-up needed' },
        ],
        talkRatio: {
          you: 48,
          them: 52,
          note: 'Healthy. Let their own buying language do part of the close.',
        },
      },
    ] as LiveEvent[],
  },
  postCall: {
    date: 'Mar 16, 2026',
    duration: '52 min',
    outcome:
      'Northstar agreed to a CFO-inclusive follow-up on Thursday and asked for a phased-launch commercial option before the meeting.',
    dealTempShift: '71 deg to 88 deg after implementation risk was reduced and budget discussion stayed tied to ROI.',
    probabilityShift: '42% to 64% based on authority clarity, stronger urgency, and live negotiation behavior.',
    lesson:
      'The rep won momentum when they quantified the cost of waiting, and lost momentum only when they started explaining price before diagnosing the budget objection.',
    followUpEmail:
      'Maya, thanks again for the candid discussion today. As agreed, I will send the phased rollout option and a short ROI view before Thursday so you and Liam can review it together. We will use that meeting to confirm scope, timeline, and whether we move into security review.',
    crmUpdate:
      'Stage: Evaluation. Probability +22 points. New contact: Liam Ortiz, CFO partner. Key commitments: buyer requested phased commercial option, CFO follow-up this week, implementation proof remains central. Next action: send tailored pricing path by Wednesday 3 PM.',
    internalSummary:
      'Deal is now real, not just exploratory. Maya is aligned on need. Liam surfaced budget caution but engaged in term structure rather than walking. Support needed: one healthcare reference quote and a phased-launch pricing approval path.',
    keyMoments: [
      '14:48 - Cost-of-waiting question shifted the call from curiosity to business urgency.',
      '28:06 - Healthcare deployment proof triggered future-tense implementation language.',
      '36:44 - Price tension surfaced; the first instinct to explain price nearly softened leverage.',
      '47:31 - Term-length question plus phased rollout request created a valid summary-close window.',
    ],
    whatWorked: [
      'Discovery stayed tied to operating pain instead of drifting into generic forecasting language.',
      'The rep used a proof-oriented implementation narrative that matched Maya\'s risk profile.',
      'Concessions were kept conditional once negotiation became explicit.',
    ],
    whatCostYou: [
      'The rep talked too long immediately after the first price objection instead of diagnosing whether the issue was ROI confidence or a real ceiling.',
      'One moment of defensive explanation weakened the premium frame and cooled the deal temperature for roughly 90 seconds.',
    ],
    missedOpportunities: [
      'A stronger authority check could have happened 10 minutes earlier when Liam first reacted to board-pressure language.',
      'The rep could have asked Sara to describe frontline impact, which would have strengthened internal champion evidence.',
    ],
    coachingMetrics: [
      { label: 'Talk ratio', value: '48 / 52', note: 'Slightly high during pricing, otherwise healthy.' },
      { label: 'Filler rate', value: '1.4 per min', note: 'Under baseline; strongest when walking the rollout.' },
      { label: 'Objection handle score', value: '84 / 100', note: 'Recovered well after the initial price wobble.' },
      { label: 'Buying signal capture', value: '3 / 4', note: 'One close window opened later than necessary.' },
      { label: 'Concession management', value: 'Clean', note: 'No free discounting. Final move tied to a joint follow-up.' },
      { label: 'Overall score', value: '88 / 100', note: 'Strong strategic call with one avoidable dip in leverage.' },
    ],
    behavioralMemory: [
      { label: 'Preferred communication style', value: 'Analytical with low tolerance for fluffy enthusiasm.' },
      { label: 'Decision pace', value: 'Methodical until business case is quantified, then noticeably faster.' },
      { label: 'Risk tolerance', value: 'Moderate-low. Wants controlled rollout and peer validation.' },
      { label: 'Language that moved them', value: '"Time to trust" and "board confidence in the forecast".' },
      { label: 'Resistance triggers', value: 'Abstract ROI claims and implementation answers without specifics.' },
    ],
    companyIntelligence: [
      { label: 'Best objection response', value: 'ROI-first price diagnosis outperforms immediate commercial flexibility.' },
      { label: 'Case study resonance', value: 'Healthcare operations examples beat generic SaaS wins for this segment.' },
      { label: 'Optimal close window', value: 'After implementation certainty plus executive-use-case alignment appear together.' },
      { label: 'Most reliable discovery question', value: '"What does staying here cost you every month?"' },
      { label: 'Competitive risk pattern', value: 'Clari mentions correlate with concern about heavy rollout, not feature gaps.' },
    ],
  },
}
