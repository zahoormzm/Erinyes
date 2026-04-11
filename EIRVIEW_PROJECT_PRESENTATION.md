# EirView Project Presentation

## Slide 1: Title
**EirView**

Health intelligence platform for interpretation, prediction, coaching, and action.

Subtitle:
- Not a dashboard of health statistics
- A full-stack health operating system built around deterministic health modeling and AI-guided action

---

## Slide 2: The Core Misconception
**What people assume**

"This just calculates statistics from the data you upload."

**Why that is wrong**

EirView does not stop at displaying numbers.

It:
- collects health data from multiple real-world sources
- normalizes and validates that data
- computes biological age and risk projections
- translates findings into coaching, reminders, simulations, and escalation paths
- supports conversations that are grounded in the user's own numbers
- pushes the user toward decisions, not just awareness

**One-line thesis**

EirView is not a passive analytics dashboard. It is an interactive health intelligence and decision-support system.

---

## Slide 3: What EirView Actually Is
**EirView is a health intelligence platform**

It combines:
- deterministic health formulas
- multi-source data ingestion
- context-aware recommendations
- agent-driven explanation
- future-risk simulation
- mental wellness support
- reminders, alerts, and specialist escalation

**In simple terms**

It takes raw health signals and turns them into:
- understanding
- prioritization
- next actions
- long-term planning

---

## Slide 4: Why It Is Not "Just Statistics"
**A statistics-only product would:**
- ingest data
- calculate numbers
- show charts

**EirView goes much further:**
- interprets health signals across domains
- identifies what matters most right now
- simulates future outcomes if habits change
- surfaces contextual reminders based on time, weather, hydration, mood, and activity
- recommends specialists when thresholds are crossed
- generates doctor-facing escalation reports
- supports guided chat experiences for coaching, mental health, and future-self reflection

**The difference**

Statistics describe the state.

EirView explains the state, predicts the trajectory, and guides the response.

---

## Slide 5: Product Vision
**Mission**

Help users understand where their health is heading and what to do next.

**Design principle**

"Formulas compute, AI communicates."

That means:
- health numbers come from deterministic code, not from a language model
- AI is used to parse inputs, explain outputs, and guide the user
- the system remains auditable, consistent, and explainable

---

## Slide 6: Main Product Areas
**1. Health Modeling**
- biological age across cardiovascular, metabolic, musculoskeletal, and neurological systems
- mental wellness scoring
- nutrition and workout target generation
- risk projection over time

**2. Data Ingestion**
- blood report PDFs
- Cult.fit or body-composition scans
- Apple Health XML or ZIP exports
- meal photos
- text meal descriptions
- FaceAge selfie uploads
- browser-based posture checks
- manual data entry
- mobile/iPhone sync

**3. Guidance and Action**
- coach chat
- mental health chat
- future-self chat
- reminders and nudges
- specialist recommendations
- doctor notifications and reports
- gamification and streaks
- family health views

---

## Slide 7: Data Sources and Real Inputs
**EirView is multi-modal**

It works with:
- structured health metrics
- unstructured medical documents
- images
- wearable/device exports
- user-entered habits
- Spotify listening behavior
- location-based weather and AQI context

**Why this matters**

A statistics tool only works on already-clean numbers.

EirView includes the pipeline that turns messy real-world inputs into usable health intelligence.

---

## Slide 8: Feature Deep Dive
**Biological Age Engine**
- four subsystem ages
- weighted overall biological age
- contributing-factor ranking

**Risk Forecasting**
- diabetes risk
- cardiovascular risk
- metabolic risk
- mental decline risk
- 15-year projection curves

**What-If Simulation**
- sleep, exercise, diet, stress, screen time, academic stress
- duration-aware scenario scaling
- projected bio-age and risk changes

**Mental Health Layer**
- wellness scoring
- PHQ-9 aware
- sleep, HRV, screen time, nutrition, Spotify mood cross-signals

---

## Slide 9: Action Layer
**This is one of the strongest reasons EirView is not just analytics**

EirView creates action from insight:
- smart reminders
- hydration prompts
- movement nudges
- sleep wind-down prompts
- vitamin D prompts using weather and UV context
- posture follow-ups
- nutrition follow-ups
- mood-related nudges from Spotify patterns

It also escalates:
- critical-value alerts
- specialist recommendations
- doctor notifications
- report generation for handoff

---

## Slide 10: Conversational Experiences
**Coach**
- practical health advice grounded in real profile data
- nutrition, recovery, sleep, activity, next-step prioritization

**Mental Health**
- empathetic conversation grounded in sleep, HRV, stress, Spotify mood, and PHQ-9
- not generic chat
- personalized to the user's current state

**Future Self**
- long-term habit consequences
- risk projection translated into urgency
- emotionally memorable communication of future outcomes

**Key point**

These chats are not a generic chatbot pasted onto a dashboard.

They are specialized interfaces sitting on top of deterministic health logic and live user context.

---

## Slide 11: Example of the Difference
**A basic analytics app says**
- "Your sleep is 5.8 hours."
- "Your LDL is 145."
- "Your 10-year heart risk is X%."

**EirView says**
- your neurological recovery is aging faster because sleep is short and stress is high
- your cardiovascular system is under more strain than your age suggests
- if you sustain this pattern for 6 months, your projected biological age and 10-year risks move in a measurable direction
- here is the single highest-leverage change to make next

**That is interpretation + prioritization + simulation + action**

Not just statistics.

---

## Slide 12: System Architecture
**Frontend**
- React 19
- Vite
- Zustand
- Recharts
- MediaPipe in browser for posture analysis

**Backend**
- FastAPI
- SQLite via `aiosqlite`
- deterministic Python modeling layer
- API aggregation layer
- specialized AI agents and tool-execution runner

**Storage**
- canonical user profile
- meals, workouts, water, posture, Spotify history
- risk projections
- agent logs
- reminders, alerts, achievements, families, reflections

---

## Slide 13: Architecture Philosophy
**Core architecture rule**

The database is the source of truth.

**Deterministic services handle**
- scoring
- thresholds
- simulations
- risk calculations
- targets

**AI services handle**
- extraction from messy input
- explanation of deterministic results
- conversation
- routing and orchestration

**Why this is important**
- consistency
- explainability
- reproducibility
- lower hallucination risk

---

## Slide 14: Data Flow
**Typical flow**

1. User uploads or syncs data
2. Parsers normalize input
3. Profile is updated in SQLite
4. Deterministic formulas recompute scores and projections
5. Alerts, specialists, reminders, and targets refresh
6. Agents explain findings and guide next actions
7. Frontend surfaces both summary and drill-down views

**This is a pipeline**

Not a static charting layer.

---

## Slide 15: Agent Architecture
**Specialized agents**
- Orchestrator
- Collector
- Mirror
- Coach
- Mental Health
- Time Machine

**Roles**
- Collector parses and validates incoming health data
- Mirror explains biological age
- Coach translates data into practical guidance
- Mental Health connects behavior, biology, and mood
- Time Machine projects future outcomes
- Orchestrator routes based on difficulty and context

**Important**

These agents do not invent health metrics.

They call tools that operate on deterministic logic.

---

## Slide 16: Research-Driven Systems
**EirView includes ideas inspired by modern agentic AI research**

Implemented concepts include:
- ReAct
- DAAO-style difficulty-aware orchestration
- semantic caching
- Reflexion-like memory
- music-emotion classification for behavioral context

These are not just names on a slide. They appear in the codebase and are visible in the Research Lab feature.

---

## Slide 17: ReAct
**ReAct = Reason + Act**

In EirView:
- agents stream reasoning as Thought, Action, Observation, Answer
- tool calls are separated from final user-visible answer
- reasoning traces can be inspected
- agents ground claims in tool-derived observations

**Why this matters**
- cleaner chat UX
- better transparency
- stronger tool use
- more explainable AI behavior

---

## Slide 18: DAAO-Style Difficulty Routing
**Not every user query needs the same amount of reasoning**

EirView classifies chat inputs into:
- easy
- medium
- hard

Then adapts:
- iteration budget
- routing strategy
- likely specialist involvement

**Why this matters**
- faster responses for simple lookups
- deeper reasoning only when needed
- lower cost
- better user experience

---

## Slide 19: Semantic Cache and Reflexion
**Semantic Cache**
- reuses prior answers when the query is similar and the user's health fingerprint is unchanged
- avoids redundant AI work
- improves speed and cost efficiency

**Reflexion**
- after medium/hard runs, the system stores short lessons about what context was used or missed
- later prompts can inject those reflections
- helps agents become more personalized over time

**Result**

EirView is not just reactive. It is learning how to respond better to a given user's context.

---

## Slide 20: Scientific and Clinical Basis
**Health modeling references include**
- PhenoAge inspiration
- Klemera-Doubal biological age concepts
- Framingham-style cardiovascular reasoning
- ADA glucose/HbA1c thresholds
- HRV and sleep literature
- PHQ-9 mental-health framework
- FaceAge-inspired facial biological age estimation

**Important nuance**

EirView is research-informed and deterministic, but it is not positioned as a medical diagnosis engine.

It is a health intelligence and guidance system.

---

## Slide 21: Why The Biological Age Model Matters
**The bio-age model is not a vanity metric**

It acts as:
- a unifying layer across health domains
- a prioritization system
- a simulation baseline
- an explanation tool for non-technical users

Instead of isolated numbers, users see how different behaviors affect whole-body aging patterns.

That creates a much stronger behavior-change loop than raw statistics alone.

---

## Slide 22: Explainability and Trust
**EirView is designed to answer**
- why is this score high?
- which inputs drove it?
- what is missing?
- what can improve it?

Mechanisms:
- formula breakdown tooltips
- detailed subsystem components
- doctor report summaries
- visible reasoning traces
- deterministic outputs

**Trust comes from transparent computation plus contextual explanation**

---

## Slide 23: User Experience Surfaces
**Dashboard**
- unified health snapshot

**Data Ingest**
- source freshness, extraction summaries, validation results

**Insights**
- scenario modeling and risk comparison

**Mental**
- wellness + mood-aware conversation

**Nutrition**
- meal analysis + nutrition coaching

**Activity**
- workout logging + targets + movement nudges

**Future Self**
- long-term consequence framing

**Research Lab**
- visible proof of advanced agentic systems

---

## Slide 24: Differentiators
**What makes EirView distinct**

1. Deterministic health engine plus AI-guided interface
2. Multi-source ingestion, not just manual form entry
3. Action systems: reminders, escalation, recommendations, simulation
4. Research-backed agent architecture visible to the user
5. Strong cross-domain reasoning across biological, behavioral, and emotional signals
6. Explainability at both formula and agent levels

---

## Slide 25: Privacy and Local-First Practicality
**Operational choices**
- runs locally in development
- SQLite-based single source of truth
- posture analysis runs in browser
- FaceAge can run locally with ONNX
- cloud AI used selectively, not for metric generation

**Why that matters**
- clearer data control
- lower dependency on opaque black-box systems
- easier to audit and reason about

---

## Slide 26: Who This Is For
**Primary users**
- health-conscious individuals
- students and young adults managing stress, recovery, and routine
- users with fragmented health data across labs, wearables, and self-tracking

**Secondary value**
- family-level awareness
- doctor handoff support
- mobile companion workflows
- research/demo visibility for advanced AI system behavior

---

## Slide 27: Project Summary
**EirView is not a statistics platform**

It is:
- a health intelligence system
- an interpretation and prioritization engine
- a future-risk simulator
- a coaching and behavioral intervention layer
- an explainable agentic application built on deterministic health logic

**The simplest accurate description**

EirView turns health data into understanding, trajectory, and action.

---

## Slide 28: Closing Slide
**Final takeaway**

If a dashboard only tells you what happened, it is analytics.

If a system tells you:
- what it means
- what matters most
- what happens next
- what to do now

then it is an intelligence platform.

**That is what EirView is.**

